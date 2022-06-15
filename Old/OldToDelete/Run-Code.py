import datetime

from Scenario_Starlink import *
from Commons.plotting import *




# DEPRECATED

# load snapshot data
reference_clients = load_latest_file('Snapshots', 'Starlink_snapshot')

# Define the main parameters of the trade space:
number_of_tgt_per_serv = [5]
number_of_serv = [3, 6, 12]
architecture = 'shuttle'  # shuttle, current_kits or picker
prop_type = 'electrical'  # electrical or chemical
# number_of_tgt_per_serv = [6]
# number_of_serv = [1]
# architecture = 'shuttle'  # shuttle, current_kits or picker
# prop_type = 'electrical'  # electrical or chemical

# Start progress bar
print_progress_bar(0, len(number_of_tgt_per_serv) * len(number_of_serv),
                   prefix='Progress:', suffix='Complete', length=50)

# Iterate through tradespace and store results in scenarios['number_of_target_per_serv']['number_of_serv']
N_tgt_per_serv, N_serv = np.meshgrid(number_of_tgt_per_serv, number_of_serv)
scenarios = dict()
unconverged = []
for i in range(0, len(number_of_tgt_per_serv)):
    scenarios[str(number_of_tgt_per_serv[i])] = {}
    for j in range(0, len(number_of_serv)):
        if number_of_serv[j] * number_of_tgt_per_serv[i] < 1.25 * len(reference_clients.get_failed_satellites()):
            temp_scenario = Scenario('scenario_'+str(number_of_serv[j])+'_servicers__'+str(number_of_tgt_per_serv[i])
                                     + '_tgt_per_serv', architecture=architecture, prop_type=prop_type)
            temp_scenario.setup(targets_per_servicer=N_tgt_per_serv[j, i], number_of_servicers=N_serv[j, i],
                                clients=reference_clients)
            result = temp_scenario.execute(verbose=False)
            if result and not isinstance(result, RuntimeWarning):
                scenarios[str(number_of_tgt_per_serv[i])][str(number_of_serv[j])] = temp_scenario
            else:
                unconverged.append((temp_scenario, result))
        print_progress_bar(i * len(number_of_serv) + j + 1, len(number_of_tgt_per_serv) * len(number_of_serv),
                           prefix='Progress '+str(number_of_tgt_per_serv[i])+'/'+str(number_of_serv[j])+':',
                           suffix='Complete', length=50)

# Save results in binary files
print("\nResults of convergence_margin :")
for temp_scenario, result in unconverged:
    print("\t"+str(temp_scenario.ID) + " failed to converge : " + str(result))
now_time = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
file_name = temp_scenario.clients.ID + "_" + architecture + "_" + prop_type + "_" + now_time
folder_name = 'Results'
dbfile = open(folder_name + '/' + file_name, 'wb')
pickle.dump(scenarios, dbfile)
dbfile.close()
print('\nSaved :\n\t' + file_name + ' in ' + folder_name)
