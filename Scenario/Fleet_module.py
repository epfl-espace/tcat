"""
Created:        ?
Last Revision:  23.05.2022
Author:         ?,Emilien Mingard
Description:    Fleet,Spacecraft,Servicer and UpperStage Classes definition
"""

# Import Classes
from Modules.CaptureModule import CaptureModule
from Modules.PropulsionModule import PropulsionModule
from Phases.Approach import Approach
from Phases.Insertion import Insertion
from Phases.OrbitChange import OrbitChange
from Phases.Release import Release
from Scenario.Interpolation import get_launcher_performance, get_launcher_fairing
from Scenario.ScenarioParameters import *
from Scenario.Plan_module import *
from Spacecrafts.UpperStage import UpperStage

# Import libraries
import logging
import warnings
import numpy as np
from astropy import units as u
from poliastro.bodies import Earth
from poliastro.twobody import Orbit
import copy
import math

class Fleet:
    """ A Fleet consists of a dictionary of servicers.
        The class is initialized with an emtpy dictionary of servicers.
        It contains methods used during simulation and convergence of the servicers design.
    """

    """
    Init
    """
    def __init__(self, fleet_id, scenario):
        # Fleet id
        self.id = fleet_id

        # Fleet architecture
        self.scenario = scenario

        # Dictionnaries of spacecrafts
        self.servicers = dict()
        self.upperstages = dict()

        # Flags
        self.is_performance_graph_already_generated = False
    
    """
    Methods
    """
    def execute(self,clients,verbose=False):
        """ This function calls all appropriate methods to design the fleet to perform a particular plan.

        Args:
            clients (Constellation): full or tailored constellation containing satellite treated as targets to reach by any spacecraft
            verbose (boolean): if True, print convergence information
        """
        # Instanciate iteration limits
        execution_limit = 100
        execution_count = 1

        # Retrieve unassigned satellites
        unassigned_satellites = clients.get_optimized_ordered_satellites()

        # Spacecraft launcher counter
        spacecraft_count = 0

        # Start execution loop
        while len(unassigned_satellites)>0 and execution_count <= execution_limit:
            # Instanciate upperstage execution limit
            upperstage_execution_limit = 20
            upperstage_execution_count = 0
            upperstage_converged = False

            # Create UpperStage
            spacecraft_count += 1
            upperstage = UpperStage(f"UpperStage_{spacecraft_count:04d}",self.scenario,mass_contingency=0.0)
            upperstage_low_sat_allowance = 0
            upperstage_up_sat_allowance = upperstage.compute_allowance(unassigned_satellites)

            # Iterate until upperstage allowance is converged
            while upperstage_execution_count <= upperstage_execution_limit and not(upperstage_converged):
                # Check if converged
                if upperstage_low_sat_allowance == upperstage_up_sat_allowance:
                    # exit loop flat
                    upperstage_converged = True

                # Compute new current allowance
                upperstage_cur_sat_allowance = math.ceil((upperstage_low_sat_allowance+upperstage_up_sat_allowance)/2)

                # Execute upperstage
                upperstage.execute(clients,upperstage_cur_sat_allowance)
                upperstage_main_propulsion_module = upperstage.get_main_propulsion_module()

                # Check for exit condition
                if upperstage_up_sat_allowance - upperstage_low_sat_allowance <= 1:
                    # If fuel mass > 0 and cur == up, then up is the solution
                    if upperstage_main_propulsion_module.get_current_prop_mass() > 0 and upperstage_cur_sat_allowance == upperstage_up_sat_allowance:
                        upperstage_low_sat_allowance = upperstage_up_sat_allowance
                    # If fuel mass < 0 then low is the solution for sure, hoping it is not zero.
                    else:
                        upperstage_up_sat_allowance = upperstage_low_sat_allowance

                # Apply dichotomia to remaining values
                else:
                    if upperstage_main_propulsion_module.get_current_prop_mass() > 0:
                        # If extra fuel, increase lower bound
                        upperstage_low_sat_allowance = upperstage_cur_sat_allowance

                    else:
                        # If lacking fuel, decrease upper bound
                        upperstage_up_sat_allowance = upperstage_cur_sat_allowance

            # Iterate until upperstage total deployment time is computed (If phasing existing)
            upperstage.execute_with_fuel_usage_optimisation(clients)
                         
            # Add converged UpperStage and remove newly assigned satellite
            self.add_upperstage(upperstage)
            
            # Remove latest assigned satellites
            clients.remove_in_ordered_satellites(upperstage.assigned_targets)
            
            # Check remaining satellites to be assigned
            unassigned_satellites = clients.get_optimized_ordered_satellites()

            # Update execution counter
            execution_count += 1

    def get_graph_status(self):
        if self.is_performance_graph_already_generated:
            return True
        else:
            return False

    def set_graph_status(self, status):
        self.is_performance_graph_already_generated = status

    def add_servicer(self, servicer):
        """ Adds a servicer to the Fleet class.

        Args:
            servicer (Servicer): servicer to add to the fleet
        """
        if servicer in self.servicers:
            warnings.warn('Servicer ', servicer.ID, ' already in fleet ', self.id, '.', UserWarning)
        else:
            self.servicers[servicer.ID] = servicer

    def add_upperstage(self, upperstage):
        """ Adds a launcher to the Fleet class.

        Args:
            launcher (UpperStage): launcher to add to the fleet
        """
        if upperstage in self.upperstages:
            warnings.warn('Launcher ', upperstage.id, ' already in fleet ', self.id, '.', UserWarning)
        else:
            self.upperstages[upperstage.id] = upperstage

    def get_number_upperstages(self):
        """ Compute and return size of self.upperstages dict

        Return:
            (int): length of self.upperstages
        """
        return len(self.upperstages)

    def get_number_servicers(self):
        """ Compute and return size of self.servicers dict

        Return:
            (int): length of self.upperstages
        """
        return len(self.servicers)

    def reset(self, plan, design_loop=True, verbose=False, convergence_margin=0.5 * u.kg):
        """ Calls the reset function for each servicer in the fleet. If design_loop is True, this include a redesign
            of the servicer.

        Args:
            plan (Plan): plan that might be used as reference to reset the fleet
            design_loop (bool): True if sub-systems dry masses are changed during iterations.
                                False if only the propellant mass is changed.
            verbose (bool): if True, print information on design convergence
            convergence_margin (u.kg): accuracy required on propellant mass for convergence during servicer redesign
        """
        for _, servicer in self.servicers.items():
            servicer.reset(plan, design_loop=design_loop, convergence_margin=convergence_margin, verbose=verbose)
        for _, upperstage in self.upperstages.items():
            upperstage.reset(plan, design_loop=design_loop, convergence_margin=convergence_margin, verbose=verbose)

    def get_development_cost(self, plan):
        """ Compute development cost, taking into account rough order of magnitude estimates.

        Arg:
            plan (Plan): keep this as argument, this is done to homogenize the "get_" methods

        Return:
            (float): cost in Euros
        """
        # Software development costs
        software_lines = 40000  # Mega-Co Reference
        software_development_cost = software_lines * 550  # Mega-Co Reference
        # Servicers development cost (for each servicer_group)
        servicers_development_cost = 0.
        for servicer_group in self.get_servicer_groups():
            max_servicer_cost = 0
            for _, servicer in self.get_servicers_from_group(servicer_group).items():
                if servicer.get_development_cost() > max_servicer_cost:
                    max_servicer_cost = servicer.get_development_cost()
            servicers_development_cost = servicers_development_cost + max_servicer_cost
        development_cost = software_development_cost + servicers_development_cost
        return development_cost.decompose()

    def get_moc_development_cost(self, plan):
        """ Compute cost of mission operational center development cost.

        Arg:
            plan (Plan): keep this as argument, this is done to homogenize the "get_" methods

        Return:
            (float): cost in Euros
        """
        return 4.7 * 1000000

    def get_ground_segment_cost(self, plan):
        """ Compute cost of ground segment based on flight segment cost.

        Arg:
            plan (Plan): Dictionary of phases that need to be performed by the fleet.

        Return:
            (float): cost in Euros
        """
        return self.get_servicers_hardware_recurring_cost(plan) / len(self.servicers) * 0.08

    def get_servicers_hardware_recurring_cost(self, plan):
        """ Compute recurring cost of flight segment hardware (without AIT).

        Arg:
            plan (Plan): keep this as argument, this is done to homogenize the "get_" methods

        Return:
            (float): cost in Euros
        """
        temp = 0.
        for _, servicer in self.servicers.items():
            temp += servicer.get_hardware_recurring_cost()
        return temp

    def get_servicers_ait_recurring_cost(self, plan):
        """ Compute recurring cost of AIT.

        Arg:
            plan (Plan): Dictionary of phases that need to be performed by the fleet.

        Return:
            (float): cost in Euros
        """
        return self.get_servicers_hardware_recurring_cost(plan) * 0.139

    def get_launch_cost(self, plan):
        """ Compute launch cost for all servicers of the fleet based on cost prorate of the mass.

        Arg:
            plan (Plan): keep this as argument, this is done to homogenize the "get_" methods

        Return:
            (float): cost in Euros
        """
        servicers_mass, _ = self.get_servicers_launch_mass()
        adapter_mass = sum(servicers_mass) * 0.15
        launched_mass = sum(servicers_mass) + adapter_mass
        price_per_kg = 5000 / u.kg
        return (price_per_kg * launched_mass).decompose()

    def get_total_cost(self, plan, with_development=True):
        """ Compute total cost for the program.

        Arg:
            plan (Plan): Dictionary of phases that need to be performed by the fleet.
            with_development (boolean): if True, include cost of servicers development

        Return:
            (float): cost in Euros
        """
        if with_development:
            return (self.get_development_cost(plan)
                    + self.get_servicers_ait_recurring_cost(plan)
                    + self.get_launch_cost(plan)
                    + self.get_servicers_hardware_recurring_cost(plan)
                    + self.get_ground_segment_cost(plan)
                    + self.get_moc_development_cost(plan))
        else:
            return (self.get_servicers_ait_recurring_cost(plan)
                    + self.get_launch_cost(plan)
                    + self.get_servicers_hardware_recurring_cost(plan)
                    + self.get_ground_segment_cost(plan))

    def get_servicers_launch_mass(self):
        """ Compute and return a list of the servicer IDs and a list of their launch masses, including contingencies.

        Return:
            ([u.kg]): list of masses
            ([str]): list of servicer IDs corresponding to listed masses
        """
        launch_mass_list = []
        servicers_id_list = []
        for _, servicer in self.servicers.items():
            servicers_id_list.append(servicer.ID)
            launch_mass_list.append(servicer.get_wet_mass(contingency=True))
        return launch_mass_list, servicers_id_list

    def get_servicer_groups(self):
        """ Return list of servicer_group names present in the fleet.

        Return:
            ([str]): list of string identifier for each servicer_group found in the fleet
        """
        groups = []
        for _, servicer in self.servicers.items():
            if servicer.group not in groups:
                groups.append(servicer.group)
        return groups

    def get_launchers_from_group(self, upperstage_group):
        """ Return servicers from the fleet that share a servicer_group.

        Arg:
            servicer_group (str): string identifier for every group in the fleet (group types: servicer, tanker, etc.)

        Return:
            (dict(Servicer)): Dictionary of servicers of the given group
        """
        return {upperstage_id: upperstage for upperstage_id, upperstage in self.upperstages.items() if upperstage.group == upperstage_group}

    def get_servicers_from_group(self, servicer_group):
        """ Return servicers from the fleet that share a servicer_group.

        Arg:
            servicer_group (str): string identifier for every group in the fleet (group types: servicer, tanker, etc.)

        Return:
            (dict(Servicer)): Dictionary of servicers of the given group
        """
        return {servicer_id: servicer for servicer_id, servicer in self.servicers.items() if servicer.group == servicer_group}

    def get_mass_summary(self, rm_duplicates=False):
        """ Returns information in a convenient way for plotting purposes. 
            What is returned depends on the module_names list (currently hard coded).

        TODO: Check if applicable to generic.

        Args:
            rm_duplicates (boolean): if True, the output will be returned only once for each servicer design

        Return:
            ([str]): list of modules or module names
            ([[float]]): list that contains, for each element of module name, and for each servicer, its mass
            ([str]): list of small string that, for each servicer, summarises the servicer dry and wet masses
        """
        # Define what will be returned by the function
        module_names = ['AOCS', 'ApproachSuite', 'Capture', 'Communication', 'DataHandling', 'EPS', 'Structure',
                        'Thermal', 'Phasing_Propulsion', 'Rendezvous_Propulsion', 'Contingency', 'Phasing_Propellant',
                        'Rendezvous_Propellant']
        # Initialize output as empty list
        output = []
        servicer_str = []
        # Iterate over the quantities to output
        for i, module_name in enumerate(module_names):
            # Initialize list to store the value for this quantity
            temp_result = []
            # if rm_duplicates is True, then we only look at the first servicer, otherwise all of them
            if rm_duplicates:
                selected_servicers = {'servicer0000': self.servicers['servicer0000']}
            else:
                selected_servicers = self.servicers
            additional_servicers = dict()
            for _, servicer in selected_servicers.items():
                if servicer.assigned_tanker:
                    additional_servicers[servicer.assigned_tanker.ID] = servicer.assigned_tanker
            selected_servicers.update(additional_servicers)
            # iterate through servicers selected (one of all)
            for _, servicer in selected_servicers.items():
                # output a string summarizing the servicer mass properties
                if len(servicer.assigned_targets) == 0:
                    temp_str = 'assigned_tanker'
                else:
                    temp_str = 'servicer'
                # temp_str = 'servicer' + '\ndry mass: {:.0f}'.format(servicer.get_dry_mass()) \
                #            + '\nwet mass: {:.0f}'.format(servicer.get_wet_mass())
                # for the first servicer, append the servicer id
                if i == 0:
                    servicer_str.append(temp_str)
                # for particular quantities, call the appropriate methods
                if module_name == 'Phasing_Propulsion':
                    if servicer.get_main_propulsion_module():
                        temp_result.append(servicer.get_main_propulsion_module().get_current_dry_mass())
                    else:
                        temp_result.append(0. * u.kg)
                elif module_name == 'Rendezvous_Propulsion':
                    if (servicer.get_rcs_propulsion_module()
                            and servicer.get_rcs_propulsion_module() != servicer.get_main_propulsion_module()):
                        temp_result.append(servicer.get_rcs_propulsion_module().get_current_dry_mass())
                    else:
                        temp_result.append(0. * u.kg)
                elif module_name == 'Phasing_Propellant':
                    if servicer.get_main_propulsion_module():
                        temp_result.append(servicer.get_main_propulsion_module().initial_propellant_mass)
                    else:
                        temp_result.append(0. * u.kg)
                elif module_name == 'Rendezvous_Propellant':
                    if (servicer.get_rcs_propulsion_module()
                            and servicer.get_rcs_propulsion_module() != servicer.get_main_propulsion_module()):
                        temp_result.append(servicer.get_rcs_propulsion_module().initial_propellant_mass)
                    else:
                        temp_result.append(0. * u.kg)
                elif module_name == 'Contingency':
                    temp_result.append(servicer.get_current_dry_mass()
                                       / (1 + servicer.mass_contingency) * servicer.mass_contingency)
                else:
                    temp_result.append(servicer.get_module_mass(module_name))
                # repeat as above for current_kits
                if rm_duplicates and servicer.initial_kits:
                    selected_kits = {'servicer0000_kit0000': servicer.initial_kits['servicer0000_kit0000']}
                else:
                    selected_kits = servicer.initial_kits
                for _, kit in selected_kits.items():
                    temp_str = 'kit'
                    if i == 0:
                        servicer_str.append(temp_str)
                    if module_name == 'Phasing_Propulsion':
                        if kit.get_main_propulsion_module():
                            temp_result.append(kit.get_main_propulsion_module().get_current_dry_mass())
                        else:
                            temp_result.append(0. * u.kg)
                    elif module_name == 'Rendezvous_Propulsion':
                        if kit.get_rcs_propulsion_module() \
                                and kit.get_rcs_propulsion_module() != kit.get_main_propulsion_module():
                            temp_result.append(kit.get_rcs_propulsion_module().get_current_dry_mass())
                        else:
                            temp_result.append(0. * u.kg)
                    elif module_name == 'Phasing_Propellant':
                        if kit.get_main_propulsion_module():
                            temp_result.append(kit.get_main_propulsion_module().initial_propellant_mass)
                        else:
                            temp_result.append(0. * u.kg)
                    elif module_name == 'Rendezvous_Propellant':
                        if kit.get_rcs_propulsion_module() \
                                and kit.get_rcs_propulsion_module() != kit.get_main_propulsion_module():
                            temp_result.append(kit.get_rcs_propulsion_module().initial_propellant_mass)
                        else:
                            temp_result.append(0. * u.kg)
                    else:
                        temp_result.append(kit.get_module_mass(module_name))
            # append quantities results to output
            output.append(temp_result)
        return module_names, output, servicer_str

    def get_recurring_cost_summary(self, rm_duplicates=False):
        """ Returns information in a convenient way for plotting purposes.
            What is returned depends on the module_names list (currently hard coded).

        TODO: Check if applicable to generic.

        Args:
            rm_duplicates (boolean): if True, the output will be returned only once for each servicer design

        Return:
            ([str]): list of modules or module names
            ([[float]]): list that contains, for each element of module name, and for each servicer, its mass
            ([str]): list of small string that, for each servicer, summarises the servicer dry and wet masses
        """
        # Define what will be returned by the function
        module_names = ['AOCS', 'ApproachSuite', 'Capture', 'Communication', 'DataHandling', 'EPS', 'Structure',
                        'Thermal', 'Phasing_Propulsion', 'Rendezvous_Propulsion']
        # Initialize output as empty list
        output = []
        servicer_str = []
        # Iterate over the quantities to output
        for i, module_name in enumerate(module_names):
            # Initialize list to store the value for this quantity
            temp_result = []
            # if rm_duplicates is True, then we only look at the first servicer, otherwise all of them
            if rm_duplicates:
                selected_servicers = {'servicer0000': self.servicers['servicer0000']}
            else:
                selected_servicers = self.servicers
            additional_servicers = dict()
            for _, servicer in selected_servicers.items():
                if servicer.assigned_tanker:
                    additional_servicers[servicer.assigned_tanker.ID] = servicer.assigned_tanker
            selected_servicers.update(additional_servicers)
            # iterate through servicers selected (one of all)
            for _, servicer in selected_servicers.items():
                # output a string summarizing the servicer mass properties
                if len(servicer.assigned_targets) == 0:
                    temp_str = 'assigned_tanker'
                else:
                    temp_str = 'servicer'
                # temp_str = 'servicer' + '\ndry mass: {:.0f}'.format(servicer.get_dry_mass()) \
                #            + '\nwet mass: {:.0f}'.format(servicer.get_wet_mass())
                # for the first servicer, append the servicer id
                if i == 0:
                    servicer_str.append(temp_str)
                # for particular quantities, call the appropriate methods
                if module_name == 'Phasing_Propulsion':
                    if servicer.get_main_propulsion_module():
                        temp_result.append(servicer.get_main_propulsion_module().get_hardware_recurring_cost()
                                           / 1000 * u.m / u.m)
                    else:
                        temp_result.append(0. * u.kg)
                elif module_name == 'Rendezvous_Propulsion':
                    if (servicer.get_rcs_propulsion_module()
                            and servicer.get_rcs_propulsion_module() != servicer.get_main_propulsion_module()):
                        temp_result.append(servicer.get_rcs_propulsion_module().get_hardware_recurring_cost()
                                           / 1000 * u.m / u.m)
                    else:
                        temp_result.append(0. * u.kg)
                else:
                    temp_result.append(servicer.get_module_recurring_cost(module_name) / 1000 * u.m / u.m)
                # repeat as above for current_kits
                if rm_duplicates and servicer.initial_kits:
                    selected_kits = {'servicer0000_kit0000': servicer.initial_kits['servicer0000_kit0000']}
                else:
                    selected_kits = servicer.initial_kits
                for _, kit in selected_kits.items():
                    temp_str = 'kit'
                    if i == 0:
                        servicer_str.append(temp_str)
                    if module_name == 'Phasing_Propulsion':
                        if kit.get_main_propulsion_module():
                            temp_result.append(kit.get_main_propulsion_module().get_hardware_recurring_cost()
                                               / 1000 * u.m / u.m)
                        else:
                            temp_result.append(0. * u.kg)
                    elif module_name == 'Rendezvous_Propulsion':
                        if kit.get_rcs_propulsion_module() \
                                and kit.get_rcs_propulsion_module() != kit.get_main_propulsion_module():
                            temp_result.append(kit.get_rcs_propulsion_module().get_hardware_recurring_cost()
                                               / 1000 * u.m / u.m)
                        else:
                            temp_result.append(0. * u.kg)
                    else:
                        temp_result.append(kit.get_module_recurring_cost(module_name) / 1000 * u.m / u.m)
            # append quantities results to output
            output.append(temp_result)
        return module_names, output, servicer_str

    def print_assignments(self):
        """ Print a quick summary of which servicer is assigned to which targets. 
        """
        # TODO: deprecate
        temp_string = ''
        for servicer_id, servicer in self.servicers.items():
            temp_string = temp_string + servicer_id+ ' :\n'
            for tgt in servicer.assigned_targets:
                temp_string = temp_string + '\t' + tgt.ID + '\n'
        print(temp_string)

    def print_report(self):
        """ Print a quick summary of fleet information for debugging purposes.
        """
        for _, servicer in self.servicers.items():
            servicer.print_report()
        for _, upperstage in self.upperstages.items():
            upperstage.print_report()

    def print_KPI(self):
        """ Print KPI related to the fleet"""
        # Number of launcher
        Nb_UpperStage = len(self.upperstages)
        if Nb_UpperStage > 1:
            print(f"UpperStages: {Nb_UpperStage}")
        else:
            print(f"UpperStage: {Nb_UpperStage}")

        # Print total launcher mass accros the fleet
        launchers_mass = [self.upperstages[key].get_initial_mass() for key in self.upperstages.keys()]
        print(F"Total mass launched in space: {sum(launchers_mass):.2f}")

    def __str__(self):
        temp = self.id
        for _, servicer in self.servicers.items():
            temp = temp + '\n\t' + servicer.__str__()
        return temp   