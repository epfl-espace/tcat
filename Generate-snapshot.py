import datetime
import pickle

from Scenario_ADR import *

# DEPRECATED

# Define reference scenario.
# The constellation state created in this scenario will serve as reference for the rest of the analysis.
reference_scenario = Scenario('reference_scenario')
reference_clients = reference_scenario.define_clients()
reference_clients.plot_distribution()

# Save data
now_time = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
file_name = reference_scenario.clients.ID + '_snapshot_' + now_time
folder_name = 'Snapshots'
dbfile = open(folder_name + '/' + file_name, 'wb')
pickle.dump(reference_clients, dbfile)
dbfile.close()
print('Saved : ' + file_name + ' in ' + folder_name)
