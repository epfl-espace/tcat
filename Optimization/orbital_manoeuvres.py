import numpy as np
from scipy.optimize import (minimize_scalar, basinhopping, differential_evolution, minimize)

# from poliastro.constants import GM_earth
import matplotlib.pyplot as plt

# TODO: do not use poliastro values
# GM_earth = GM_earth.value / 1e9  # km**3 / s**2
GM_earth = 3.986004418e14 / 1e9  # km**3 / s**2
R_earth = 6.3710084e3  # km


def cross(x, y):
    # TODO: replace with np.cross if performance is similar
    return np.array(
        [
            x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2],
            x[0] * y[1] - x[1] * y[0]
        ]
    )


def n_versor(raan):
    """Input:
    raan: right ascension of the ascending node in radians

    Return:
    array (vector) containing the components, in the
    Geocentric-Equatorial frame, of the line of nodes versor
    """

    return np.array([np.cos(raan), np.sin(raan), 0])


def m_versor(raan, i):
    """Input:
    raan: right ascension of the ascending node in radians
    i: inclination in radians

    Return:
    array (vector) containing the components, in the
    Geocentric-Equatorial frame, of the versor in the orbital plane
    perpendicular to the line of nodes
    """

    return np.array(
        [
            -np.sin(raan) * np.cos(i),
            np.cos(raan) * np.cos(i),
            np.sin(i)
        ]
    )


def p_vector(raan, i):
    """Input:
    raan: right ascension of the ascending node in radians
    i: inclination in radians

    Return:
    array (vector) containing the components, in the
    Geocentric-Equatorial frame, of the vector perpendicular
    to the orbital plane
    """

    n = n_versor(raan)
    m = m_versor(raan, i)
    return cross(n, m)  # TODO use np.cross


def p_versor(raan, i):
    p = p_vector(raan, i)
    return p / np.sqrt(p.dot(p))  # TODO:substitute np.sqrt(p.dot(p)) with np.linalg.norm(p)


def theta_angle(raan1, i1, raan2, i2):
    """Input:
    raan1: first orbital plane's right ascension of the ascending node
           in radians
    i1: first orbital plane's inclination in radians
    raan2: second orbital plane's right ascension of the ascending node
           in radians
    i2: second orbital plane's inclination in radians

    Return:
    angle between the two orbital planes in radians
    """

    p1 = p_versor(raan1, i1)
    p2 = p_versor(raan2, i2)
    cos_theta = np.dot(p1, p2)
    if abs(cos_theta) < 0.7:    #TODO: delete this if-cycle if not necessary
        return np.arccos(cos_theta)
    else:
        p1_p2 = cross(p1, p2)
        sin_theta = np.sqrt(p1_p2.dot(p1_p2))
        if cos_theta >= 0:
            return np.arcsin(sin_theta)
        else:
            return np.pi - np.arcsin(sin_theta)


def velocity_circular_orbit(r):
    """Input:
    r: radius of the circular orbit in km

    Return:
    satellite velocity on a circular orbit in km/s
    """

    return np.sqrt(GM_earth / r)


def velocity_orbit(r, a):
    """Input:
    r: distance between the satellite and the focus of the conical orbit
    in km
    a: semimajor axis in km

    Return:
    satellite velocity in km/s
    """

    return np.sqrt(GM_earth * (2 / r - 1 / a))


def delta_V_carnot(x, y, beta):
    """Input:
    x: satellite velocity on the departure or arrival orbit
    y: satellite velocity on the transfer orbit
    beta: angle between x and y in radians

    Return:
    delta-V necessary for a change of plane of an angle beta
    """

    # Compute sqrt(x**2 + y**2 - 2*x*y*cos(beta))
    # in a numerically stable way:

    if x >= y:
        a = x - y * np.cos(beta)
        b = y * np.sin(beta)
    else:
        a = y - x * np.cos(beta)
        b = x * np.sin(beta)
    return np.sqrt(a * a + b * b)


def delta_V_tot_HT(r1, r2):
    """Input:
    r1: radius of the circular departure orbit in km
    r2: radius of the circular arrival orbit in km

    Return:
    delta-V necessary for the transfer between a circular departure
    orbit (r1) and a circular arrival orbit (r2) in the same plane
    with an Hohmann Transfer in km/s
    """

    vc1 = velocity_circular_orbit(r1)
    vPt = velocity_orbit(r1, (r1 + r2) / 2)
    vc2 = velocity_circular_orbit(r2)
    vAt = velocity_orbit(r2, (r1 + r2) / 2)
    delta_V1 = abs(vPt - vc1)
    delta_V2 = abs(vc2 - vAt)
    return delta_V1 + delta_V2


def delta_V_tot_TIGM(rt, alpha1, alpha2, r, theta):
    """Input:
    rt: apogee of the elliptical transfer orbits in km
    alpha1: angle between the departure orbit and the first elliptical
    transfer orbit in radians
    alpha2: angle between the first elliptical transfer orbit and the
    second elliptical transfer orbit in radians
    r: radius of the circular orbits in km
    theta: angle between the departure orbit and the arrival orbit
    in radians

    Return:
    delta-V necessary for the transfer between a circular departure
    orbit and a circular arrival orbit with the same radius (r)
    separated by an angle theta with a Three-Impulse Generalized
    Maneuver in km/s
    """

    vc = velocity_circular_orbit(r)
    vP = velocity_orbit(r, (r + rt) / 2)
    vA = velocity_orbit(rt, (r + rt) / 2)
    delta_V1 = delta_V_carnot(vc, vP, alpha1)
    delta_V2 = 2 * vA * abs(np.sin(alpha2 / 2))
    delta_V3 = delta_V_carnot(vc, vP, theta - alpha1 - alpha2)
    return delta_V1 + delta_V2 + delta_V3


def delta_V_tot_TIGM_optimal(r, theta):
    """Input:
    r: radius of the circular orbits in km
    theta: angle between the departure orbit and the arrival orbit
    in radians

    Return:
    tuple containing:
    [0] optimal delta-V necessary for the transfer between a circular
    departure orbit and a circular arrival orbit with the same
    radius (r) separated by an angle theta in km/s
    [1] array [rt, alpha1, alpha2], with:
    rt: optimal apogee of the elliptical transfer orbits in km
    alpha1: optimal angle between the departure orbit and the first
    elliptical transfer orbit in radians
    alpha2: optimal angle between the first elliptical transfer
    orbit and the second elliptical transfer orbit in radians
    for a Three-Impulse Generalized Maneuver
    """
    # TODO: add orbits graphical view
    def f(x):
        rt, alpha1, alpha2 = x
        return delta_V_tot_TIGM(rt, alpha1, alpha2, r, theta)

    x0 = [r, np.deg2rad(4), np.deg2rad(25)]
    res = basinhopping(f, x0)
    return res.fun, res.x


def delta_V_tot_GHT(alpha, r1, r2, theta):
    """Input:
    alpha: angle between the departure orbit and the transfer orbit
    in radians
    r1: radius of the circular departure orbit in km
    r2: radius of the circular arrival orbit in km
    theta: angle between the departure orbit and the arrival orbit
    in radians

    Return:
    delta-V necessary for the transfer between a circular departure
    orbit (r1) and a circular arrival orbit (r2) separated by an angle
    theta with a Generalized Hohmann Transfer in km/s
    """
    # TODO: add orbits graphical view
    vc1 = velocity_circular_orbit(r1)
    vPt = velocity_orbit(r1, (r1 + r2) / 2)
    vc2 = velocity_circular_orbit(r2)
    vAt = velocity_orbit(r2, (r1 + r2) / 2)
    delta_V1 = delta_V_carnot(vc1, vPt, alpha)
    delta_V2 = delta_V_carnot(vc2, vAt, theta - alpha)
    return delta_V1 + delta_V2


def delta_V_tot_GHT_optimal(r1, r2, theta):
    """Input:
    r1: radius of the circular departure orbit in km
    r2: radius of the circular arrival orbit in km
    theta: angle between the departure orbit and the arrival orbit
    in radians

    Return:
    tuple containing:
    [0] optimal delta-V necessary for the transfer beetween a circular
    departure orbit (r1) and a circular arrival orbit (r2) separated
    by an angle theta in km/s
    [1] optimal angle alpha between the departure orbit and the transfer
    orbit in radians
    for a Generalized Hohmann Transfer
    """

    res = minimize_scalar(delta_V_tot_GHT, args=(r1, r2, theta))
    return res.fun, res.x


# For the purpose of building the cost vector and with the assumption of circular
# orbits and impulsive manoeuvres, the following Python functions are used:
def delta_V_tot_GBT(rt_alpha1_alpha2, r1, r2, theta):
    """Input:
    rt_alpha1_alpha2: np.array containing:
    [0] rt: apogee of the elliptical transfer orbits in km
    [1] alpha1: angle between the departure orbit (r1) and the first
    elliptical transfer orbit in radians
    [2] alpha2: angle between the first elliptical transfer orbit
    and the second elliptical transfer orbit in radians
    r1: radius of the departure circular orbit in km
    r2: radius of the arrival circular orbit in km
    theta: angle between the departure orbit and the arrival orbit
    in radians

    Return:
    delta-V necessary for the transfer beetween a circular departure
    orbit (r1) and a circular arrival orbit (r2) separated by an angle
    theta with a Generalized Bielliptical Transfer in km/s
    """

    rt, alpha1, alpha2 = rt_alpha1_alpha2
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


def delta_V_tot_GBT_optimal(r1, r2, theta):
    """Input:
    r1: radius of the departure circular orbit in km
    r2: radius of the arrival circular orbit in km
    theta: angle between the departure orbit and the arrival orbit
    in radians

    Return:
    tuple containing:
    [0] optimal delta-V necessary for the transfer beetween a circular
    departure orbit (r1) and a circular arrival orbit (r2) separated
    by an angle theta in km/s
    [1] array [rt, alpha1, alpha2], with:
    rt: optimal apogee of the elliptical transfer orbits in km
    alpha1: optimal angle between the departure orbit (r1) and the
    first elliptical transfer orbit in radians
    alpha2: optimal angle between the first elliptical transfer
    orbit and the second elliptical transfer orbit in radians
    for a Generalized Bielliptical Transfer
    """

    res = differential_evolution(
        delta_V_tot_GBT,
        [(min(r1, r2), 40000), (-np.pi, np.pi), (-np.pi, np.pi)],
        args=(r1, r2, theta)
    )
    res = minimize(
        delta_V_tot_GBT, res.x, method="BFGS", args=(r1, r2, theta)
    )
    return res.fun, res.x


def period_orbit(a):
    """Input:
    a: semimajor axis in km

    Return:
    orbital period in s
    """

    return 2 * np.pi * a ** (3 / 2) / np.sqrt(GM_earth)


def semimajor_axis(T):
    """Input:
    T: orbital period in s

    Return:
    semimajor axis in km
    """

    return (GM_earth * (T / (2 * np.pi)) ** 2) ** (1 / 3)


def period_orbit_min(r, h_min):
    """Input:
    r: radius of the circular orbit in km
    h_min: minimum safety altitude above which the satellite can orbit
    in km

    Return:
    minimum orbital period in s
    """

    return period_orbit((r + R_earth + h_min) / 2)


def n_upper_bound(trv, Tt_min):
    """Input:
    trv: time to be spent for the rendez-vous in s
    Tt_min: minimum orbital period in s

    Return:
    maximum number of rounds the satellite can travel on the
    transfer orbit
    """

    return int(trv / Tt_min)


def delta_t(r, lambda_angle):
    """Input:
    r: radius of the circular orbit in km
    lambda_angle: angle between the satellite and the target
    (in the same circular orbit) in radians

    Return:
    time needed by the target to travel (on the circular orbit)
    the angle (2pi-lambda_angle) in s
    """

    return (1 - lambda_angle / (2 * np.pi)) * period_orbit(r)


def m_rounds(r, lambda_angle, trv_max, h_min):
    """Input:
    r: radius of the circular orbit in km
    lambda_angle: angle between the satellite and the target
    (in the same circular orbit) in radians
    trv_max: maximum time to be spent for the rendez-vous in s
    h_min: minimum safety altitude above which the satellite can orbit
    in km

    Return:
    number of rounds the target travels on the circular orbit to satisfy
    the constraint on the maximum time allowed for the rendez-vous
    """

    dt = delta_t(r, lambda_angle)
    Tt_min = period_orbit_min(r, h_min)
    T = period_orbit(r)
    if dt >= Tt_min:
        assert trv_max >= dt, (
            "maximum time for the rendez-vous (trv_max) must be "
            "greater than or equal to dt = {} s"
        ).format(dt)
    else:
        assert trv_max >= dt + T, (
            "maximum time for the rendez-vous (trv_max) must be "
            "greater than or equal to dt + T = {} s"
        ).format(dt + T)
    m = (trv_max - dt) / T
    return int(m)


def time_rendez_vous(r, lambda_angle, trv_max, h_min):
    """Input:
    r: radius of the circular orbit in km
    lambda_angle: angle between the satellite and the target
    (in the same circular orbit) in radians
    trv_max: maximum time to be spent for the rendez-vous in s
    h_min: minimum safety altitude above which the satellite can orbit
    in km

    Return:
    time needed for the rendez-vous in s
    """

    m = m_rounds(r, lambda_angle, trv_max, h_min)
    return delta_t(r, lambda_angle) + m * period_orbit(r)


def delta_V_same_orbit(r, trv, n):
    """Input:
    r: radius of the circular orbit in km
    trv: time to be spent for the rendez-vous in s
    n: number of rounds the satellite travels on the transfer orbit

    Return:
    delta-V necessary for the change of phasing angle on a circular orbit
    travelling on an elliptical orbit in km/s
    """

    Tt = trv / n
    a = semimajor_axis(Tt)
    vc = velocity_circular_orbit(r)
    vt = velocity_orbit(r, a)
    return 2 * abs(vt - vc)


def delta_V_same_orbit_optimal(r, lambda_angle, trv_max, h_min):
    """Input:
    r: radius of the circular orbit in km
    lambda_angle: angle between the satellite and the target
    (in the same circular orbit) in radians
    trv_max: maximum time to be spent for the rendez-vous in s
    h_min: minimum safety altitude above which the satellite can orbit
    in km

    Return:
    tuple containing:
    [0] optimal delta-V necessary for the change of phasing angle on a circular
    orbit travelling on an elliptical orbit in km/s
    [1] number of rounds the satellite travels on the transfer orbit to
    have the optimal delta-V
    """

    Tt_min = period_orbit_min(r, h_min)
    m = m_rounds(r, lambda_angle, trv_max, h_min)
    trv = delta_t(r, lambda_angle) + m * period_orbit(r)
    n_max = n_upper_bound(trv, Tt_min)
    n_min = 1

    assert n_min <= n_max
    n = min(max(m, n_min), n_max)  # first guess

    n_best = n
    f_best = delta_V_same_orbit(r, trv, n)

    assert n_min <= n <= n_max
    n += 1
    while n <= n_max:
        f_cur = delta_V_same_orbit(r, trv, n)
        if f_cur < f_best:
            n_best = n
            f_best = f_cur
            n += 1
        else:
            break

    n = min(n, n_max)

    assert n_min <= n <= n_max
    n -= 1
    while n >= n_min:
        f_cur = delta_V_same_orbit(r, trv, n)
        if f_cur <= f_best:
            n_best = n
            f_best = f_cur
            n -= 1
        else:
            break

    return f_best, n_best
