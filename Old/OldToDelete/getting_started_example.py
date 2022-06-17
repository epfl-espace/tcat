# import plan and phases
from Plan_module import *
from Phases.Approach import *
from Phases.Capture import *
from Phases.Insertion import *
from Phases.OrbitChange import *
from Phases.Release import *

# import servicer and modules
from Fleet_module import *
from Modules.PropulsionModule import *
from Modules.CaptureModule import *
from Modules.StructureModule import *
from Modules.ThermalModule import *
from Modules.AOCSModule import *
from Modules.EPSModule import *
from Modules.CommunicationModule import *
from Modules.DataHandlingModule import *
from Modules.ApproachSuiteModule import *

# import client related methods
from ADRClient_module import *

# Define starting epoch
starting_epoch = Time("2025-06-02 12:00:00", scale="tdb")

# Define orbits
# ----------------------------------------------------------------------------------------------------------------------
# Servicer insertion orbit
a = 500. * u.km + Earth.R
ecc = 0. * u.rad / u.rad
inc = 98.6 * u.deg
raan = 30.5 * u.deg
argp = 0. * u.deg
nu = 0. * u.deg
insertion_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, starting_epoch)

# target operational orbit
a = 7100. * u.km
ecc = 0.001 * u.rad / u.rad
inc = 98.76 * u.deg
raan = 45. * u.deg
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

# Define fleet (here a single ADR servicer)
# ----------------------------------------------------------------------------------------------------------------------
fleet = Fleet('ADR', 'single_picker')

# Define servicers of the fleet (here an ADR servicer using mono-propellant)
# ----------------------------------------------------------------------------------------------------------------------
servicer001 = Servicer('servicer001', 'ADR_servicers')

# modules
reference_structure = StructureModule(servicer001.ID + '_structure', servicer001)
reference_thermal = ThermalModule(servicer001.ID + '_thermal', servicer001)
reference_aocs = AOCSModule(servicer001.ID + '_aocs', servicer001)
reference_eps = EPSModule(servicer001.ID + '_eps', servicer001)
reference_com = CommunicationModule(servicer001.ID + '_communication', servicer001)
reference_data_handling = DataHandlingModule(servicer001.ID + '_data_handling', servicer001)
reference_approach_suite = ApproachSuiteModule(servicer001.ID + '_approach_suite', servicer001)

# propulsion module (define with initial propellant mass and assign as default)
initial_propellant_guess = 100. * u.kg
reference_rendezvous_propulsion = PropulsionModule(servicer001.ID + '_propulsion', servicer001, 'mono-propellant',
                                                   22 * u.N, 0.01 * u.N, 240 * u.s, initial_propellant_guess,
                                                   100. * u.kg, propellant_contingency=0.1)
reference_rendezvous_propulsion.define_as_rcs_propulsion()
reference_rendezvous_propulsion.define_as_main_propulsion()

# capture module
reference_capture = CaptureModule(servicer001.ID + '_capture', servicer001, dry_mass_override=20. * u.kg)
reference_capture.define_as_capture_default()

# add servicer to the fleet
fleet.add_servicer(servicer001)

# Define clients
# ----------------------------------------------------------------------------------------------------------------------
clients = ADRClients('targets')

# Add target to the client (here a single target for an ADR service)
# (Note that the fleet and plan classes are client independent, but the client needs to be tailored to each study).
target = Target('target', 100. * u.kg, insertion_orbit, target_orbit, reentry_orbit)
clients.add_target(target)

# Define plan
# ----------------------------------------------------------------------------------------------------------------------
plan = Plan('plan', starting_epoch)

# Servicer insertion (includes 30 days of commissioning).
# This is performed by the main propulsion module by default, though no actual propellant is used during this phase.
insertion = Insertion('Insertion', plan, insertion_orbit, duration=30. * u.day)
insertion.assign_module(servicer001.get_main_propulsion_module())

# Servicer raise to target (possibly includes phasing at insertion orbit if raan difference is important).
# This is performed by the main propulsion module by default.
orbit_raise = OrbitChange('Raise', plan, target_orbit, raan_specified=True, initial_orbit=insertion_orbit,
                          delta_v_contingency=0.1)
orbit_raise.assign_module(servicer001.get_main_propulsion_module())

# Approach of the target (budgeting 5 kg of propellant for the manoeuvres)
# This is performed by the rcs propulsion module (in this case, the same module does both main and rcs propulsion).
approach = Approach('Approach', plan, target, 5. * u.kg)
approach.assign_module(servicer001.get_rcs_propulsion_module())

# Capture
# This is performed by the main capture propulsion module by default.
capture = Capture('Capture', plan, target, duration=1. * u.day)
capture.assign_module(servicer001.get_capture_module())

# Deorbit
# This is performed by the main propulsion module by default.
deorbit = OrbitChange('Deorbit', plan, reentry_orbit, raan_specified=False, initial_orbit=target_orbit,
                      delta_v_contingency=0.1)
deorbit.assign_module(servicer001.get_main_propulsion_module())

# Release
# This is performed by the main capture propulsion module by default.
release = Release('Release', plan, target)
release.assign_module(servicer001.get_capture_module())

# Perform simulation to converge the fleet to the plan, then reset the fleet. At this point, the fleet is designed.
# ----------------------------------------------------------------------------------------------------------------------
fleet.converge(plan, clients, convergence_margin=0.5 * u.kg)

plan.print_report()
fleet.print_report()

from Commons.plotting import *

# Define starting epoch (here corresponding to launch date)
starting_epoch = Time("2025-06-02 12:00:00", scale="tdb")

# scenario = load_latest_file('Results', 'OneWeb' + '_' + 'refueled_shuttle_high' + '_chemical')

# servicer = scenario['5']['3'].fleet.servicers['tanker_servicer0000']
# fleet = scenario['5']['3'].fleet
# plan = scenario['5']['3'].plan

# plot_single_timeline(servicer, 'current_prop_mass', plan, starting_epoch)

#plot_multiple_timeline(fleet, 'current_prop_mass', plan, starting_epoch)

# plot_scenario_mass_summary(scenario['5']['3'])

