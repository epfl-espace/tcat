import numpy as np
from astropy import units as u
from astropy.time import Time
from poliastro.bodies import Earth, Moon
from poliastro.twobody import Orbit
from Phases.Manoeuvre import Manoeuvre
from Scenarios.ScenarioParameters import EP_DUTY_CYCLE, EP_COAST_CYCLE

def orbit_string(orbit):
    """Custom function to display orbit altitudes over ground. """
    orbit_apogee_alt = orbit.a * (1 + orbit.ecc) - Earth.R
    orbit_perigee_alt = orbit.a * (1 - orbit.ecc) - Earth.R
    return ("{0:.0f}".format(orbit_perigee_alt) + " x " + "{0:.0f}".format(orbit_apogee_alt)
            + ", inc: {0:.1f}".format(orbit.inc)
            + ", raan: {0:.0f}".format(orbit.raan % (360 * u.deg))
            + ", nu: {0:.0f}".format(orbit.nu % (360 * u.deg))
            + ", ltan {0:.0f}".format((orbit.raan-mean_sun_long(julian_day(orbit.epoch.to_datetime()))) % (360 * u.deg))
            )

def nodal_precession(orbit):
    """Returns the nodal precession period and speed of an object orbiting a body.
    Based on J2 perturbations only. Positive is eastward.
    
    Args:
        orbit (poliastro.twobody.Orbit): orbit we want to know the precession of
        
    Return:
        (u.day): period of precession
        (u.deg / u.day): angular speed of precession
    """
    body = orbit.attractor
    nodal_precession_period = orbit.period / (-1.5 * body.R**2 /
                                              (orbit.a * (1 - orbit.ecc**2))**2 * body.J2 * np.cos(orbit.inc.to(u.rad)))
    nodal_precession_speed = 360 * u.deg / nodal_precession_period
    return nodal_precession_period.to(u.day), nodal_precession_speed.to(u.deg / u.day)


def mean_sun_long(jde):  # Mean sun longitude at JDE (from algo [1]p.183)
    """Return mean sun longitude for reference"""
    tau = (jde - 2451545.0) / 365.250
    earth_draan = 360.0076982776  # 360/365.24199 * 365.25 # deg/year
    l0 = 280.4664567 + earth_draan * tau
    # TODO: A INTEGRER PLUS TARD
    # + 0.03032028 * tau**2 + tau**3/49931 - tau**4/15300 - tau**5/2000000
    return l0 * u.deg


def julian_day(datetime):
    """from epoch give JDE"""
    date = datetime
    year = date.year
    month = date.month
    output_julian_day = date.day + (date.hour + (date.minute + date.second/60)/60)/24
    if month <= 2:
        year = year-1
        month = month+12
    a = np.floor(year/100)
    b = 2 - a + np.floor(a/4)
    output_julian_day = np.floor(365.25*(year+4716)) + np.floor(30.6001*(month+1)) + output_julian_day + b - 1524.5
    return output_julian_day


def inclination_from_precession(orbit, nodal_precession_period=1*u.year, direction='eastward'):
    """ Returns inclination of orbit necessary to match a desired precession.
    The default precession period and direction corresponds to an SSO orbit.

    Args:
        orbit (poliastro.twobody.Orbit): initial orbit; to compute the inclination, its other orbital elements are used
        nodal_precession_period (u.<time unit>): desired precession period for one revolution
        direction (string): eastward or westward, gives the direction of the precession desired

    Return:
        (u.deg): required inclination
    """
    body = orbit.attractor
    temp = (orbit.period / (-1.5 * body.R**2 /
                            (orbit.a * (1 - orbit.ecc**2))**2 * body.J2 * nodal_precession_period)).to(u.m/u.m)
    if temp > 1.:
        raise Exception('Unattainable precession period specified.')
    else:
        inclination = np.arccos(temp)
        if direction == 'westward':
            inclination = 180 * u.deg - inclination
        return inclination.to(u.deg)


def instant_orbital_velocity(orbit, radius):
    """ Returns instantaneous orbital velocity at a particular distance from attractor.
    Used during delta v calculations.

     Args:
        orbit (poliastro.twobody.Orbit): orbit
        radius (u.<distance unit>): distance to the center of the attractor

    Return:
        (u.deg): orbital speed at distance given in argument
    """
    # Check if radius is smaller than apogee plus 1m to account for rounding errors.
    if radius > orbit.r_a + 1 * u.m:
        raise Exception('Unattainable radius specified.', radius, orbit)
    # compute speed
    body = orbit.attractor
    speed = np.sqrt(body.k * (2./radius - 1/orbit.a)).to(u.m / u.s)
    return speed.to(u.m/u.s)


def inclination_change_delta_v(initial_orbit, final_orbit):
    """ Returns delta_v necessary to change inclination from initial to final orbital plane.
    This only includes inclination change.

    Args:
        initial_orbit (poliastro.twobody.Orbit): initial orbit
        final_orbit (poliastro.twobody.Orbit): final orbit

    Return:
        (u.m / u.s): delta v necessary for inclination change
    """
    body = initial_orbit.attractor
    delta_i = final_orbit.inc - initial_orbit.inc
    ecc = initial_orbit.ecc
    w = initial_orbit.argp
    a = max(initial_orbit.a, final_orbit.a)
    n = np.sqrt(body.k / a**3)
    f = -initial_orbit.argp
    delta_v = abs(2 * np.sin(delta_i / 2.) * (np.sqrt(1-ecc**2)*np.cos(w + f)*n*a) / (1 + ecc * np.cos(f)))
    return delta_v.to(u.m / u.s)


def high_thrust_delta_v(initial_orbit, final_orbit, initial_mass, mean_thrust, isp, no_2n_burn=False):
    """Returns the delta v necessary to perform an orbit change, assuming impulsive maneuvers.
    This takes into account the transfer from one elliptical orbit to another.
    This takes into account possible inclination changes, performed during the adequate impulse.
    This neglects argument of periapsis changes.
    
    Args:
        initial_orbit (poliastro.twobody.Orbit): initial orbit
        final_orbit (poliastro.twobody.Orbit): final orbit
        initial_mass (u.kg) assumed servicer mass at start of maneuver
        mean_thrust (u.N): assumed thrust at start of maneuver
        isp (u.s): assumed isp, used to estimate manoeuvre duration
        no_2n_burn (bool): used to decide if the second burn is computed or if the spacecraft has already burnt in the atmosphere

    Return:
        (u.m / u.s): total delta v to reach final orbit
        (poliastro.twobody.Orbit): transfer orbit if applicable
        (u.m / u.s): first impulse
        (u.m / u.s): second impulse
        (u.day): first impulse duration
        (u.day): second impulse duration
        (u.day): total orbit change duration
    """
    maneouvres = []
    # compute delta v for inclination change and find if inclination needs to be done during first or second impulse
    inc_delta_v = inclination_change_delta_v(initial_orbit, final_orbit)
    if initial_orbit.a > final_orbit.a:
        first_inc_delta_v = inc_delta_v
        second_inc_delta_v = 0. * u.m/u.s
    else:
        first_inc_delta_v = 0. * u.m/u.s
        second_inc_delta_v = inc_delta_v

    # let's simplify the problem by neglecting argument of periapsis changes
    # we suppose arguments of periapsis are either aligned or opposed
    # TODO: introduce argument of periapsis changes
    first_burn_radius = initial_orbit.r_a
    if abs(final_orbit.argp - initial_orbit.argp) < 180. * u.deg:
        second_burn_radius = final_orbit.r_p
    else:
        second_burn_radius = final_orbit.r_a

    # find transfer orbit, neglecting argument of periapsis change
    a = (first_burn_radius + second_burn_radius) / 2.
    ecc = abs(first_burn_radius - second_burn_radius) / (first_burn_radius + second_burn_radius)
    transfer_orbit = Orbit.from_classical(final_orbit.attractor, a, ecc, final_orbit.inc, final_orbit.raan,
                                          final_orbit.argp, final_orbit.nu, final_orbit.epoch)

    if final_orbit.attractor != initial_orbit.attractor:
        raise ValueError("Initial and final orbits have different attractors.")

    # first burn
    v_i_1 = instant_orbital_velocity(initial_orbit, first_burn_radius)
    v_f_1 = instant_orbital_velocity(transfer_orbit, first_burn_radius)
    delta_v_1 = np.sqrt((v_f_1 - v_i_1)**2 + first_inc_delta_v**2)
    manoeuvre = Manoeuvre(delta_v_1,"first high-trust dV")
    manoeuvre.compute_burn_duration(initial_mass, mean_thrust, isp)
    maneouvres.append(manoeuvre)

    if no_2n_burn is False:
        # second burn
        v_i_2 = instant_orbital_velocity(transfer_orbit, second_burn_radius)
        v_f_2 = instant_orbital_velocity(final_orbit, second_burn_radius)
        delta_v_2 = np.sqrt((v_f_2 - v_i_2)**2 + second_inc_delta_v**2)
        manoeuvre = Manoeuvre(delta_v_2,"second high-trust dV")
        manoeuvre.compute_burn_duration(initial_mass, mean_thrust, isp)
        maneouvres.append(manoeuvre)

    transfer_duration = (transfer_orbit.period / 2).to(u.day)

    return maneouvres, transfer_duration


def low_thrust_delta_v(initial_orbit, final_orbit, initial_mass, mean_thrust, isp):
    """Returns the delta v necessary to perform the phase, assuming low thrust maneuvers (Edelbaum).
    Edelbaum's main assumptions are:
    1) propulsive thrust is continuous during the transfer,
    2) thrust acceleration is constant during the transfer,
    3) the transfer is quasi circular (eccentricity remains zero),
    4) the magnitude of the out-of-plane (yaw) steering angle is held constant during an orbital revolution.

    This does not take into account the transfer from one elliptical orbit to another, only circular orbits are valid.
    This takes into account possible inclination changes.
    This neglects argument of periapsis changes.
    Based on initial thrust and mass, the acceleration is supposed constant throughout the maneuver.
        
    Args:
        initial_orbit (poliastro.twobody.Orbit): initial orbit
        final_orbit (poliastro.twobody.Orbit): final orbit
        initial_mass (u.kg) assumed servicer mass at start of maneuver
        mean_thrust (u.N): assumed thrust at start of maneuver
        isp (u.s): assumed isp, used to estimate manoeuvre duration

    Return:
        (u.m / u.s): required total delta v
        (u.day): maneuver duration
    """
    maneouvres = []
    # TODO: include eccentricity changes correctly, current implementation is not valid for big changes in eccentricity
    if initial_orbit.ecc > 0.1 or final_orbit.ecc > 0.1:
        raise Exception('Use of Edelbaum not valid for elliptic orbits')
        
    # compute necessary inputs for Edelbaum formulations
    initial_radius = (initial_orbit.r_a + initial_orbit.r_p) / 2
    final_radius = (final_orbit.r_a + final_orbit.r_p) / 2
    v_0 = instant_orbital_velocity(initial_orbit, initial_radius)
    v_f = instant_orbital_velocity(final_orbit, final_radius)
    delta_i = final_orbit.inc - initial_orbit.inc

    # compute delta v for total maneuver
    delta_v = np.sqrt(v_0**2 + v_f**2 - 2*v_0*v_f*np.cos(np.pi/2 * delta_i))
    manoeuvre = Manoeuvre(delta_v,"low-trust maneuver")
    manoeuvre.compute_burn_duration(initial_mass, mean_thrust, isp)
    maneouvres.append(manoeuvre)

    transfer_duration = manoeuvre.get_burn_duration(duty_cycle=EP_DUTY_CYCLE)/(1-EP_COAST_CYCLE)

    return maneouvres, transfer_duration


def compute_altitude_maintenance_delta_v(duration, orbit):
    """ Returns an estimation of delta v required to maintain an orbit in altitude for a duration.

     Args:
        duration (u.<time unit>): total time spent on orbit
        orbit (poliastro.twobody.Orbit): orbit to maintain

    Return:
        (u.m / u.s): required delta v
    """
    if orbit.attractor == Earth:
        altitude = orbit.a - orbit.attractor.R
        delta_v_per_year = 9.0e18 * altitude.to(u.km).value**(-6.746) * u.m / u.s / u.year
        delta_v = (delta_v_per_year * duration.to(u.year)).to(u.m / u.s)
        manoeuvre = Manoeuvre(delta_v,id="altitude maintenance")
        manoeuvre.burn_duration = duration
        return manoeuvre
    elif orbit.attractor == Moon:
        delta_v_per_year = 50 *u.m / u.s / u.year
        delta_v = (delta_v_per_year * duration.to(u.year)).to(u.m / u.s)
        manoeuvre = Manoeuvre(delta_v,id="altitude maintenance")
        manoeuvre.burn_duration = duration
        return manoeuvre
    else:
        raise ValueError(f"{orbit.attractor} is not yet included in this model. Please wait for updates.")

def high_thrust_raan_change_delta_v(delta_raan, initial_orbit, final_orbit, initial_mass, mean_thrust, isp):
    """ Returns a rough estimation of delta_v needed to perform a small change in raan.
    This is not valid for large maneuvers, only maintenance or corrections."""
    delta_raan = delta_raan % (360 * u.deg)
    if delta_raan > 180. * u.deg:
        delta_raan -= 360. * u.deg

    mean_a = (final_orbit.a + initial_orbit.a) / 2
    mean_inc = (final_orbit.inc + initial_orbit.inc) / 2
    vel = np.sqrt(initial_orbit.attractor.k / mean_a.to(u.m))
    d_inc_ratio = np.sin(mean_inc.to(u.rad))
    delta_v = np.pi / 2 * vel * d_inc_ratio * abs(delta_raan.to(u.rad).value)

    manoeuvre = Manoeuvre(delta_v,id="high trust direct raan change")
    manoeuvre.compute_burn_duration(initial_mass, mean_thrust, isp)
    transfer_duration = (final_orbit.period / 2).to(u.day)

    return manoeuvre, transfer_duration


def low_thrust_raan_change_delta_v(delta_raan, initial_orbit, final_orbit, initial_mass, mean_thrust, isp):
    """ Returns a rough estimation of delta_v needed to perform a small change in raan.
    This is not valid for large maneuvers, only maintenance or corrections."""
    delta_raan = delta_raan % (360 * u.deg)
    if delta_raan > 180. * u.deg:
        delta_raan -= 360. * u.deg
    mean_a = (final_orbit.a + initial_orbit.a) / 2
    mean_inc = (final_orbit.inc + initial_orbit.inc) / 2
    delta_v = np.pi / 2 * (np.sqrt(initial_orbit.attractor.k / mean_a) * np.sin(mean_inc.to(u.rad).value)
                           * abs(delta_raan.to(u.rad).value))

    manoeuvre = Manoeuvre(delta_v,id="low trust direct raan change")
    manoeuvre.compute_burn_duration(initial_mass, mean_thrust, isp)
    transfer_duration = manoeuvre.get_burn_duration(duty_cycle=EP_DUTY_CYCLE)/(1-EP_COAST_CYCLE)

    return manoeuvre, transfer_duration

def update_orbit(orbit, reference_epoch,starting_epoch=None):
    """ Update an orbit to a further reference epoch by adding raan drift, only if the main body is Earth.

    Args:
        orbit (poliastro.twobody.Orbit): orbit to be updated
        reference_epoch (astropy.time.Time): epoch to which the orbit needs to be updated

    Return:
        (poliastro.twobody.Orbit): orbit at reference epoch

    TODO: implement more complex things like altitude loses or lack of orbit maintenance
    """
    if starting_epoch is not None:
        orbit = Orbit.from_classical(orbit.attractor, orbit.a, orbit.ecc,
                                     orbit.inc, orbit.raan,
                                     orbit.argp, orbit.nu,
                                     starting_epoch)
                                     
    time_since_epoch = reference_epoch - orbit.epoch
    if time_since_epoch < 0:
        raise Exception('Error in timing propagation in Orbit Change.'
                        + str(time_since_epoch) + str(reference_epoch) + str(orbit.epoch))

    if orbit.attractor == Earth:
        raan_drift_since_epoch = nodal_precession(orbit)[1] * time_since_epoch
    else:
        raan_drift_since_epoch = 0.*u.deg
    current_raan = (orbit.raan + raan_drift_since_epoch).to(u.deg) % (360 * u.deg)
    if current_raan > 180. * u.deg:
        current_raan = current_raan - 360. * u.deg
    if current_raan <= -180. * u.deg:
        current_raan = current_raan + 360. * u.deg

    new_orbit = Orbit.from_classical(orbit.attractor, orbit.a, orbit.ecc,
                                     orbit.inc, current_raan,
                                     orbit.argp, orbit.nu,
                                     orbit.epoch)
    new_orbit = new_orbit.propagate(time_since_epoch)
    return new_orbit

def get_reentry_parameters(orbit, altitude=100. * u.km):
    """

    Args:
        orbit (poliastro.twobody.Orbit): orbit to be updated
        altitude (u.<length unit>): reentry altitude at which the parameters are computed
    Return:
        reentry_true_anomaly (u.<angle unit>): true anomaly at time of reentry
        reentry_velocity (u.<speed unit>): object velocity at time of reentry
        reentry_angle (u.<angle unit>): angle between object trajectory and local horizontal at time of reentry
    """
    reentry_radius = altitude + Earth.R
    reentry_true_anomaly = np.arccos((orbit.a * (1 - orbit.ecc**2) - reentry_radius) / (orbit.ecc * reentry_radius))
    reentry_angle = np.arctan((orbit.a * (1 - orbit.ecc**2) / reentry_radius * orbit.ecc * np.sin(reentry_true_anomaly)
                              / (1 + orbit.ecc * np.cos(reentry_true_anomaly))**2))
    if reentry_angle.value < 0.:
        reentry_angle = reentry_angle + 360. * u.deg
    reentry_velocity = instant_orbital_velocity(orbit, reentry_radius)
    return reentry_true_anomaly.to(u.deg), reentry_velocity.to(u.m/u.s), reentry_angle.to(u.deg)

def compute_translunar_injection(initial_orbit, final_orbit):
    """Returns the delta v and duration necessary to perform a translunar injection, assuming impulsive maneuvers.
    This takes into account the following assumptions:
    (1) the Earth planet is fixed in space;
    (2) the Moon orbit around the Earth is circular;
    (3) the flight of the space vehicle lies in the orbital plane of the Moon;
    (4) the gravitational field of the Earth and the Moon is central and obeys the inverse square
        law;
    (5) the transfer trajectory has two distinct phases: the geocentric phase, which it starts immediately
        after the first velocity increment; and the selenocentric phase, which begins when
        the vehicle reaches the sphere of influence of the Moon;
    (6) the two-impulse model is considered. Each velocity increment is applied tangentially to
        the initial orbit (LEO) and the final (LMO) orbit.

    REF: "Optimal round trip lunar missions based on the patched-conic approximation" DOI 10.1007/s40314-015-0247-y
    :param initial_orbit (poliastro.twobody.Orbit): initial orbit
    :param final_orbit (poliastro.twobody.Orbit): final orbit
    :return:
            (u.m / u.s): total delta v to reach final orbit around the Moon
            (u.m / u.s): first impulse
            (u.m / u.s): second impulse
            (u.day): total time of flight
            (u.day): time of flight in the geocentric phase
            (u.day): time of flight in the selenocentric phase
            (u.deg): initial phase angle between the space vehicle and the Moon at the moment of the first impulse
    """

    # CONSTANTS
    D = (384400 * u.km).to(u.m)  # distance Earth-Moon
    R_s = (66300 * u.km).to(u.m)  # radius of the moon's sphere of influence
    v_M = (1.018 * u.km / u.s).to(u.m / u.s)  # Moon's mean orbital velocity
    mu_E = Earth.k
    mu_M = Moon.k

    # INPUTS
    phi_0 = 0 * u.deg  # flight path angle
    r_0 = initial_orbit.r_p.to(u.m)
    v_c = np.sqrt(mu_E / r_0)  # circular velocity
    lambda_1 = 75 * u.deg
    r_f = final_orbit.r_p.to(u.m)  # desired final radius
    counter1 = 0
    counter2 = 0
    tol = 10. * u.km

    # simple Hohmann transfer to compute a first guess of v_0
    start = Orbit.from_classical(Earth, 2 * r_0, 0 * u.one, 23 * u.deg, 0 * u.deg, 90 * u.deg, 180 * u.deg,
                                 Time("2025-01-01 12:00:00", scale="tdb"))
    moon = Orbit.from_classical(Earth, 2 * D, 0 * u.one, 23 * u.deg, 0 * u.deg, 90 * u.deg, 180 * u.deg,
                                Time("2025-01-01 12:00:00", scale="tdb"))
    v_ht, _, _, _, _ = high_thrust_delta_v(start, moon)
    v_0 = v_ht + v_c

    while abs(tol) > 5 * u.km:
        counter1 += 1
        counter2 += 1
        epsilon = 0.5 * v_0 ** 2 - mu_E / r_0
        r_1 = np.sqrt(D ** 2 + R_s ** 2 - 2 * D * R_s * np.cos(lambda_1))
        # phase angle of the spacecraft with the Moon with respect to the Earth
        gamma_1 = np.arcsin(R_s * np.sin(lambda_1) / r_1)
        while epsilon + mu_E / r_1 < 0 * u.m ** 2 / u.s ** 2:
            v_0 = v_0 + 0.05 * u.km / u.s
            epsilon = 0.5 * v_0 ** 2 - mu_E / r_0
        counter2 = 1
        h_1 = r_0 * v_0 * np.cos(phi_0)
        v_1 = np.sqrt(2 * (epsilon + mu_E / r_1))
        phi_1 = np.arccos(h_1 / (r_1 * v_1))
        v_2 = np.sqrt(v_1 ** 2 + v_M ** 2 - 2 * v_1 * v_M * np.cos(phi_1 - gamma_1))
        phi_2 = np.arctan(-v_1 * np.sin(phi_1 - gamma_1) / (v_M - v_1 * np.cos(phi_1 - gamma_1))) - lambda_1

        # Selenocentric trajectory

        Q_2 = (R_s * v_2 ** 2) / mu_M
        a_f = R_s / (2 - Q_2)
        e_f = np.sqrt(1 + Q_2 * (Q_2 - 2) * (np.cos(phi_2)) ** 2)

        # periapsis of the selenocentric trajectory

        r_pM = a_f * (1 - e_f)
        v_pM = np.sqrt(mu_M * (1 + e_f) / r_pM)

        # Newton–Raphson algorithm:

        # Derivatives
        d_v_1d_v_0 = v_0 / v_1
        d_phi_1d_v_0 = np.cos(phi_1) / (v_1 * np.sin(phi_1) * (v_0 / v_1 - v_1 / v_0))
        d_v_2d_v_0 = (v_1 - v_M * np.cos(phi_1 - gamma_1)) / v_2 * d_v_1d_v_0 + (
                v_1 * v_M * np.sin(phi_1 - gamma_1)) / v_2 * d_phi_1d_v_0
        d_phi_2d_v_1 = -v_M * np.sin(phi_1 - gamma_1) / v_2 ** 2
        d_phi_2d_phi_1 = (-v_1 * v_M * np.cos(phi_1 - gamma_1) + v_1 ** 2) / v_2 ** 2
        d_phi_2d_v_0 = d_phi_2d_v_1 * d_v_1d_v_0 + d_phi_2d_phi_1 * d_phi_1d_v_0
        d_e_fd_v_0 = 2 * Q_2 * (Q_2 - 1) * (np.cos(phi_2)) ** 2 / (e_f * v_2) * d_v_2d_v_0 - Q_2 * (Q_2 - 2) * np.cos(
            phi_2) * np.sin(phi_2) / e_f * d_phi_2d_v_0
        d_a_fd_v_0 = 2 * a_f ** 2 * v_2 / mu_M * d_v_2d_v_0
        d_r_pMd_v_0 = d_a_fd_v_0 * (1 - e_f) - d_e_fd_v_0 * a_f

        v_0 = v_0 + (r_f - r_pM) / d_r_pMd_v_0
        tol = r_f - r_pM

    # delta-V

    delta_v_LEO = v_0 - np.sqrt(mu_E / r_0)  # velocity increment at LEO
    delta_v_LMO = v_pM - np.sqrt(mu_M / r_f)  # velocity increment at LMO
    delta_v_TOT = delta_v_LEO + delta_v_LMO

    # time of flight

    Q_0 = (r_0 * v_0 ** 2) / mu_E
    a_0 = r_0 / (2 - Q_0)
    e_0 = np.sqrt(1 + Q_0 * (Q_0 - 2) * (np.cos(phi_0) ** 2))
    E_1 = np.arccos((1 - r_1 / a_0) / e_0)  # Eccentric anomaly
    F_2 = np.arccosh((1 - R_s / a_f) / e_f)  # Hyperbolic anomaly

    # Time of flight in the geocentric phase
    delta_t_E = np.sqrt(a_0 ** 3 / mu_E) * (E_1.value - e_0 * np.sin(E_1))
    # Time of flight in the selenocentric phase
    delta_t_M = np.sqrt((-a_f) ** 3 / mu_M) * (e_f * np.sinh(F_2) - F_2.value)
    delta_t_TOT = delta_t_E + delta_t_M

    # Initial phase angle:

    # true anomaly at the contact point of the geocentric trajectory with the sphere of influence of the Moon
    f_1 = np.arccos((np.cos(E_1) - e_0) / (1 - e_0 * np.cos(E_1)))
    # true anomaly at the insertion point in the geocentric trajectory
    f_0 = 0 * u.rad
    # angular velocity of the Moon’s orbit around the Earth
    omega_M = np.sqrt(mu_E / D ** 3)
    # initial phase angle between the space vehicle and the Moon at the moment of the first impulse
    gamma_0 = -(f_1 - f_0 - gamma_1 - (omega_M * delta_t_E) * u.rad)
    # TODO: add launch-window based on phase angle between the two bodies
    # TODO: add return phase calculations

    return delta_v_TOT, delta_v_LEO, delta_v_LMO, delta_t_TOT.to(u.day), delta_t_E.to(u.day), delta_t_M.to(u.day), gamma_0.to(u.deg)
