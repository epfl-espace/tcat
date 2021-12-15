import warnings
from Scenario_ConstellationDeployment import Scenario
import sys
from json import load as load_json
import os
warnings.filterwarnings("ignore")

config_file = sys.argv[1]

# read properties from json config file
with open(config_file) as file:
    json = load_json(file)
    results_folder_path = json["data_path"]

# create the Results folder if it does not exist
if not os.path.exists(results_folder_path):
    os.makedirs(results_folder_path, exist_ok=True)

# this bool enables/disables the generation of txt files and restore the console printing. For debugging purposes
print_to_files = True
if print_to_files:
    original_stdout = sys.stdout  # Save a reference to the original standard output
    original_stderr = sys.stderr  # Save a reference to the original standard error

    # open files (with statement wont write exceptions to the file, see https://stackoverflow.com/questions/66151573)
    # also, we open files with line-buffering mode (buffering=1) for flushing more often (every line)
    result = open(os.path.join(results_folder_path, 'result.txt'), 'w', 1, encoding="utf-8")
    log = open(os.path.join(results_folder_path, 'log.txt'), 'w', 1, encoding="utf-8")

    sys.stdout = result  # Change the standard output to the file result.txt
    sys.stderr = log  # Change the standard error to the file log.txt

    scenario = Scenario("test_from_file", config_file)
    scenario.setup()
    results = scenario.execute()

    scenario.plan.print_report()
    scenario.fleet.print_report()

    sys.stdout = original_stdout  # Reset the standard output to its original value
    sys.stderr = original_stderr  # Reset the standard error to its original value

    result.close()
    log.close()
else:
    scenario = Scenario("test_from_file", config_file)
    scenario.setup()
    results = scenario.execute()

    scenario.plan.print_report()
    scenario.fleet.print_report()

