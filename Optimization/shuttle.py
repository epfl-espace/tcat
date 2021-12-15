import numpy as np
import pandas as pd
from scipy.integrate import odeint
from scipy.interpolate import interp1d
from scipy.optimize import differential_evolution
from orbital_manoeuvres import *
from cost_vector import *
from poliastro.constants import GM_earth

GM_earth = GM_earth.value / 1e9 # km**3 / s**2
R_earth = 6.3710084e3 # km
R_eq_earth = 6.378136e3 # km

from mystic.differential_evolution import DifferentialEvolutionSolver
from mystic.termination import (
    And, Or, ChangeOverGeneration, NormalizedChangeOverGeneration
)
from mystic.monitors import VerboseMonitor, Monitor


def selected_debris(df, indices):
    """Input:
    df: dataframe containing all the debris, each of one is marked by
    its own index
    indices: np.array containing the indices of the debris selected
    to be caught

    Return:
    dataframe containing the debris to be caught
    """

    return df.loc[indices]


def population(cdf, pop_size):
    """Input:
    cdf: dataframe containing the debris to be caught, each of one is
    marked by its own index
    pop_size: size of the population (a population is made by individuals
    and each individual consists in an array of debris' indices)

    Return:
    population: list of individuals, where each individual is a np.array
    containing debris' indices
    """

    pop = []
    for i in range(pop_size):
        arr = np.array(cdf.index)
        np.random.shuffle(arr)
        pop.append(arr)
    return pop


def COE0(df, indices):
    """Input:
    df: dataframe containing all the debris, each of one is marked by
    its own index
    indices: np.array containing the indices of the debris selected
    to be caught

    Return:
    dictionary: the keys are the indices, the values consist in a
    np.array of the classical orbital elements (a in km, ecc,
    inc in rad, raan in rad, argp in rad, nu in rad)
    """

    return {
        i: np.array(
            [
                df.loc[i].a, df.loc[i].ecc,
                np.deg2rad(df.loc[i].inc),
                np.deg2rad(df.loc[i].raan),
                np.deg2rad(df.loc[i].argp),
                np.deg2rad(df.loc[i].nu)
            ]
        )
        for i in indices
    }


def COE_to_MEE(z):
    """Input:
    z: np.array containing the classical orbital elements (a, ecc, inc,
    raan, argp, nu)

    Return:
    np.array containing the corresponding modified equinoctial orbital
    elements (p, f, g, h, k, L)
    """

    a, ecc, inc, raan, argp, nu = z
    p = a * (1 - ecc**2)
    f = ecc * np.cos(argp + raan)
    g = ecc * np.sin(argp + raan)
    h = np.tan(inc / 2) * np.cos(raan)
    k = np.tan(inc / 2) * np.sin(raan)
    L = raan + argp + nu
    return np.array([p, f, g, h, k, L])


def MEE_to_COE(y):
    """Input:
    y: np.array containing the modified equinoctial orbital elements
    (p, f, g, h, k, L)

    Return:
    np.array containing the corresponding classical orbital elements
    (a, ecc, inc, raan, argp, nu)
    """

    p, f, g, h, k, L = y
    raan = np.arctan2(k, h)
    argp_ = np.arctan2(g, f)
    argp = argp_ - raan
    inc = np.arctan2(2 * np.sqrt(h**2 + k**2), 1 - h**2 - k**2)
    ecc = np.sqrt(f**2 + g**2)
    a = p / (1 - ecc**2)
    nu = L - argp_
    return np.array([a, ecc, inc, raan, argp, nu])


def J2_perturbation(y):
    """Input:
    y: np.array containing the modified equinoctial orbital elements
    (p in km, f, g, h, k, L in rad)

    Return:
    np.array containing the radial, tangential and normal perturbations
    acting on the orbit due to zonal gravity effects of J2 in km/s**2
    """

    p, f, g, h, k, L = y
    J2 = 1.0826e-3
    r = p / (1 + f * np.cos(L) + g * np.sin(L))
    R = -3 * GM_earth * J2 * R_eq_earth**2 / (2 * r**4) * (
        1 - 12 * (h * np.sin(L) - k * np.cos(L))**2 /
        (1 + h**2 + k**2)**2
    )
    T = -12 * GM_earth * J2 * R_eq_earth**2 / r**4 * (
        h * np.sin(L) - k * np.cos(L)
    ) * (h * np.cos(L) + k * np.sin(L)) / (1 + h**2 + k**2)**2
    N = -6 * GM_earth * J2 * R_eq_earth**2 / r**4 * (
        1 - h**2 - k**2
    ) * (h * np.sin(L) - k * np.cos(L)) / (1 + h**2 + k**2)**2
    return np.array([R, T, N])


def MEE_variation(y0, t, pert='J2_perturbation'):
    """Input:
    y0: np.array containing the initial conditions, that is the initial
    modified equinoctial orbital elements (p in km, f, g, h,
    k, L in rad)
    t: np.array containing the times at which the orbital elements will
    be computed (the array can also contain only one element) in s
    pert: perturbation taken into account; the default value is
    'J2_perturbation', but it can also be None or a callable

    Return:
    np.array containing the perturbed modified equinoctial orbital
    elements (p in km, f, g, h, k, L in rad), it has six rows (one for
    each orbital element) and a number of columns equal to the
    length of t
    """

    if pert == 'J2_perturbation':
        perturbation = J2_perturbation
    elif callable(pert):
        perturbation = pert
    elif pert is None:
        def perturbation(y):
            return np.array([0, 0, 0])
    else:
        raise ValueError(
            "pert is not a valid perturbation specification"
        )

    def equations(y, t):
        p, f, g, h, k, L = y
        R, T, N = perturbation(y)
        s = np.sqrt(1 + h**2 + k**2)
        w = 1 + f * np.cos(L) + g * np.sin(L)
        dpdt = T * 2 * p**(3 / 2) / (w * GM_earth**(1 / 2))
        dfdt = (p / GM_earth)**(1 / 2) * (
            R * np.sin(L) + (
                T * ((w + 1) * np.cos(L) + f) - N * g *
                (h * np.sin(L) - k * np.cos(L))
            ) / w
        )
        dgdt = (p / GM_earth)**(1 / 2) * (
            -R * np.cos(L) + (
                T * ((w + 1) * np.sin(L) + g) + N * f *
                (h * np.sin(L) - k * np.cos(L))
            ) / w
        )
        dhdt = N * (p / GM_earth)**(1 / 2) * s**2 * np.cos(L) / (2 * w)
        dkdt = N * (p / GM_earth)**(1 / 2) * s**2 * np.sin(L) / (2 * w)
        dLdt = GM_earth**(1 / 2) * p**(-3 / 2) * w**2 + (
            p / GM_earth
        )**(1 / 2) * N * (h * np.sin(L) - k * np.cos(L)) / w
        return [dpdt, dfdt, dgdt, dhdt, dkdt, dLdt]

    sol = odeint(equations, y0, t)
    p = sol[:, 0]
    f = sol[:, 1]
    g = sol[:, 2]
    h = sol[:, 3]
    k = sol[:, 4]
    L = sol[:, 5]
    return np.array([p, f, g, h, k, L])


def COE_variation(z0, t, pert='J2_perturbation'):
    """Input:
    z0: np.array containing the initial conditions, that is the initial
    classical orbital elements (a in km, ecc, inc in rad,
    raan in rad, argp in rad, nu in rad)
    t: np.array containing the times at which the orbital elements will
    be computed (the array can also contain only one element) in s
    pert: perturbation taken into account; the default value is
    'J2_perturbation', but it can also be None or a callable

    Return:
    np.array containing the perturbed classical orbital elements
    (a in km, ecc, inc in rad, raan in rad, argp in rad, nu in rad), it
    has six rows (one for each orbital element) and a number of columns
    equal to the length of t
    """

    MEE0 = COE_to_MEE(z0)
    MEEvar = MEE_variation(MEE0, t, pert=pert)
    return MEE_to_COE(MEEvar)


def COE_variation_interpolation(z0, ts, pert='J2_perturbation'):
    """Input:
    z0: np.array containing the initial conditions, that is the initial
    classical orbital elements (a in km, ecc, inc in rad,
    raan in rad, argp in rad, nu in rad)
    ts: np.array containing the times at which the orbital elements will
    be computed and interpolated in s
    pert: perturbation taken into account; the default value is
    'J2_perturbation', but it can also be None or a callable

    Return:
    tuple containing:
    [0] callable that requires as input a time (in s) between 0 and the
    maximum value of ts
    [1] np.array containing the perturbed classical orbital elements
    (a in km, ecc, inc in rad, raan in rad, argp in rad, nu in rad),
    it has six rows (one for each orbital element) and a number of
    columns equal to the length of ts
    """

    sol = COE_variation(z0, ts, pert=pert)
    return interp1d(ts, sol), sol


def COE_function_of_time(df, indices, ts, pert='J2_perturbation'):
    """Input:
    df: dataframe containing all the debris, each of one is marked by
    its own index
    indices: np.array containing the indices of the debris selected
    to be caught
    ts: np.array containing the times at which the orbital elements will
    be computed and interpolated in s
    pert: perturbation taken into account; the default value is
    'J2_perturbation', but it can also be None or a callable

    Return:
    tuple containing:
    [0] dictionary: the keys are the indices, the values consist in a
                    tuple containing:
                [0] callable that requires as input a time (in s)
                    between 0 and the maximum value of ts
                [1] np.array containing the perturbed classical orbital
                    elements (a in km, ecc, inc in rad, raan in rad,
                    argp in rad, nu in rad), it has six rows (one for
                    each orbital element) and a number of columns equal
                    to the length of ts
    [1] the minimum value among the values in ts
    [2] the maximum value among the values in ts
    """

    t_min = np.amin(ts)
    t_max = np.amax(ts)
    z0_several_debris = COE0(df, indices)
    return {
        i: COE_variation_interpolation(
        z0_several_debris[i], ts, pert=pert
        )
        for i in indices
    }, t_min, t_max


def delta_V_tot_GBT_shuttle(alpha1_alpha2, r1, r2, theta, h_deorbit):
    """Input:
    alpha1_alpha2: np.array containing:
        [0] alpha1: angle between the departure orbit (r1) and the first
            elliptical transfer orbit in radians
        [1] alpha2: angle between the first elliptical transfer orbit
            and the second elliptical transfer orbit in radians
    r1: radius of the departure circular orbit in km
    r2: radius of the arrival circular orbit in km
    theta: angle between the departure orbit and the arrival orbit
        in radians
    h_deorbit: altitude at which the debris is left by the shuttle and
        starts to deorbit in km

    Return:
    delta-V necessary for the transfer beetween a circular departure
    orbit (r1) and a circular arrival orbit (r2) separated by an angle
    theta with a Generalized Bielliptical Transfer, where the perigee of
    the transfer ellipsis is equal to R_earth + h_deorbit, in km/s
    """

    rt = R_earth + h_deorbit
    alpha1, alpha2 = alpha1_alpha2
    vc1 = velocity_circular_orbit(r1)
    vPt1 = velocity_orbit(r1, (r1 + rt) / 2)
    vAt1 = velocity_orbit(rt, (r1 + rt) / 2)
    vAt2 = velocity_orbit(rt, (r2 + rt) / 2)
    vc2 = velocity_circular_orbit(r2)
    vPt2 = velocity_orbit(r2, (r2 + rt) / 2)
    delta_V1 = delta_V_carnot(vc1, vPt1, alpha1)
    delta_V2 = delta_V_carnot(vAt1, vAt2, alpha2)
    delta_V3 = delta_V_carnot(vc2, vPt2, theta - alpha1 - alpha2)
    return delta_V1 + delta_V2 + delta_V3


def delta_V_tot_GBT_optimal_shuttle(r1, r2, theta, h_deorbit=500):
    """Input:
    r1: radius of the departure circular orbit in km
    r2: radius of the arrival circular orbit in km
    theta: angle between the departure orbit and the arrival orbit
        in radians
    h_deorbit: altitude at which the debris is left by the shuttle and
               starts to deorbit in km

    Return:
    tuple containing:
        [0] optimal delta-V necessary for the transfer beetween a circular
            departure orbit (r1) and a circular arrival orbit (r2) separated
            by an angle theta in km/s
        [1] array [alpha1, alpha2], with:
            alpha1: optimal angle between the departure orbit (r1) and the
                    first elliptical transfer orbit in radians
            alpha2: optimal angle between the first elliptical transfer
                    orbit and the second elliptical transfer orbit in radians
    for a Generalized Bielliptical Transfer where the perigee of the
    transfer ellipsis is equal to R_earth + h_deorbit
    """

    res = differential_evolution(
        delta_V_tot_GBT_shuttle, [(-np.pi, np.pi), (-np.pi, np.pi)],
        args=(r1, r2, theta, h_deorbit)
    )
    res = minimize(
        delta_V_tot_GBT_shuttle,
        res.x,
        method="BFGS",
        args=(r1, r2, theta, h_deorbit)
    )
    return res.fun, res.x


def delta_t_minimum_manouver_shuttle(COE1, COE2, h_deorbit=500):
    """Input:
    COE1: COE_variation_interpolation(z01, ts, pert)
    COE2: COE_variation_interpolation(z02, ts, pert)
    h_deorbit: altitude at which the shuttle leaves the target for its
               deorbiting in km

    Return:
    minimum time needed by the shuttle to go from debris1 to debris2
    with a Generalized Bielliptical Transfer, where the perigee of the
    transfer ellipsis is equal to R_earth + h_deorbit, in s
    """

    a_mean1 = np.mean(COE1[1][0])
    a_mean2 = np.mean(COE2[1][0])
    a_transfer_ellipse1 = (a_mean1 + R_earth + h_deorbit) / 2
    a_transfer_ellipse2 = (R_earth + h_deorbit + a_mean2) / 2
    return np.pi / np.sqrt(GM_earth) * (
        a_transfer_ellipse1**(3 / 2) + a_transfer_ellipse2**(3 / 2)
    )


class OutOfInterpolationRangeError(ValueError):
    pass


def delta_lambda(COE1, COE2, t1, h_deorbit=500):
    """Input:
    COE1: COE_variation_interpolation(z01, ts, pert)
    COE2: COE_variation_interpolation(z02, ts, pert)
    t1: time at which the shuttle begins the Generalized Bielliptical
        Transfer to deorbit debris1 in s
    h_deorbit: altitude at which the shuttle leaves the target for its
               deorbiting in km

    Return:
    lambda_angle in [0, 2pi): angle between the shuttle and the debris2
                            (in the same circular orbit) when the
                            shuttle arrives in the debris2's orbit
                            in radians
    """

    # t12 is the time at which the shuttle arrives in the second
    # debris' orbit:
    t12 = t1 + delta_t_minimum_manouver_shuttle(
        COE1, COE2, h_deorbit=h_deorbit
    )
    COE1_t1 = COE1[0](t1)
    try:
        COE2_t12 = COE2[0](t12)
    except ValueError as e:
        if "the interpolation range." in e.args[0]:
            raise OutOfInterpolationRangeError(*e.args)
        else:
            raise
    # u1_t1 = argp(t1) + nu(t1) is the argument of latitude of the first
    # debris at time t1:
    u1_t1 = COE1_t1[4] + COE1_t1[5]
    raan1_t1 = COE1_t1[3]
    raan2_t12 = COE2_t12[3]
    delta_raan = raan2_t12 - raan1_t1
    # alpha = inc(t1) is the inclination of the first debris' orbit
    # at time t1:
    alpha = COE1_t1[2]
    # beta = pi - inc(t12), where inc(t12) is the inclination of the
    # second debris' orbit at time t12:
    beta = np.pi - COE2_t12[2]
    cos_gamma = np.cos(u1_t1) * np.cos(delta_raan) + np.sin(
        u1_t1
    ) * np.sin(delta_raan) * np.cos(alpha)
    sin_gamma = np.sin(u1_t1) * np.sin(alpha) / np.sin(beta)
    # gamma is the argument of latitude of the shuttle in the second
    # debris' orbit at time t12:
    gamma = np.arctan2(sin_gamma, cos_gamma)
    # u2_t12 = argp(t12) + nu(t12) is the argument of latitude of the
    # second debris at time t12:
    u2_t12 = COE2_t12[4] + COE2_t12[5]
    lambda_angle = u2_t12 - gamma
    return lambda_angle % (2 * np.pi)


class TimeRendezVousError(ValueError):
    pass


def delta_V_shuttle(COE1, COE2, t1, t2, h_deorbit=500, h_min=200):
    """Input:
    COE1: COE_variation_interpolation(z01, ts, pert)
    COE2: COE_variation_interpolation(z02, ts, pert)
    t1: time at which the shuttle begins the Generalized Bielliptical
        Transfer to deorbit debris1 in s
    t2: time at which the shuttle begins the Generalized Bielliptical
        Transfer to deorbit debris2 in s
    h_deorbit: altitude at which the shuttle leaves the target for its
               deorbiting in km
    h_min: minimum safety altitude above which the shuttle can orbit
           in km

    Return:
    delta_V needed by the shuttle to go from debris1 to debris2 with a
    Generalized Bielliptical Transfer where the perigee of the transfer
    ellipsis is equal to (R_earth + h_deorbit) followed by a rephasing
    rendez-vous in km/s
    """

    # t1 e t2 devono essere nell'intervallo dei ts
    lambda_angle = delta_lambda(COE1, COE2, t1, h_deorbit=h_deorbit)
    # delta_t needed to go from debris1 orbit to debris2 orbit:
    min_delta_t = delta_t_minimum_manouver_shuttle(
        COE1, COE2, h_deorbit=h_deorbit
    )
    # t12 is the time at which the shuttle arrives in the second
    # debris' orbit:
    t12 = t1 + min_delta_t
    COE1_t1 = COE1[0](t1)
    COE2_t12 = COE2[0](t12)
    # delta_t needed by debris2 to travel (on the circular orbit)
    # the angle (2pi-lambda_angle):
    dt = delta_t(COE2_t12[0], lambda_angle)
    Tt_min = period_orbit_min(COE2_t12[0], h_min)
    T = period_orbit(COE2_t12[0])
    if dt >= Tt_min:
        if t2 < t1 + min_delta_t + dt:
            raise TimeRendezVousError(
                (
                    't2 must be greater than or equal to {} s '
                    '(= t1 + min_delta_t + dt)'
                ).format(t1 + min_delta_t + dt)
            )
    else:
        if t2 < t1 + min_delta_t + dt + T:
            raise TimeRendezVousError(
                (
                    't2 must be greater than or equal to {} s '
                    '(= t1 + min_delta_t + dt + T)'
                ).format(t1 + min_delta_t + dt + T)
            )
    trv_max = t2 - t12
    theta = theta_angle(
        COE1_t1[3], COE1_t1[2], COE2_t12[3], COE2_t12[2]
    )
    dV_GBT = delta_V_tot_GBT_optimal_shuttle(
        COE1_t1[0], COE2_t12[0], theta, h_deorbit=h_deorbit
    )[0]
    dV_so = delta_V_same_orbit_optimal(
        COE2_t12[0], lambda_angle, trv_max, h_min=h_min
    )[0]
    return dV_GBT + dV_so


def path_cost(times_array, i_sel, COE, h_deorbit=500, h_min=200):
    """Input:
    times_array: np.array containing times, each time is the time at
                which the shuttle begins the Generalized Bielliptical
                Transfer to deorbit the debris in s
    i_sel: np.array containing the indices of the debris in the order in
           which they will be caught
    COE = COE_function_of_time(df, indices, ts, pert)
    h_deorbit: altitude at which the shuttle leaves the target for its
               deorbiting in km
    h_min: minimum safety altitude above which the shuttle can orbit
           in km

    Return:
    total delta_V needed to catch all debris in the given order in km/s
    """

    tmp = 0
    for d in range(len(i_sel) - 1):
        try:
            tmp = tmp + delta_V_shuttle(
                COE[0][i_sel[d]],
                COE[0][i_sel[d + 1]],
                times_array[d],
                times_array[d + 1],
                h_deorbit=h_deorbit,
                h_min=h_min
            )
        except (TimeRendezVousError, OutOfInterpolationRangeError):
            return np.inf
    return tmp


def path_cost_population(
    times_arrays, pop, COE, h_deorbit=500, h_min=200
):
    return np.array(
        [
            path_cost(
                i[0], i[1], COE, h_deorbit=h_deorbit, h_min=h_min
            ) for i in zip(times_arrays, pop)
        ]
    )


def make_constr(t_min, t_max):
    def constr(times_array):
        return np.clip(np.sort(times_array), t_min, t_max)

    return constr


def time_optimization_of_deltaV(
    dim, NP, obj_fun, constraint, t_min, t_max, extra_args
):
    """Input:
    dim: dimensionality of the problem
    NP: size of the trial solution population [requires: NP >= 4]
    obj_fun: function to be minimized
    constraint: constraint regarding times_array (which is the np.array
                containing times, each time is the time at which the
                shuttle begins the Generalized Bielliptical Transfer to
                deorbit the debris in s)
    t_min: the minimum value among the values in ts (which is the
            np.array containing the times at which the orbital elements
            will be computed and interpolated in s)
    t_max: the maximum value among the values in ts
    extra_args: required extra arguments

    Return:
    tuple containing:
    [0] array containing the optimized times, each time is the time at
        which the shuttle begins the Generalized Bielliptical Transfer
        to deorbit the debris in s
    [1] optimal delta_V needed to catch the debris in the given order
        in km/s
    """

    solver = DifferentialEvolutionSolver(dim, NP)
    solver.SetConstraints(constraint)
    solver.SetRandomInitialPoints(
        np.repeat(t_min, dim), np.repeat(t_max, dim)
    )
    for i in range(len(solver.population)):
        solver.population[i] = solver._constraints(solver.population[i])
    termin = Or(
        ChangeOverGeneration(tolerance=1e-5, generations=30),
        NormalizedChangeOverGeneration(tolerance=1e-3, generations=20)
    )
    solver.SetTermination(termin)
    solver.SetGenerationMonitor(VerboseMonitor()) #this prints all the stuff
    solver.Solve(obj_fun, ExtraArgs=extra_args)
    return solver.bestSolution, solver.bestEnergy


class Individual():
    def __init__(self, times_array, i, cost):
        self.times_array = times_array
        self.i = i
        self.cost = cost

    def __repr__(self):
        return "Individual({!r}, {!r}, {!r})".format(
            self.times_array, self.i, self.cost
        )

    def __str__(self):
        return "times = {!r}, i = {!r}, cost = {!r}".format(
            self.times_array, self.i, self.cost
        )


def time_optimization_of_deltaV_population(
    pop, COE, obj_fun=path_cost, h_deorbit=500, h_min=200
):
    """Input:
    pop: list of sequences, where each sequence is a np.array
         containing debris' indices
    COE = COE_function_of_time(df, indices, ts, pert)
    obj_fun: function to be minimized; the default value is path_cost
    h_deorbit: altitude at which the shuttle leaves the target for its
               deorbiting in km
    h_min: minimum safety altitude above which the shuttle can orbit
           in km

    Return:
    list of objects of the class Individual optimized in time
    """

    dim = len(pop[0])
    NP = len(pop)
    t_min = COE[1]
    t_max = COE[2]
    constraint = make_constr(t_min, t_max)
    j = []
    for i in pop:
        extra_args = (i, COE, h_deorbit, h_min)
        time_opt = time_optimization_of_deltaV(
            dim, NP, obj_fun, constraint, t_min, t_max, extra_args
        )
        bestsolution_ind_bestenergy = Individual(
            time_opt[0], i, time_opt[1]
        )
        j.append(bestsolution_ind_bestenergy)
    return j


def inv_ov(times_pop_cost, COE, r, h_deorbit=500, h_min=200):
    """Input:
    times_pop_cost = time_optimization_of_deltaV_population(pop, COE,
                    obj_fun=path_cost, h_deorbit=h_deorbit, h_min=h_min)
    COE = COE_function_of_time(df, indices, ts, pert)
    r: probability of a random inversion
    h_deorbit: altitude at which the shuttle leaves the target for its
               deorbiting in km
    h_min: minimum safety altitude above which the shuttle can orbit
           in km

    Return:
    times_pop_cost optimized
    """

    for tic in times_pop_cost:
        i_sel_original = np.copy(tic.i)
        d1 = np.random.choice(tic.i)
        while True:
            if np.random.random() < r:
                index_d2 = np.random.choice(range(len(tic.i) - 1))
                if tic.i[index_d2] == d1:
                    d2 = tic.i[len(tic.i) - 1]
                else:
                    d2 = tic.i[index_d2]
            else:
                index_i_rand = np.random.choice(
                    range(len(times_pop_cost) - 1)
                )
                if times_pop_cost[index_i_rand] is tic:
                    i_rand = times_pop_cost[len(times_pop_cost) - 1].i
                else:
                    i_rand = times_pop_cost[index_i_rand].i
                index_d1 = int(np.argwhere(i_rand == d1))
                if index_d1 == len(i_rand) - 1:
                    d2 = i_rand[0]
                else:
                    d2 = i_rand[index_d1 + 1]
            index_d1_i_sel = int(np.argwhere(tic.i == d1))
            index_d2_i_sel = int(np.argwhere(tic.i == d2))
            if abs(index_d1_i_sel - index_d2_i_sel) == 1:

                new_cost = path_cost(
                    tic.times_array,
                    tic.i,
                    COE,
                    h_deorbit=h_deorbit,
                    h_min=h_min
                )
                if new_cost < tic.cost:
                    tic.cost = new_cost
                    break
                else:
                    dim = len(tic.i)
                    NP = len(times_pop_cost)
                    obj_fun = path_cost
                    t_min = COE[1]
                    t_max = COE[2]
                    constraint = make_constr(t_min, t_max)
                    extra_args = (tic.i, COE, h_deorbit, h_min)
                    time_opt = time_optimization_of_deltaV(
                        dim, NP, obj_fun, constraint, t_min, t_max,
                        extra_args
                    )
                    if time_opt[1] < tic.cost:
                        tic.times_array = time_opt[0]
                        tic.cost = time_opt[1]
                        break
                    else:
                        tic.i = i_sel_original
                        break

            elif index_d2_i_sel - index_d1_i_sel >= 2:
                if index_d2_i_sel == len(tic.i) - 1:
                    d1 = tic.i[0]
                    tic.i[index_d1_i_sel +
                        1:] = tic.i[index_d2_i_sel:index_d1_i_sel:-1]
                else:
                    d1 = tic.i[index_d2_i_sel + 1]
                    tic.i[index_d1_i_sel + 1:index_d2_i_sel +
                        1] = tic.i[index_d2_i_sel:index_d1_i_sel:-1]
            else:
                if index_d2_i_sel == 0:
                    d1 = tic.i[-1]
                    tic.i[index_d2_i_sel:index_d1_i_sel] = tic.i[
                        index_d1_i_sel - 1::-1]
                else:
                    d1 = tic.i[index_d2_i_sel - 1]
                    tic.i[index_d2_i_sel:index_d1_i_sel] = tic.i[
                        index_d1_i_sel - 1:index_d2_i_sel - 1:-1]
    return times_pop_cost


def inver_over(
    times_pop_cost,
    COE,
    r,
    h_deorbit=500,
    h_min=200,
    generations0=5,
    generations=5
):
    for n in range(generations0):
        print(
            "Loop 0: Generation {} out of {}".format(
                n, max(range(generations0))
            )
        )
        tpc = inv_ov(
            times_pop_cost, COE, r, h_deorbit=h_deorbit, h_min=h_min
        )
        times_pop_cost = tpc
        np.save(
            "Loop 0: Generation {} out of {}".format(
                n, max(range(generations0))
            ), times_pop_cost
        )
        print([tic.cost for tic in times_pop_cost])
    min_cost1 = min(tic.cost for tic in times_pop_cost)
    gen = 1
    while True:
        for n in range(generations):
            print(
                "Loop {}: Generation {} out of {}".format(
                    gen, n, max(range(generations))
                )
            )
            tpc = inv_ov(
                times_pop_cost,
                COE,
                r,
                h_deorbit=h_deorbit,
                h_min=h_min
            )
            times_pop_cost = tpc
            np.save(
                "Loop {}: Generation {} out of {}".format(
                    gen, n, max(range(generations))
                ), times_pop_cost
            )
            print([tic.cost for tic in times_pop_cost])
        min_cost2 = min(tic.cost for tic in times_pop_cost)
        print(min_cost1, min_cost2)
        if min_cost1 - min_cost2 <= 1e-3 * (min_cost1 + min_cost2) / 2:
            break
        else:
            min_cost1 = min_cost2
            gen = gen + 1
    return [item for item in times_pop_cost if item.cost == min_cost2]