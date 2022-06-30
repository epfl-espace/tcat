# Created:          17.05.2022
# Last Revision:    30.06.2022
# Authors:          Emilien Mingard, Malo Goury du Roslan
# Emails:           emilien.mingard@tcdc.ch, malo.goury@tcdc.ch
# Description:      Python script to run TCAT scenario

# Import class
from Scenarios.ScenarioConstellation import ScenarioConstellation
from Scenarios.ScenarioADR import ScenarioADR

# Import libraries
import warnings
import sys
from json import load as load_json
import os
warnings.filterwarnings("ignore")

# User defines
PRINT_IN_FILES = True #DEBUG: Toggling bool for console printing: True = Print in file | False = print in console

# Access system output and error
original_stdout = sys.stdout  # Save a reference to the original standard output
original_stderr = sys.stderr  # Save a reference to the original standard error

# Output files
result = None
log = None

"""
Methods definition
"""

def main():
    """ Script main static function
    """
    json = open_input_json()
    if(json is None): exit() 

    results_dir_path = json["data_path"]
    create_results_dir(results_dir_path)

    set_sys_std_dir(PRINT_IN_FILES,results_dir_path)

    create_and_run_scenario(json,"test_from_file")    

    reset_sys_std_dir()

def open_input_json():
    """ Open the input json file given as sys.argv[1]

    :return: json input structure
    :rtype: dict
    """
    # Set configuration file as input or manually inserted
    try:
        config_file = sys.argv[1]
    except IndexError:
        print("Please specify an input .json file in the argv: PATH/FILENAME.json")
        return None
        #config_file = SCENARIO_INPUT_JSON

    # Open .json and read mission description
    with open(config_file) as file:
        # Open file
        json = load_json(file)
    return json

def create_results_dir(results_folder_path):
    """ Create results directories if not existing

    :param results_folder_path: relative results folder path
    :type results_folder_path: str
    """
    # Create results folder if non-existent
    if not os.path.exists(results_folder_path):
        os.makedirs(results_folder_path, exist_ok=True)

def create_and_run_scenario(input_json, scenario_id="test_scenario"):
    """ Creates and execute

    :param input_json: json input structure
    :type input_json: dict
    :param scenario_id: scenario id name, defaults to "test_scenario"
    :type scenario_id: str, optional
    :return: execution flag
    :rtype: bool or Warning
    """
    scenario = create_scenario(input_json, scenario_id)
    sim_message = run_scenario(scenario)
    return sim_message

def run_scenario(scenario):
    """ Setup and execute a scenario

    :param scenario: main scenario
    :type scenario: :class:`~Scenarios.Scenario.Scenario`
    :return: execution flag
    :rtype: bool or Warning
    """
    if(scenario is None): return "error - invalid scenario"

    # Set-up scenario
    scenario.setup()
    
    # Execute scenario
    results = scenario.execute()

    # Print scenario reports
    scenario.print_results()

    return results

def create_scenario(input_json,scenario_id="test_scenario"):
    """ Create a scenario based on input json file

    :param input_json: json input structure
    :type input_json: dict
    :param scenario_id: scenario id name, defaults to "test_scenario"
    :type scenario_id: str, optional
    :return: main scenario
    :rtype: :class:`~Scenarios.Scenario.Scenario`
    """
    scenario = None
    scenario_type = input_json["scenario"]
    if scenario_type == "constellation_deployment":
        scenario = ScenarioConstellation(scenario_id,input_json)
    elif scenario_type == "adr":
        scenario = ScenarioADR(scenario_id,input_json)
    return scenario

def set_sys_std_dir(print_to_files=True,results_folder_path="./Results"):
    """ If print_to_files is true, redirect the sys console to the output files

    :param print_to_files: print to file flag, defaults to True
    :type print_to_files: bool, optional
    :param results_folder_path: relative results folder path, defaults to "./Results"
    :type results_folder_path: str, optional
    """
    if(print_to_files): 
        # Open files (with statement wont write exceptions to the file, see https://stackoverflow.com/questions/66151573)
        # Files open with line-buffering mode (buffering=1) for flushing more often (every line)
        result = open(os.path.join(results_folder_path, 'result.txt'), 'w', 1, encoding="utf-8")
        log = open(os.path.join(results_folder_path, 'log.txt'), 'w', 1, encoding="utf-8")
        
        # Link output to .txt files
        sys.stdout = result  # Change the standard output to the file result.txt
        sys.stderr = log  # Change the standard error to the file log.txt

def reset_sys_std_dir():
    """ Re-define the system std dir to their original value. Close all files already open
    """
    # Close .txt file
    if(result is not None): result.close()
    if(log is not None): log.close()
    # Reset output to initial value
    sys.stdout = original_stdout  # Reset the standard output to its original value
    sys.stderr = original_stderr  # Reset the standard error to its original value

"""
Main script
"""

if __name__ == "__main__":
    main()

