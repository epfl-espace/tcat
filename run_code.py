import datetime
# import scenarios as scenarios
#from Commons.plotting import plot_mass_summary
from Scenario_moonOperation import *
# import Scenario_characterization as scenario
from Commons.plotting import *
from Commons.Excel_output import *
from astropy import units as u
from datetime import datetime

startTime = datetime.now()

# EPOCH
starting_epoch = Time("2025-01-01 12:00:00", scale="tdb")

# Define the main parameters of the trade space:

architectures = ['direct_LLO', 'direct_nrho', 'nrho_reuse_transfer_module']
load_mass = [0, 100, 200, 500, 800, 1000, 2000, 5000]

for load_mass in load_mass:
    arch_no = 0
    for architecture in architectures:
        arch_no += 1
        temp_scenario = Scenario('Moon Operations', architecture=architecture, load_mass=load_mass * u.kg)
        temp_scenario.setup()
        # print(temp_scenario.fleet)
        result = temp_scenario.execute(verbose=False)
        print(temp_scenario.plan)
        print(temp_scenario.fleet)
        print_excel(temp_scenario, arch_no, load_mass)
        # plot_timeline_from_plan_and_fleet(temp_scenario.starting_epoch, temp_scenario.plan, temp_scenario.fleet,
        #                                   ['get_current_mass'])

print(f'DONE.\n' 
      f'Time elapsed to run the code: {int((datetime.now() - startTime).total_seconds())} seconds')


# print(temp_scenario.fleet.get_total_wet_mass())
# print(temp_scenario.plan)
# print(temp_scenario.fleet.servicers['landing_module'].print_report())
# print(temp_scenario.fleet.servicers['service_module'].print_report())
# print(temp_scenario.fleet.servicers['small_cargo_module'].print_report())

# plot_timeline_from_plan_and_fleet(temp_scenario.starting_epoch, temp_scenario.plan, temp_scenario.fleet, ['get_current_mass'], annotate=True)

# module_names, temp_output, temp_servicer_id = temp_scenario.fleet.get_mass_summary(rm_duplicates=False)

# plot_timeline_from_plan_and_fleet(temp_scenario.starting_epoch, temp_scenario.plan, temp_scenario.fleet, ['get_current_mass'])
