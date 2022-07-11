from Scenario_ADR import *
from Commons.plotting import *
from ADRClient_module import *

propulsion="electrical"
architecture='current_kits'
scenario=Scenario("test", architecture,  propulsion)
scenario.setup(number_of_servicers=1, targets_per_servicer=4)

results=scenario.execute()

scenario.plan.print_report()
scenario.fleet.print_report()


plot_single_timeline(scenario.fleet.servicers["servicer0000"], "current_mass", scenario.plan, scenario.starting_epoch, annotate=True)
# plot_single_timeline(scenario.fleet.servicers["servicer0001"], "current_mass", scenario.plan, scenario.starting_epoch, annotate=True)
# # plot_single_timeline(scenario.fleet.servicers["servicer0002"], "current_mass", scenario.plan, scenario.starting_epoch, annotate=True)
# plot_multiple_timeline(scenario.fleet, "current_mass", scenario.plan, scenario.starting_epoch, annotate=True, save=f"{architecture}_{propulsion}__mass")
# plot_multiple_timeline(scenario.fleet, "dry_mass", scenario.plan, scenario.starting_epoch, annotate=True, save=f"{architecture}_{propulsion}__dry_mass")
# plot_multiple_timeline(scenario.fleet, "wet_mass", scenario.plan, scenario.starting_epoch, annotate=True, save=f"{architecture}_{propulsion}__wet_mass")
# plot_multiple_timeline(scenario.fleet, "initial_prop_mass", scenario.plan, scenario.starting_epoch, annotate=True, save=f"{architecture}_{propulsion}__init_prop_mass")
# plot_multiple_timeline(scenario.fleet, "a", scenario.plan, scenario.starting_epoch, annotate=True, save=f"{architecture}_{propulsion}__a")
# plot_multiple_timeline(scenario.fleet, "ecc", scenario.plan, scenario.starting_epoch, annotate=True, save=f"{architecture}_{propulsion}__ecc")
# plot_multiple_timeline(scenario.fleet, "inc", scenario.plan, scenario.starting_epoch, annotate=True, save=f"{architecture}_{propulsion}__inc")
# plot_multiple_timeline(scenario.fleet, "raan", scenario.plan, scenario.starting_epoch, annotate=True, save=f"{architecture}_{propulsion}__raan")
# plot_multiple_timeline(scenario.fleet, "argp", scenario.plan, scenario.starting_epoch, annotate=True, save=f"{architecture}_{propulsion}__argp")
# plot_multiple_timeline(scenario.fleet, "nu", scenario.plan, scenario.starting_epoch, annotate=True, save=f"{architecture}_{propulsion}__nu")

