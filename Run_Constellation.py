"""
Created:        17.05.2022
Last Revision:  18.05.2022
Author:         Emilien Mingard
Description:    Run python script to test and debug Constellation Deployement TCAT
"""

# Import class
from Scenario.ScenarioConstellation import ScenarioConstellation
from Scenario.ScenarioParameters import SCENARIO_INPUT_JSON

# Import libraries
import warnings
import sys
from json import load as load_json
import os
warnings.filterwarnings("ignore")

# Set configuration file as input or manually inserted
try:
    config_file = sys.argv[1]
except IndexError:
    config_file = SCENARIO_INPUT_JSON

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
    scenario = ScenarioConstellation("test_from_file", config_file)
    
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
    scenario = ScenarioConstellation("test_from_file", config_file)
    
    # Set-up scenario
    scenario.setup()
    
    # Execute scenario
    results = scenario.execute()

    # Print scenario reports
    scenario.plan.print_report()
    scenario.fleet.print_report()

