import matplotlib.pyplot as plt

from ADRClient_module import *
from Fleet_module import *
from Modules.CaptureModule import *
from Modules.PropulsionModule import *
from Phases.Capture import *
from Phases.Insertion import *
from Phases.OrbitChange import *
from Phases.OrbitMaintenance import *
from Phases.Release import *
from Plan_module import *

SMALL_SIZE = 16
MEDIUM_SIZE = 20
BIGGER_SIZE = 24

plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=SMALL_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title

# Define starting epoch (here corresponding to launch date)
starting_epoch = Time("2025-06-02 12:00:00", scale="tdb")


def analysis_scenario(insertion_inclination, insertion_altitude, insertion_mlt):
    # initial raan of target at date
    target_initial_raan = (27. * u.deg + mean_sun_long(julian_day(starting_epoch.to_datetime()))) % (360. * u.deg)
    servicer_initial_raan = (insertion_mlt + mean_sun_long(julian_day(starting_epoch.to_datetime()))) % (360. * u.deg)

    # insertion orbit
    a = insertion_altitude + Earth.R
    ecc = 0. * u.rad / u.rad
    inc = insertion_inclination
    raan = servicer_initial_raan
    argp = 0. * u.deg
    nu = 0. * u.deg
    servicer_insertion_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, starting_epoch)

    # target operational orbit
    a = 7095.7 * u.km
    ecc = 0.0096 * u.rad / u.rad
    inc = 98.76 * u.deg
    raan = target_initial_raan
    argp = 136. * u.deg
    nu = 0. * u.deg
    target_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, starting_epoch)

    # reentry orbit by bringing perigee to 20 km
    apogee = target_orbit.a * (1+target_orbit.ecc)
    perigee = 50. * u.km + Earth.R
    a = (apogee+perigee) / 2
    ecc = (apogee-perigee) / (apogee+perigee)
    inc = target_orbit.inc
    raan = target_orbit.raan
    argp = target_orbit.argp
    nu = 0. * u.deg
    reentry_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, starting_epoch)

    # phasing orbit
    phasing_angle = (target_orbit.raan - servicer_insertion_orbit.raan) % (360. * u.deg)
    phasing_drift = nodal_precession(servicer_insertion_orbit)[1] - nodal_precession(target_orbit)[1]
    phasing_duration = -30.5 * u.day + phasing_angle / phasing_drift

    # first orbit raise
    apogee = servicer_insertion_orbit.a * (1+servicer_insertion_orbit.ecc) + 110. * u.km
    perigee = servicer_insertion_orbit.a * (1-servicer_insertion_orbit.ecc)
    a = (apogee+perigee) / 2
    ecc = (apogee-perigee) / (apogee+perigee)
    inc = servicer_insertion_orbit.inc
    raan = servicer_insertion_orbit.raan
    argp = servicer_insertion_orbit.argp
    nu = 0. * u.deg
    raise01_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, starting_epoch)

    # second orbit raise
    apogee = servicer_insertion_orbit.a * (1+servicer_insertion_orbit.ecc) + 220. * u.km
    perigee = servicer_insertion_orbit.a * (1-servicer_insertion_orbit.ecc)
    a = (apogee + perigee) / 2
    ecc = (apogee - perigee) / (apogee + perigee)
    inc = servicer_insertion_orbit.inc
    raan = servicer_insertion_orbit.raan
    argp = servicer_insertion_orbit.argp
    nu = 0. * u.deg
    raise02_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, starting_epoch)

    # third orbit raise
    apogee = target_orbit.a * (1 + target_orbit.ecc)
    perigee = servicer_insertion_orbit.a * (1 - servicer_insertion_orbit.ecc) + 50. * u.km
    a = (apogee + perigee) / 2
    ecc = (apogee - perigee) / (apogee + perigee)
    inc = servicer_insertion_orbit.inc + 0.2 * u.deg
    raan = servicer_insertion_orbit.raan
    argp = servicer_insertion_orbit.argp
    nu = 0. * u.deg
    raise03_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, starting_epoch)

    # first inclination correction
    apogee = raise03_orbit.a * (1 + raise03_orbit.ecc)
    perigee = raise03_orbit.a * (1 - raise03_orbit.ecc)
    a = (apogee + perigee) / 2
    ecc = (apogee - perigee) / (apogee + perigee)
    inc = servicer_insertion_orbit.inc - 0.25 * u.deg
    raan = servicer_insertion_orbit.raan
    argp = servicer_insertion_orbit.argp
    nu = 0. * u.deg
    inc01_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, starting_epoch)

    # second inclination correction
    apogee = inc01_orbit.a * (1 + inc01_orbit.ecc)
    perigee = inc01_orbit.a * (1 - inc01_orbit.ecc)
    a = (apogee + perigee) / 2
    ecc = (apogee - perigee) / (apogee + perigee)
    inc = servicer_insertion_orbit.inc - 0.5 * u.deg
    raan = servicer_insertion_orbit.raan
    argp = servicer_insertion_orbit.argp
    nu = 0. * u.deg
    inc02_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, starting_epoch)

    # third inclination correction
    apogee = inc02_orbit.a * (1 + inc02_orbit.ecc)
    perigee = inc02_orbit.a * (1 - inc02_orbit.ecc)
    a = (apogee + perigee) / 2
    ecc = (apogee - perigee) / (apogee + perigee)
    inc = servicer_insertion_orbit.inc - 0.75 * u.deg
    raan = servicer_insertion_orbit.raan
    argp = servicer_insertion_orbit.argp
    nu = 0. * u.deg
    inc03_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, starting_epoch)

    # fourth inclination correction
    apogee = inc03_orbit.a * (1 + inc03_orbit.ecc)
    perigee = inc03_orbit.a * (1 - inc03_orbit.ecc) + 50. * u.km
    a = (apogee + perigee) / 2
    ecc = (apogee - perigee) / (apogee + perigee)
    inc = target_orbit.inc
    raan = servicer_insertion_orbit.raan
    argp = servicer_insertion_orbit.argp
    nu = 0. * u.deg
    inc04_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, starting_epoch)

    # first lower perigee
    apogee = target_orbit.a * (1+target_orbit.ecc)
    perigee = target_orbit.a * (1-target_orbit.ecc) - 100. * u.km
    a = (apogee+perigee) / 2
    ecc = (apogee-perigee) / (apogee+perigee)
    inc = target_orbit.inc
    raan = target_orbit.raan
    argp = target_orbit.raan
    nu = 0. * u.deg
    lower01_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, starting_epoch)

    # second lower perigee
    apogee = target_orbit.a * (1 + target_orbit.ecc)
    perigee = target_orbit.a * (1 - target_orbit.ecc) - 200. * u.km
    a = (apogee + perigee) / 2
    ecc = (apogee - perigee) / (apogee + perigee)
    inc = target_orbit.inc
    raan = target_orbit.raan
    argp = target_orbit.raan
    nu = 0. * u.deg
    lower02_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, starting_epoch)

    # third lower perigee
    apogee = target_orbit.a * (1+target_orbit.ecc)
    perigee = target_orbit.a * (1-target_orbit.ecc) - 300. * u.km
    a = (apogee+perigee) / 2
    ecc = (apogee-perigee) / (apogee+perigee)
    inc = target_orbit.inc
    raan = target_orbit.raan
    argp = target_orbit.raan
    nu = 0. * u.deg
    lower03_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, starting_epoch)

    # fourth lower perigee
    apogee = target_orbit.a * (1 + target_orbit.ecc)
    perigee = target_orbit.a * (1 - target_orbit.ecc) - 400. * u.km
    a = (apogee + perigee) / 2
    ecc = (apogee - perigee) / (apogee + perigee)
    inc = target_orbit.inc
    raan = target_orbit.raan
    argp = target_orbit.raan
    nu = 0. * u.deg
    lower04_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, starting_epoch)

    # fifth lower perigee
    apogee = target_orbit.a * (1 + target_orbit.ecc)
    perigee = target_orbit.a * (1 - target_orbit.ecc) - 500. * u.km
    a = (apogee + perigee) / 2
    ecc = (apogee - perigee) / (apogee + perigee)
    inc = target_orbit.inc
    raan = target_orbit.raan
    argp = target_orbit.raan
    nu = 0. * u.deg
    lower05_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, starting_epoch)

    # Chaser
    adr_fleet = Fleet('Servicers', 'ADR')
    servicer = Servicer('Chaser', "Chaser")
    guess = 100. * u.kg
    reference_rendezvous_propulsion = PropulsionModule('propulsion_prop', servicer, 'mono-propellant', 22 * u.N,
                                                       0.01 * u.N, 240 * u.s, guess, 100. * u.kg,
                                                       propellant_contingency=0.1)
    reference_rendezvous_propulsion.define_as_rcs_propulsion()
    reference_rendezvous_propulsion.define_as_main_propulsion()
    reference_capture = CaptureModule('capture', servicer)
    reference_capture.define_as_capture_default()
    adr_fleet.add_servicer(servicer)

    # Target
    clients = ADRClients('VESPUP')
    target = Target('target', 112. * u.kg, target_orbit, target_orbit, target_orbit)
    clients.add_target(target)

    # Plan
    adr_plan = Plan('plan', starting_epoch)
    # Servicer insertion
    insertion = Insertion('Insertion_' + servicer.ID, adr_plan, servicer_insertion_orbit, duration=30. * u.day)
    insertion.assign_module(servicer.get_main_propulsion_module())
    # define starting orbit
    phasing = OrbitMaintenance('Phasing', adr_plan, servicer_insertion_orbit, phasing_duration, delta_v_contingency=0.1)
    phasing.assign_module(servicer.get_main_propulsion_module())
    raise01 = OrbitChange('First raise', adr_plan, raise01_orbit, raan_specified=False,
                          initial_orbit=servicer_insertion_orbit,
                          delta_v_contingency=0.1)
    raise01.assign_module(servicer.get_main_propulsion_module())
    raise02 = OrbitChange('Second raise', adr_plan, raise02_orbit, raan_specified=False,
                          initial_orbit=raise01_orbit,
                          delta_v_contingency=0.1)
    raise02.assign_module(servicer.get_main_propulsion_module())
    raise03 = OrbitChange('Third raise', adr_plan, raise03_orbit, raan_specified=False,
                          initial_orbit=raise02_orbit,
                          delta_v_contingency=0.1)
    raise03.assign_module(servicer.get_main_propulsion_module())
    last_phasing_maneuver = OrbitChange('Last phasing', adr_plan, target_orbit, raan_specified=True,
                                        initial_orbit=inc04_orbit,
                                        delta_v_contingency=0.1,
                                        raan_cutoff=0. * u.deg)
    last_phasing_maneuver.assign_module(servicer.get_main_propulsion_module())

    approach = Approach('Approach', adr_plan, target, (3.69 + 0.93) * u.kg, propellant_contingency=0.,
                        duration=(3 * 30. + 48.) * u.day)
    approach.assign_module(servicer.get_rcs_propulsion_module())
    capture = Capture('Capture', adr_plan, target, duration=10. * u.day)
    capture.assign_module(servicer.get_capture_module())
    lower01 = OrbitChange('First lowering', adr_plan, lower01_orbit, raan_specified=False,
                          initial_orbit=target_orbit,
                          delta_v_contingency=0.1)
    lower01.assign_module(servicer.get_main_propulsion_module())
    lower02 = OrbitChange('Second lowering', adr_plan, lower02_orbit, raan_specified=False,
                          initial_orbit=lower01_orbit,
                          delta_v_contingency=0.1)
    lower02.assign_module(servicer.get_main_propulsion_module())
    lower03 = OrbitChange('Third lowering', adr_plan, lower03_orbit, raan_specified=False,
                          initial_orbit=lower02_orbit,
                          delta_v_contingency=0.1)
    lower03.assign_module(servicer.get_main_propulsion_module())
    lower04 = OrbitChange('Fourth lowering', adr_plan, lower04_orbit, raan_specified=False,
                          initial_orbit=lower03_orbit,
                          delta_v_contingency=0.1)
    lower04.assign_module(servicer.get_main_propulsion_module())
    lower05 = OrbitChange('Fifth lowering', adr_plan, lower05_orbit, raan_specified=False,
                          initial_orbit=lower04_orbit,
                          delta_v_contingency=0.1)
    lower05.assign_module(servicer.get_main_propulsion_module())
    reentry = OrbitChange('Reentry', adr_plan, reentry_orbit, raan_specified=False,
                          initial_orbit=lower02_orbit,
                          delta_v_contingency=0.1)
    reentry.assign_module(servicer.get_main_propulsion_module())

    release = Release('Release', adr_plan, target)
    release.assign_module(servicer.get_capture_module())

    adr_fleet.converge(adr_plan, clients, convergence_margin=0.01 * u.kg, verbose=False, design_loop=True)
    adr_fleet.reset(adr_plan)

    return (adr_plan.phases[1].get_duration(), adr_fleet.servicers['chaser'].get_dry_mass(),
            adr_fleet.servicers['chaser'].get_wet_mass(), adr_fleet, adr_plan)


def analysis_option(variable, altitude=500. * u.km, inclination=98.75 * u.deg, mlt=10.5):
    mlt = (mlt - 12.) / 6. * 90. * u.deg
    if variable == 'inclination':
        if altitude < 700. * u.km:
            inc_range = np.linspace(-0.25, 3.25, 20) * u.deg + inclination
        else:
            inc_range = np.linspace(-3.25, 0.25, 20) * u.deg + inclination
        option_duration = []
        option_mass = []
        for inc in inc_range:
            phasing_time, dry_mass, wet_mass, _, _ = analysis_scenario(inc, altitude, mlt)
            option_duration.append(phasing_time.to(u.day).value)
            option_mass.append(wet_mass.to(u.kg).value)

    elif variable == 'altitude':
        if altitude < 700. * u.km:
            inc_range = np.linspace(-200., 100., 20) * u.km + altitude
        else:
            inc_range = np.linspace(-100., 500., 20) * u.km + altitude
        option_duration = []
        option_mass = []
        for alt in inc_range:
            phasing_time, dry_mass, wet_mass, _, _ = analysis_scenario(inclination, alt, mlt)
            option_duration.append(phasing_time.to(u.day).value)
            option_mass.append(wet_mass.to(u.kg).value)
    else:
        print('ERROR')
        return 0
    return inc_range, option_duration, option_mass


default_altitude = 500. * u.km
default_inclination = 98.6 * u.deg
default_mlt = 13.50
default_mlt = (default_mlt - 12.) / 6. * 90. * u.deg

duration, dry, wet, fleet, plan = analysis_scenario(default_inclination, default_altitude, default_mlt)

print('Phasing duration: {0:.0f}'.format(duration))
print('Propellant mass: {0:.1f}'.format(wet-dry))
print('Dry mass: {0:.1f}'.format(dry))
print('Wet mass: {0:.1f}'.format(wet))

plan.print_report()
fleet.print_report()
