# Import class
from Scenario_ConstellationDeployment import Scenario

# Import libraries
import warnings
import sys
from json import load as load_json
import os
warnings.filterwarnings("ignore")

# Set configuration file as input or manually inserted
config_file = "test_config_Example_AsReceived.json" #= sys.argv[1]

# Open .json and read mission description
with open(config_file) as file:
    # Open file
    json = load_json(file)
    
    # Extract output folder path
    results_folder_path = json["data_path"]

# Create results folder if non-existent
if not os.path.exists(results_folder_path):
    os.makedirs(results_folder_path, exist_ok=True)

# DEBUG: Toggling bool for console printing: True = Print in file | False = print in console
print_to_files = True

# Check for debug
if print_to_files:
    # Access system output and error
    original_stdout = sys.stdout  # Save a reference to the original standard output
    original_stderr = sys.stderr  # Save a reference to the original standard error

    # Open files (with statement wont write exceptions to the file, see https://stackoverflow.com/questions/66151573)
    # Files open with line-buffering mode (buffering=1) for flushing more often (every line)
    result = open(os.path.join(results_folder_path, 'result.txt'), 'w', 1, encoding="utf-8")
    log = open(os.path.join(results_folder_path, 'log.txt'), 'w', 1, encoding="utf-8")
    
    # Link output to .txt files
    sys.stdout = result  # Change the standard output to the file result.txt
    sys.stderr = log  # Change the standard error to the file log.txt

    # Instanciate scenario object
    scenario = Scenario("test_from_file", config_file)
    
    # Set-up scenario
    scenario.setup()
    
    # Execute scenario
    results = scenario.execute()
    
    # Print scenario reports
    scenario.plan.print_report()
    scenario.fleet.print_report()
    
    # Close .txt file
    result.close()
    log.close()
    
    # Reset output to initial value
    sys.stdout = original_stdout  # Reset the standard output to its original value
    sys.stderr = original_stderr  # Reset the standard error to its original value
    
    
else:
    # Instanciate scenario object
    scenario = Scenario("test_from_file", config_file)
    
    # Set-up scenario
    scenario.setup()
    
    # Execute scenario
    results = scenario.execute()

    # Print scenario reports
    scenario.plan.print_report()
    scenario.fleet.print_report()
