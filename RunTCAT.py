"""
Created:        17.05.2022
Last Revision:  18.05.2022
Author:         Emilien Mingard
Description:    Python script to run TCAT scenario
"""

# Import class
from Scenarios.ScenarioConstellation import ScenarioConstellation
from Scenarios.ScenarioADR import ScenarioADR

# Import libraries
import warnings
import sys
from json import load as load_json
import os
warnings.filterwarnings("ignore")

# user defines
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
    """ main function of the script to run TCAT Scenario
    """
    json = open_input_json()
    if(json is None): exit() 

    results_dir_path = json["data_path"]
    create_results_dir(results_dir_path)

    set_sys_std_dir(PRINT_IN_FILES,results_dir_path)

    create_and_run_scenario(json,"test_from_file")    

    reset_sys_std_dir()

def open_input_json():
    ''' Opens and return the json file specified in sys.argv[1].

    Returns:
        (dict): content of json file. None if sys.argv[1] is empty
    '''
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
    """ if results dir doesn't exist, create it
    """
    # Create results folder if non-existent
    if not os.path.exists(results_folder_path):
        os.makedirs(results_folder_path, exist_ok=True)

def create_and_run_scenario(input_json, scenario_id="test_scenario"):
    """ creates the scenario object and runs the simulation

    return:
        (str) message outputed by scenario
    """
    scenario = create_scenario(input_json, scenario_id)
    sim_message = run_scenario(scenario)
    return sim_message

def run_scenario(scenario):
    """ runs the different methods from the scenario object

    return:
        (str) message outputed by scenario
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
    """ creates the scenario based on the scenario type specified in input json
    args:
        input_json (dict): json object containing the scenario inputs 
        scenario_id (str): to give a name to the scenario

    return:
        (Scenario): the proper object inheriting from Scenario class.
    """
    scenario = None
    scenario_type = input_json["scenario"]
    if scenario_type == "constellation_deployment":
        scenario = ScenarioConstellation(scenario_id,input_json)
    elif scenario_type == "adr":
        scenario = ScenarioADR(scenario_id,input_json)
    return scenario

def set_sys_std_dir(print_to_files=True,results_folder_path="./Results"):
    """ if print_to_files is true, redirect the sys console to the output files
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
    """ re-define the system std dir to their original value. 
        close files eventualy openend.
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

