from Constellation_Client_Module import *
from Scenario_ConstellationDeployment import *

from astropy.time import Time

from matplotlib.pyplot import show
from poliastro.plotting import StaticOrbitPlotter
from poliastro.frames import Planes
from poliastro.constants import J2000
from poliastro.examples import *
from poliastro.plotting import *
import warnings

warnings.filterwarnings("ignore")

scenario = Scenario("test", architecture='launch_vehicle', prop_type='electrical', verbose=False)
scenario.setup()
results = scenario.execute()

scenario.plan.print_report()
scenario.fleet.print_report()

# # target insertion orbit
# starting_epoch = Time("2025-01-01 12:00:00", scale="tdb")
# a = 550 * u.km + Earth.R
# ecc = 0. * u.rad / u.rad
# inc = 53.0 * u.deg
# raan = 0. * u.deg
# argp = 90. * u.deg
# nu = 0. * u.rad
# target_insertion_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, starting_epoch)
#
# tgt_orbit = target_insertion_orbit
# clients = ConstellationClients('Starlink')
# reference_sat = Target('ref_Starlink_sat', 180 * u.kg, tgt_orbit, tgt_orbit, tgt_orbit, state='failed')
#
# clients.populate_standard_constellation('Starlink', reference_sat, number_of_planes=24, sat_per_plane=5)
# clients.plot_distribution()
#
# starting_epoch = Time("2025-06-02 12:00:00", scale="tdb")
#
# fig = OrbitPlotter3D()
# verbose = True
# if verbose:
#     i = 0
#     for _, target in clients.targets.items():
#         i += 1
#         if i < len(clients.targets):
#             fig.plot(target.current_orbit, label=target)
#         else:
#             fig.plot(target.current_orbit, label=target).show()
