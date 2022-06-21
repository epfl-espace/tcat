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

                # Check for exit condition
                if upperstage_up_sat_allowance - upperstage_low_sat_allowance <= 1:
                    # If fuel mass > 0 and cur == up, then up is the solution
                    if upperstage.mainpropulsion.current_propellant_mass > 0 and upperstage_cur_sat_allowance == upperstage_up_sat_allowance:
                        upperstage_low_sat_allowance = upperstage_up_sat_allowance
                    # If fuel mass < 0 then low is the solution for sure, hoping it is not zero.
                    else:
                        upperstage_up_sat_allowance = upperstage_low_sat_allowance

                # Apply dichotomia to remaining values
                else:
                    if upperstage.mainpropulsion.current_propellant_mass > 0:
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

class Spacecraft:
    """
    General Attributs
    """

    """
    Init
    """
    def __init__(self,id,group,additional_dry_mass,mass_contingency,starting_epoch):
        # Original attributs (To be described)
        self.id = id
        self.group = group
        self.current_orbit = None
        self.previous_orbit = None
        self.additional_dry_mass = additional_dry_mass
        self.modules = dict()
        self.main_propulsion_module_ID = ''
        self.rcs_propulsion_module_ID = ''
        self.capture_module_ID = ''
        self.initial_kits = dict()
        self.current_kits = dict()
        self.initial_sats = dict()
        self.current_sats = dict()
        self.assigned_tanker = None
        self.assigned_targets = []
        self.mothership = None
        self.mass_contingency = mass_contingency

        # Instanciate Plan
        self.plan = Plan(f"Plan_{self.id}",starting_epoch)

    """
    Methods
    """
    def empty_plan(self):
        """ Reset plan for next iteration
        """
        self.plan.empty()

    def add_module(self, module):
        """ Adds a module to the Servicer class.
            TODO: change description

        Args:
            module (GenericModule): module to be added
        """
        if module in self.modules:
            warnings.warn('Module ', module.id, ' already in servicer ', self.id, '.', UserWarning)
        else:
            self.modules[module.id] = module

    def get_dry_mass(self, contingency=True):
        """Returns the total dry mass of the servicer. Does not include kits.

        Args:
            contingency (boolean): if True, apply contingencies

        Return:
            (u.kg): total dry mass
        """
        temp_mass = self.additional_dry_mass
        for _, module in self.modules.items():
            temp_mass = temp_mass + module.get_dry_mass(contingency=contingency)
        if contingency:
            temp_mass = temp_mass * (1 + self.mass_contingency)
        return temp_mass

    def design(self, plan, convergence_margin=0.5 * u.kg, verbose=False):
        """ Loop on the modules computations until the dry mass is stable.

        Args:
            plan (Plan): plan for which the fleet needs to be designed
            convergence_margin (u.kg): accuracy required on propellant mass for convergence
            verbose (boolean): if True, print convergence_margin information
        """
        unconverged = True
        try:
            while unconverged:
                # design kits
                for _, kit in self.initial_kits.items():
                    kit.design(plan)
                # design modules based on current wet mass and compare with last iteration wet mass
                # TODO: replace this very crude convergence_margin with a better solution
                iteration_mass = self.get_wet_mass()
                for _, module in self.modules.items():
                    module.design(plan)
                delta = abs(self.get_wet_mass() - iteration_mass)
                if verbose:
                    print('Sub-systems design ', self.id, ' - Delta: ', delta, iteration_mass, self.get_dry_mass(),self.get_wet_mass())
                if delta <= convergence_margin:
                    unconverged = False
        except RecursionError:
            warnings.warn('No convergence_margin in sub-systems design.', UserWarning)

    def get_initial_prop_mass(self):
        """ Returns the total mass of propellant inside the servicer at launch. Does not include kits propellant.

        Return:
            (u.kg): initial propellant mass
        """
        temp_mass = 0. * u.kg
        for _, module in self.modules.items():
            if isinstance(module, PropulsionModule):
                temp_mass = temp_mass + module.get_initial_prop_mass()
        return temp_mass

    def get_wet_mass(self, contingency=True):
        """ Returns the wet mass of the servicer at launch. Does not include kits.

        Args:
            contingency (boolean): if True, apply contingencies

        Return:
              (u.kg): total wet mass
        """
        return self.get_dry_mass(contingency=contingency) + self.get_initial_prop_mass()

    def get_hardware_recurring_cost(self):
        """ Returns the recurring cost of the servicer, including all modules and current_kits.

        Return:
            (float): cost in Euros
        """
        recurring_cost = 0.
        # modules cost
        for _, module in self.modules.items():
            recurring_cost = recurring_cost + module.get_recurring_cost()
        # kits modules cost
        for _, kit in self.initial_kits.items():
            recurring_cost = recurring_cost + kit.get_hardware_recurring_cost()
        return recurring_cost

    def get_development_cost(self):
        """ Returns the non recurring cost of the servicer development, including all modules and the development
            cost among kits for each groups present among kits (this assumes).

        Return:
            (float): cost in Euros
        """
        non_recurring_cost = 0.
        # modules non recurring cost
        for _, module in self.modules.items():
            non_recurring_cost = non_recurring_cost + module.get_non_recurring_cost()
        # find all groups in kits
        kit_groups = []
        for _, kit in self.initial_kits.items():
            if kit.group not in kit_groups:
                kit_groups.append(kit.group)
        # for each kit group, find maximum development cost
        for group in kit_groups:
            max_kit_development_cost = 0.
            for _, kit in self.initial_kits.items():
                if kit.group == group:
                    kit_development_cost = kit.get_development_cost()
                    if max_kit_development_cost < kit_development_cost:
                        max_kit_development_cost = kit_development_cost
            non_recurring_cost = non_recurring_cost + max_kit_development_cost
        return non_recurring_cost

    def get_phases(self, plan):
        """ Returns all phases from the plan the servicer is assigned to.

        Args:
            plan (Plan): plan for which the fleet needs to be designed

        Return:
            ([Phase]): list of phases
        """
        servicer_phases = []
        for phase in plan.phases:
            if phase.get_assigned_spacecraft() == self:
                servicer_phases.append(phase)
        return servicer_phases

    def get_reference_manoeuvres(self, plan, module):
        """ Returns representative values for the servicer corresponding to:
            - maximum delta v among maneuvers (used to dimension the main propulsion system
            - total mass of propellant used during approaches (used to dimension the rcs propulsion system)

        Args:
            plan (Plan): plan for which the fleet needs to be designed
            module (GenericModule): module to be added

        Return:
            (u.m/u.s): delta v
            (u.kg): rcs propellant mass
        """
        reference_delta_v = 0. * u.m / u.s
        rcs_prop_mass = 0. * u.kg
        for phase in self.get_phases(plan):
            if phase.assigned_module == module:
                if isinstance(phase, OrbitChange):
                    phase_delta_v = phase.get_delta_v()
                    if phase_delta_v > reference_delta_v:
                        reference_delta_v = phase_delta_v
                if isinstance(phase, Approach):
                    rcs_prop_mass += phase.propellant
        return reference_delta_v.to(u.m / u.s), rcs_prop_mass

    def get_reference_power(self):
        """ Returns a reference power used as input for different models. This reference represents the mean power
            conditioned by the servicer during nominal operations.

        Return:
            (u.W): mean servicer power drawn
        """
        nominal_power_draw = 0. * u.W
        for _, module in self.modules.items():
            nominal_power_draw = nominal_power_draw + module.get_reference_power()
        return nominal_power_draw

    def get_reference_inertia(self):
        """ Returns estimated inertia of the servicer along its main axis based on a generic box and wings shape.
            Used for estimations of required mass for aocs systems.

        Return:
            (u.kg*u.m*u.m): servicer inertia
        """
        # TODO: check this models
        # compute inertia of spacecraft without solar arrays (simple scaling from a reference point of 100kg)
        box_inertia = 100. * u.kg * u.m * u.m * (self.get_wet_mass(contingency=False).to(u.kg).value / 200.) ** (5 / 3)
        # compute inertia of solar arrays (simple scaling from a reference of 600W)
        solar_array_inertia = 50. * u.kg * u.m * u.m * (self.get_reference_power().to(u.W).value / 600.)
        return (box_inertia + solar_array_inertia).to(u.kg * u.m * u.m)

    def get_attribute_history(self, attribute_name, plan):
        """ Get the time evolution of an attribute of the servicer over the phases of a plan.
            The information must be returned in a method of a servicer or phase or an attribute of an orbit.

        Arg:
            attribute_name (str): name of an attribute of "get_" method
            plan (Plan): plan for which the fleet needs to be designed

        Return:
              ([<>]): List of values for the queried data
              ([epoch]): list of epochs for each data point
              ([str]): list of phases id for each data point
        """
        # get class method name
        data = []
        time = []
        phase_id = []
        for phase in self.get_phases(plan):
            # check if this is available in the Scenario class
            if hasattr(phase, attribute_name):
                data.append(getattr(phase, attribute_name))
                time.append(phase.spacecraft_snapshot.current_orbit.epoch)
                phase_id.append(phase.ID)
            elif hasattr(phase.spacecraft_snapshot, attribute_name):
                data.append(getattr(phase.spacecraft_snapshot, attribute_name)())
                time.append(phase.spacecraft_snapshot.current_orbit.epoch)
                phase_id.append(phase.ID)
            elif hasattr(phase.spacecraft_snapshot.current_orbit, attribute_name):
                data.append(getattr(phase.spacecraft_snapshot.current_orbit, attribute_name))
                time.append(phase.spacecraft_snapshot.current_orbit.epoch)
                phase_id.append(phase.ID)
            else:
                return False
        return data, time, phase_id

    def get_capture_module(self):
        """ Returns default capture module of servicer. Used to simplify scenario creation.

        Return:
            (Module): module
        """
        try:
            return self.modules[self.capture_module_ID]
        except KeyError:
            return False

    def get_main_propulsion_module(self):
        """ Returns default main propulsion module of servicer. Used to simplify scenario creation.

        Return:
            (Module): module
        """
        try:
            return self.modules[self.main_propulsion_module_ID]
        except KeyError:
            return None

    def get_rcs_propulsion_module(self):
        """ Returns default rcs propulsion module of servicer. Used to simplify scenario creation.

        Return:
            (Module): module
        """
        try:
            return self.modules[self.rcs_propulsion_module_ID]
        except KeyError:
            return None

    def print_report(self):
        print(f"Built-in function print report not defined for Class: {type(self)}")

    def __str__(self):
        return (self.id
                + "\n\t  dry mass: " + '{:.01f}'.format(self.get_dry_mass()))    

class Servicer(Spacecraft):
    """Servicer is an object that performs phases in the plan using its modules.
    A servicer can have any number of modules of any type. A servicer can also host other servicers as in the
    case of current_kits. The mass of the servicer depends on the hosted modules. The servicer has a current orbit and
    mass that will be modified during each applicable phase. The class is initialized with no modules and no orbit.
    It is added to the fleet specified as argument.

    TODO: remove expected_number_of_targets

    Args:
        servicer_id (str): Standard id. Needs to be unique.
        group (str): describes what the servicer does (servicing, refueling, ...)
        expected_number_of_targets (int): expected number of targets assigned to the servicer
        additional_dry_mass (u.kg): additional mass, excluding the modules, used to easily tweak dry mass

    Attributes:
        ID (str): Standard id. Needs to be unique.
        expected_number_of_targets (int): expected number of targets assigned to the servicer
        additional_dry_mass (u.kg): additional mass, excluding the modules, used to easily tweak dry mass
        current_orbit (poliastro.twobody.Orbit): Orbit of the servicer at current time.
        modules (dict): Dictionary of modules contained in the servicer.
        main_propulsion_module_ID (str): id of the default module to be used for phasing on this servicer
        rcs_propulsion_module_ID (str): id of the default module to be used for rendezvous on this servicer
        capture_module_ID (str): id of the default module to be used for capture on this servicer
        initial_kits (dict): Dictionary of other servicers contained in the servicer at time 0.
        current_kits (dict): Dictionary of other servicers contained in the servicer at current time.
        assigned_tanker (Servicer): in case of refueling architecture, assigned_tanker assigned to refuel the servicer
        assigned_targets (list): List of targets in the order of servicing (used during planning)
        mothership (Servicer): Mothership hosting the servicer if the servicer is a kit
        mass_contingency (float): contingency to apply at system level on the dry mass
    """

    """
    Init
    """
    def __init__(self, servicer_id, group, expected_number_of_targets=3, additional_dry_mass=0. * u.kg,mass_contingency=0.2):
        super(Servicer, self).__init__(servicer_id,group,additional_dry_mass,mass_contingency)
        self.expected_number_of_targets = expected_number_of_targets

    """
    Methods
    """
    def assign_targets(self, targets_assigned_to_servicer):
        # TODO: check if can be put into scenario
        # update initial propellant guess if less targets than expected
        initial_propellant_mass = self.get_main_propulsion_module().initial_propellant_mass
        corrected_propellant_mass = (initial_propellant_mass
                                     * len(targets_assigned_to_servicer) / self.expected_number_of_targets)
        self.get_main_propulsion_module().initial_propellant_mass = corrected_propellant_mass
        for target in targets_assigned_to_servicer:
            self.assigned_targets.append(target)

    def assign_tanker(self, tanker):
        """ Adds another servicer to the Servicer class as assigned_tanker.
        TODO: get into scenario

        Args:
            tanker (Servicer): servicer to be added as assigned_tanker
        """
        self.assigned_tanker = tanker

    def get_module_mass(self, module_name, contingency=True):
        """ Returns the dry mass of a particular module based on the name of its class.

        TODO: remove
        Args:
            module_name (str): name of the module class, must be linked to a class as such: <module_name>Module
            contingency (boolean): if True, apply contingencies

        Return:
            (u.kg): mass of the module for the servicer
        """
        dry_mass = 0. * u.kg
        for _, module in self.modules.items():
            if module.__class__.__name__ == module_name + 'Module':
                dry_mass += module.get_current_dry_mass(contingency=contingency)
        return dry_mass

    def get_module_recurring_cost(self, module_name):
        """ Returns the dry mass of a particular module based on the name of its class.

        TODO: remove

        Args:
            module_name (str): name of the module class, must be linked to a class as such: <module_name>Module

        Return:
            (float): cost in Euros
        """
        recurring = 0.
        for _, module in self.modules.items():
            if module.__class__.__name__ == module_name + 'Module':
                recurring += module.get_hardware_recurring_cost()
        return recurring

    def get_module_non_recurring_cost(self, module_name):
        """ Returns the dry mass of a particular module based on the name of its class.

        TODO: remove

        Args:
            module_name (str): name of the module class, must be linked to a class as such: <module_name>Module

        Return:
            (float): cost in Euros
        """
        non_recurring = 0.
        for _, module in self.modules.items():
            if module.__class__.__name__ == module_name + 'Module':
                non_recurring += module.get_development_cost()
        return non_recurring

    def assign_kit(self, kit):
        """Adds a kit to the servicer as kit. The servicer becomes the kit's mothership.

        Args:
            kit (Servicer): servicer to be added as kit
        """
        if kit in self.current_kits:
            warnings.warn('Kit ', kit.ID, ' already in servicer ', self.id, '.', UserWarning)
        else:
            self.initial_kits[kit.ID] = kit
            self.current_kits[kit.ID] = kit
            kit.mothership = self

    def separate_kit(self, kit):
        """ Separate a kit from the servicer. This is used during simulation.
        The kit is still assigned to the servicer and will be linked if the servicer is reset.

        Args:
            kit (Servicer): kit to be removed from servicer
        """
        if kit.ID in self.current_kits:
            del self.current_kits[kit.ID]
        else:
            warnings.warn('No kit ', kit.ID, ' in servicer ', self.id, '.', UserWarning)

    def separate_sat(self, sat):
        """ Separate a sat from the servicer. This is used during simulation.
        The sat is still assigned to the servicer and will be linked if the servicer is reset.

        Args:
            sat (Client): sat to be removed from launcher
        """
        if sat.ID in self.current_sats:
            del self.current_sats[sat.ID]
        else:
            warnings.warn('No sat ', sat.ID, ' in servicer ', self.id, '.', UserWarning)

    def assign_sats(self, targets_assigned_to_servicer):
        """Adds sats to the Servicer as Target. The Servicer becomes the sat's mothership.

        Args:
            targets_assigned_to_servicer:
        """
        # TODO: check if can be put into scenario
        for target in targets_assigned_to_servicer:
            if target in self.current_sats:
                warnings.warn('Satellite ', target.ID, ' already in Servicer ', self.id, '.', UserWarning)
            else:
                self.initial_sats[target.ID] = target
                self.current_sats[target.ID] = target
                target.mothership = self
            self.assigned_targets.append(target)

    def get_current_mass(self):
        """Returns the total mass of the servicer, including all modules and kits at the current time in the simulation.

        Return:
            (u.kg): current mass, including kits
        """
        # servicer dry mass (with contingency)
        temp_mass = self.additional_dry_mass
        for _, module in self.modules.items():
            temp_mass = temp_mass + module.get_dry_mass()
        temp_mass = temp_mass * (1 + self.mass_contingency)
        # servicer prop mass and captured target mass
        for _, module in self.modules.items():
            if isinstance(module, PropulsionModule):
                temp_mass = temp_mass + module.get_current_prop_mass()
            if isinstance(module, CaptureModule):
                if module.captured_object:
                    temp_mass = temp_mass + module.captured_object.get_current_mass()
        # kits mass
        for _, kit in self.current_kits.items():
            temp_mass = temp_mass + kit.get_current_mass()
        return temp_mass

    def reset(self, plan, design_loop=True, convergence_margin=1. * u.kg, verbose=False):
        """Reset the servicer current orbit and mass to the parameters given during initialization.
        This function is used to reset the state of all modules after a simulation.
        If this is specified as a design loop, the sub-systems can be updated based on different inputs.
        It also resets the current_kits and the servicer orbits.

        Args:
            plan (Plan): plan for which the servicer is used and designed
            design_loop (boolean): if True, redesign modules after resetting them
            convergence_margin (u.kg): accuracy required on propellant mass for convergence_margin
            verbose (boolean): if True, print convergence_margin information
        """
        # reset orbit
        self.current_orbit = None

        # reset current_kits
        for _, kit in self.initial_kits.items():
            kit.reset(plan, design_loop=False, verbose=verbose)
            self.current_kits[kit.ID] = kit

        # reset modules
        for _, module in self.modules.items():
            module.reset()
        if design_loop:
            self.design(plan, convergence_margin=convergence_margin, verbose=verbose)

    def get_refueling_modules(self):
        """ Returns only modules that can offer refueling to other servicers.

        Return:
            (dict(Module)): dictionary of the modules
        """
        available_module = {}
        for _, module in self.modules.items():
            if isinstance(module, PropulsionModule):
                if module.is_refueler:
                    available_module[module.id] = module
        return available_module

    def get_propulsion_modules(self):
        """ Returns all modules that contain propellant. This is used for fleet convergence.

        Note: This includes propulsion modules that belong to kits assigned to the servicer. Kits are converged with
        their mothership.

        Return:
            (dict(Module)): dictionary of the modules
        """
        prop_modules = {ID: module for ID, module in self.modules.items() if isinstance(module, PropulsionModule)}
        for _, kit in self.initial_kits.items():
            prop_modules.update(kit.get_propulsion_modules())
        return prop_modules

    def get_capture_modules(self):
        """ Returns only modules that can capture targets of simulation at current time.

        Return:
            (dict(Module)): dictionary of the modules
        """
        capture_modules = {ID: module for ID, module in self.modules.items() if isinstance(module, CaptureModule)}
        for _, kit in self.current_kits.items():
            capture_modules.update(kit.get_capture_modules())
        return capture_modules

    def change_orbit(self, orbit):
        """ Changes the current_orbit of the servicer and linked objects.

        Args:
            orbit (poliastro.twobody.Orbit): orbit where the servicer will be after update
        """
        # servicer own orbit
        self.current_orbit = orbit
        # orbit of capture objects
        for _, capture_module in self.get_capture_modules().items():
            if capture_module.captured_object:
                capture_module.captured_object.current_orbit = orbit
        # orbit of kits
        for _, kit in self.current_kits.items():
            kit.change_orbit(orbit)

    def print_report(self):
        """ Print quick summary for debugging purposes."""
        print('----------------------------------------------------------------')
        print(self.id)
        print('Dry mass : ' + '{:.01f}'.format(self.get_dry_mass()))
        print('Wet mass : ' + '{:.01f}'.format(self.get_wet_mass()))
        print('Modules : ')
        for _, module in self.modules.items():
            print(module)
        print('Phasing : ' + self.main_propulsion_module_ID)
        print('RDV : ' + self.rcs_propulsion_module_ID)
        print('Capture : ' + self.capture_module_ID)
        print('Mothership : ' + str(self.mothership))
        print('Kits : ')
        for _, kit in self.current_kits.items():
            kit.print_report()

class UpperStage(Spacecraft):
    """UpperStage is an object that performs phases in the plan using its modules.
    A UpperStage can have any number of modules of any type. A servicer can also host other servicers as in the
    case of current_kits. The mass of the servicer depends on the hosted modules. The servicer has a current orbit and
    mass that will be modified during each applicable phase. The class is initialized with no modules and no orbit.
    It is added to the fleet specified as argument.

    TODO: change description

    Args:
        servicer_id (str): Standard id. Needs to be unique.
        group (str): describes what the servicer does (servicing, refueling, ...)
        expected_number_of_targets (int): expected number of targets assigned to the servicer
        additional_dry_mass (u.kg): additional mass, excluding the modules, used to easily tweak dry mass

    Attributes:
        id (str): Standard id. Needs to be unique.
        expected_number_of_targets (int): expected number of targets assigned to the servicer
        additional_dry_mass (u.kg): additional mass, excluding the modules, used to easily tweak dry mass
        current_orbit (poliastro.twobody.Orbit): Orbit of the servicer at current time.
        modules (dict): Dictionary of modules contained in the servicer.
        main_propulsion_module_ID (str): id of the default module to be used for phasing on this servicer
        rcs_propulsion_module_ID (str): id of the default module to be used for rendezvous on this servicer
        capture_module_ID (str): id of the default module to be used for capture on this servicer
        initial_kits (dict): Dictionary of other servicers contained in the servicer at time 0.
        current_kits (dict): Dictionary of other servicers contained in the servicer at current time.
        assigned_tanker (Servicer): in case of refueling architecture, assigned_tanker assigned to refuel the servicer
        assigned_targets (list): List of targets in the order of servicing (used during planning)
        mothership (Servicer): Mothership hosting the servicer if the servicer is a kit
        mass_contingency (float): contingency to apply at system level on the dry mass
    """


    """
    Init
    """
    def __init__(self, launch_vehicle_id, scenario, additional_dry_mass=0. * u.kg,mass_contingency=0.2):
        super(UpperStage, self).__init__(launch_vehicle_id,"launcher",additional_dry_mass,mass_contingency,scenario.starting_epoch)
        self.launcher_name = scenario.launcher_name
        self.reference_satellite = scenario.reference_satellite
        self.volume_available = None
        self.mass_available = None
        self.insertion_orbit = scenario.launcher_insertion_orbit
        self.disposal_orbit = scenario.launcher_disposal_orbit
        self.mass_filling_ratio = 1
        self.volume_filling_ratio = 1
        self.disp_mass = 0. * u.kg
        self.disp_volume = 0. * u.m ** 3
        self.satellites_allowance = 0
        self.delta_inc_for_raan_from_scenario = scenario.mission_cost_vs_duration_factor
        self.delta_inc_for_raan_from_opti = 0.

        # Compute initial performances
        self.compute_upperstage(scenario)

    """
    Methods
    """
    def execute_with_fuel_usage_optimisation(self,clients):
        # check default cases
        if self.mainpropulsion.current_propellant_mass < 0.:
            logging.info(f"Remaining fuel is negative, remove a satellite")
            return False

        # initialise algorithm's variables
        remaining_fuel_prev = 0.
        self.delta_inc_for_raan_from_opti = 0. # % of MODEL_RAAN_DELTA_INCLINATION_HIGH

        delta_inc_up = 1. # % of MODEL_RAAN_DELTA_INCLINATION_HIGH
        delta_inc_low = 0. # % of MODEL_RAAN_DELTA_INCLINATION_HIGH
        nb_iter = 0
        nb_iter_max = int(MODEL_RAAN_DELTA_INCLINATION_HIGH/(2*MODEL_RAAN_DELTA_INCLINATION_LOW))+1
        converged = False

        # find inclination change minimising plan's remaining fuel
        #   exit condition 1: no remaining fuel variation between two loops (converge)
        #   exit condition 2: relative inclination change is below tolerance (converge)
        #   exit condition 3: max iter achieved (not converge)
        while not(converged) and nb_iter < nb_iter_max:
            # set recursing variables
            remaining_fuel_prev = self.mainpropulsion.current_propellant_mass
            nb_iter += 1

            # compute remaining fuel for new inclination change
            self.delta_inc_for_raan_from_opti = (delta_inc_up+delta_inc_low)/2
            self.execute(clients,self.satellites_allowance)

            # define new inclination's range
            if self.mainpropulsion.current_propellant_mass-UPPERSTAGE_REMAINING_FUEL_MARGIN >= 0:
                delta_inc_low = self.delta_inc_for_raan_from_opti
            else:
                delta_inc_up = self.delta_inc_for_raan_from_opti

            # detect algorithm's convergence
            if MODEL_RAAN_DELTA_INCLINATION_HIGH*(delta_inc_up-delta_inc_low) <= 2*MODEL_RAAN_DELTA_INCLINATION_LOW \
            or abs(self.mainpropulsion.current_propellant_mass-remaining_fuel_prev) <= UPPERSTAGE_REMAINING_FUEL_TOLERANCE:
                converged = True

        # ensure remaining fuel is positive
        if self.mainpropulsion.current_propellant_mass-UPPERSTAGE_REMAINING_FUEL_MARGIN < 0.:
            self.delta_inc_for_raan_from_opti = delta_inc_low
            self.execute(clients,self.satellites_allowance)

        return converged

    def execute(self,clients,custom_sat_allowance):
        """ Reset, redesign and compute the upperstage plan based on clients and satellite allowance

        Args:
            clients (Scenario.ConstellationSatellite.Constellation): clients/constellation to consider
            upperstage_cur_sat_allowance: allowance to assign to the launcher (for iterative purpose)
        """
        # Perform initial setup (mass and volume available)
        self.reset()

        # Compute launcher design for custom satellite allowance
        self.design(custom_sat_allowance=custom_sat_allowance)

        # Assign target as per mass and volume allowance
        self.assign_ordered_satellites(clients)

        # Define spacecraft mission profile
        self.define_mission_profile(clients.get_global_precession_rotation())

        # Execute upperstage (Apply owned plan)
        self.execute_plan()

    def reset(self):
        """ Reset the object to inital parameters. Empty the plan
        """
        # Reset attribut
        self.current_orbit = None
        self.mass_filling_ratio = 1
        self.volume_filling_ratio = 1
        self.disp_mass = 0. * u.kg
        self.disp_volume = 0. * u.m ** 3

        # Empty the plan
        self.empty_plan()

        # Empty targets
        self.assigned_targets = []
        self.sats_number = len(self.assigned_targets)
    
    def design(self,custom_sat_allowance=None,tech_level=1):
        """ Design the upperstage based on allowance, tech_level and current performances

        Args:
            custom_sat_allowance: allowance to assign to the launcher (for iterative purpose)
            tech_level: dispenser technology level
        """
        # If custom_sat_allowance provided, update upperstage allowance
        if not(custom_sat_allowance == None):
            self.satellites_allowance = custom_sat_allowance

        # Compute filling ratio and disp mass and volume
        self.total_satellites_mass = self.satellites_allowance * self.reference_satellite.get_initial_mass()
        self.mass_filling_ratio = self.total_satellites_mass / self.mass_available
        self.volume_filling_ratio = (self.satellites_allowance * self.reference_satellite.get_volume()) / self.volume_available

        # Add dispenser as CaptureModule
        dispenser_mass = 0.1164 * self.total_satellites_mass / tech_level
        dispenser_volume = (0.0114 * dispenser_mass.to(u.kg).value / tech_level) * u.m ** 3
        self.dispenser = CaptureModule(self.id + '_Dispenser',
                                            self,
                                            mass_contingency=0.0,
                                            dry_mass_override=dispenser_mass)
        self.dispenser.define_as_capture_default()

        # Add propulsion as PropulsionModule
        self.mainpropulsion = PropulsionModule(self.id + '_MainPropulsion',
                                                        self, 'bi-propellant', 294000 * u.N,
                                                        294000 * u.N, 330 * u.s, UPPERSTAGE_INITIAL_FUEL_MASS,
                                                        5000 * u.kg, reference_power_override=0 * u.W,
                                                        propellant_contingency=0.05, dry_mass_override=UPPERSTAGE_PROPULSION_DRY_MASS,
                                                        mass_contingency=0.2)
        self.mainpropulsion.define_as_main_propulsion()
    
    def assign_ordered_satellites(self,clients):
        """ Assigned remaining ordered satellites to current launcher within allowance

        Args:
            clients (Scenario.ConstellationSatellite.Constellation): clients/constellation to consider
        """
        # Remaining satellite to be delivered
        available_satellites = clients.get_optimized_ordered_satellites()

        # Assign sats
        self.assign_sats(available_satellites[0:self.satellites_allowance])
    
    def assign_sats(self, satellite_assigned_to_upperstage):
        """Adds sats to the UpperStage as Target. The UpperStage becomes the sat's mothership.

        Args:
            satellite_assigned_to_upperstage (Scenario.ConstellationSatellite.Satellite): List of satellites to assign to the upperstage
        """
        # TODO: check if can be put into scenario
        for target in satellite_assigned_to_upperstage:
            if target in self.current_sats:
                logging.warning('Satellite '+ target.ID+ ' already in UpperStage '+ self.id+ '.')
            else:
                self.initial_sats[target.ID] = target
                self.current_sats[target.ID] = target
                target.mothership = self
            self.assigned_targets.append(target)

        # Update number of satellites
        self.sats_number = len(self.assigned_targets)

    def execute_plan(self):
        """ Apply own plan
        """
        # Apply plan
        self.plan.apply()

    def compute_upperstage(self,scenario):
        """ Compute upperstage initial capacities

        Args:
            scenario (Scenario.ScenarioConstellation): encapsulating scenario
        """
        # Interpolate launcher performance + correction
        self.compute_mass_available(scenario)

        # Interpolate launcher fairing capacity + correction
        self.compute_volume_available(scenario)

    def compute_mass_available(self,scenario):
        """ Compute the satellite performance

        Args:
            scenario (Scenario.ScenarioConstellation): encapsulating scenario
        """
        # Check for custom launcher_name values
        if scenario.custom_launcher_name is None:
            logging.info(f"Gathering Launch Vehicle performance from database...")
            # Compute launcher capabilities to deliver into orbit
            launcher_performance = get_launcher_performance(scenario.fleet,
                                                            scenario.launcher_name,
                                                            scenario.launch_site,
                                                            self.insertion_orbit.inc.value,
                                                            scenario.apogee_launcher_insertion.value,
                                                            scenario.perigee_launcher_insertion.value,
                                                            scenario.orbit_type,
                                                            method=scenario.interpolation_method,
                                                            verbose=scenario.verbose,
                                                            save="InterpolationGraph",
                                                            save_folder=scenario.data_path)

            # Substract UpperStage mass
            self.mass_available = launcher_performance
        else:
            logging.info(f"Using custom Launch Vehicle performance...")
            self.mass_available = scenario.custom_launcher_performance

    def compute_volume_available(self,scenario):
        """ Estimate the satellite volume based on mass

        Args:
            scenario (Scenario.ScenarioConstellation): encapsulating scenario
        """
        # Check for custom launcher_name values
        if scenario.fairing_diameter is None and scenario.fairing_cylinder_height is None and scenario.fairing_total_height is None:
            if scenario.custom_launcher_name is not None or scenario.custom_launcher_performance is not None:
                raise ValueError("You have inserted a custom launcher, but forgot to insert its related fairing size.")
            else:
                logging.info(f"Gathering Launch Vehicle's fairing size from database...")
                self.volume_available = get_launcher_fairing(self.launcher_name)
        else:
            logging.info(f"Using custom Launch Vehicle's fairing size...")
            cylinder_volume = np.pi * (scenario.fairing_diameter * u.m / 2) ** 2 * scenario.fairing_cylinder_height * u.m
            cone_volume = np.pi * (scenario.fairing_diameter * u.m / 2) ** 2 * (scenario.fairing_total_height * u.m - scenario.fairing_cylinder_height * u.m)
            self.volume_available = (cylinder_volume + cone_volume).to(u.m ** 3)
    
    def compute_allowance(self,unassigned_satellites):
        """ Compute satellites allowance based on reference satellite dimensions and capacities
        """
        # Compute limit in mass terms
        limit_mass = math.floor(self.mass_available/self.reference_satellite.get_initial_mass())

        # Compute limit in volume terms
        limit_volume = math.floor(self.volume_available/self.reference_satellite.get_volume())

        # Minimal value is of interest
        self.satellites_allowance =  min([limit_volume,limit_mass,len(unassigned_satellites)])

        # Return allowance
        return self.satellites_allowance

    def separate_sat(self, satellite):
        """ Separate a sat from the launcher. This is used during simulation.
            The sat is still assigned to the launcher and will be linked if the launcher is reset.

        Args:
            sat (Client): sat to be removed from launcher
        """
        if satellite.ID in self.current_sats:
            del self.current_sats[satellite.ID]
        else:
            logging.warning('No sat '+ satellite.ID +' in launcher '+ self.id+ '.')

    def get_satellites_allowance(self):
        """ Return maximum allowable of the upperstage
        """
        return self.satellites_allowance

    def get_current_mass(self):
        """ Returns the total mass of the launcher, including all modules and kits at the current time in the simulation.

        Return:
            (u.kg): current mass, including kits
        """
        # launcher dry mass (with contingency)
        temp_mass = self.additional_dry_mass
        for _, module in self.modules.items():
            temp_mass = temp_mass + module.get_dry_mass()
        temp_mass = temp_mass * (1 + self.mass_contingency)
        # launcher prop mass and captured target mass
        for _, module in self.modules.items():
            if isinstance(module, PropulsionModule):
                temp_mass = temp_mass + module.get_current_prop_mass()
            if isinstance(module, CaptureModule):
                if module.captured_object:
                    temp_mass = temp_mass + module.captured_object.get_current_mass()
        # kits mass
        for _, sats in self.current_sats.items():
            temp_mass = temp_mass + sats.get_current_mass()
        return temp_mass

    def get_initial_mass(self):
        """ Returns the total mass of the launcher, including all modules and kits at the launch time in the simulation.

        Return:
            (u.kg): current mass, including kits
        """
        temp_mass = 0

        prop_modules =  self.get_propulsion_modules()
        temp_mass += sum([(prop_modules[key].get_initial_prop_mass()+prop_modules[key].get_dry_mass()) for key in prop_modules.keys()])

        capt_modules =  self.get_capture_modules()
        temp_mass += sum([capt_modules[key].get_dry_mass() for key in capt_modules.keys()])

        temp_mass += sum([satellite.initial_mass for satellite in self.assigned_targets])

        return temp_mass

    def get_propulsion_modules(self):
        """ Returns all modules that contain propellant. This is used for fleet convergence.

        Note: This includes propulsion modules that belong to kits assigned to the servicer. Kits are converged with
        their mothership.

        Return:
            (dict(Module)): dictionary of the modules
        """
        prop_modules = {ID: module for ID, module in self.modules.items() if isinstance(module, PropulsionModule)}
        return prop_modules

    def get_capture_modules(self):
        """ Returns only modules that can capture targets of simulation at current time.

        Return:
            (dict(Module)): dictionary of the modules
        """
        capture_modules = {ID: module for ID, module in self.modules.items() if isinstance(module, CaptureModule)}
        return capture_modules

    def get_modules_initial_mass(self):
        """ Returns all modules initial mass

        Return:
            (dict(Module)): dictionary of the modules
        """
        return sum([module.get_initial_mass() for _,module in self.modules.items()])

    def change_orbit(self, orbit):
        """ Changes the current_orbit of the servicer and linked objects.

        Args:
            orbit (poliastro.twobody.Orbit): orbit where the servicer will be after update
        """
        # Upperstage own orbit
        self.previous_orbit = self.current_orbit
        self.current_orbit = orbit

        # Captured objects orbit
        for _, capture_module in self.get_capture_modules().items():
            if capture_module.captured_object:
                capture_module.captured_object.current_orbit = orbit

    def compute_delta_inclination_for_raan_phasing(self):
        """ Computes the inclination change for RAAN phasing basd on two ratios:
        self.delta_inc_for_raan_from_scenario: lets the senario define how much dV should be used to accelrate phasing
        self.delta_inc_for_raan_from_opti: used by optimisation loop minimising phasing duration with the available fuel
        """
        total_ratio = self.delta_inc_for_raan_from_scenario + self.delta_inc_for_raan_from_opti
        range = MODEL_RAAN_DELTA_INCLINATION_HIGH - MODEL_RAAN_DELTA_INCLINATION_LOW
        return total_ratio*range + MODEL_RAAN_DELTA_INCLINATION_LOW

    def define_mission_profile(self,precession_direction):
        """ Define launcher profile by creating and assigning adequate phases for a typical servicer_group profile.

        Args:
            launcher (Fleet_module.UpperStage): launcher to which the profile will be assigned
            precession_direction (int): 1 if counter clockwise, -1 if clockwise (right hand convention)
        """
        # Update insertion raan, supposing each target can be sent to an ideal raan for operation
        # TODO : implement a launch optimizer
        
        # Insertion orbit margin
        insertion_raan_margin = INSERTION_RAAN_MARGIN
        insertion_raan_window = INSERTION_RAAN_WINDOW
        insertion_a_margin = INSERTION_A_MARGIN

        # Contingencies and cutoff
        delta_v_contingency = CONTINGENCY_DELTA_V
        raan_cutoff = MODEL_RAAN_DIRECT_LIMIT

        # Extract first target
        first_target = self.assigned_targets[0]

        ##########
        # Step 1: Insertion Phase
        ##########      
        # Compute insertion orbit
        insertion_orbit = Orbit.from_classical(Earth,
                                               self.insertion_orbit.a - insertion_a_margin,
                                               self.insertion_orbit.ecc,
                                               self.insertion_orbit.inc,
                                               first_target.insertion_orbit.raan - precession_direction * insertion_raan_margin,
                                               self.insertion_orbit.argp,
                                               self.insertion_orbit.nu,
                                               self.insertion_orbit.epoch)

        # Add Insertion phase to the plan
        insertion = Insertion(f"({self.id}) Goes to insertion orbit",self.plan, insertion_orbit, duration=1 * u.h)

        # Assign propulsion module to insertion phase
        insertion.assign_module(self.get_main_propulsion_module())

        ##########
        # Step 2: Raise from insertion to constellation orbit
        ##########
        # Add Raising phase to plan
        raising = OrbitChange(f"({self.id}) goes to first target orbit ({first_target.ID})",
                              self.plan,
                              first_target.insertion_orbit,
                              raan_specified=True,
                              initial_orbit=insertion_orbit,
                              raan_cutoff=raan_cutoff,
                              raan_phasing_absolute=True,
                              delta_v_contingency=delta_v_contingency)

        # Assign propulsion module to raising phase
        raising.assign_module(self.get_main_propulsion_module())

        ##########
        # Step 3: Iterate through organised assigned targets
        ##########
        # Initialise current orbit object
        current_orbit = first_target.insertion_orbit

        # Loop over assigned targets
        for i, current_target in enumerate(self.assigned_targets):
            # Print target info
            #print(i,current_target,current_target.insertion_orbit,current_target.current_orbit)

            # Check for RAAN drift
            if abs(current_target.insertion_orbit.raan - current_orbit.raan) > insertion_raan_window:
                # TODO Compute ideal phasing orgit
                phasing_orbit = copy.deepcopy(current_target.insertion_orbit)
                phasing_orbit.inc += self.compute_delta_inclination_for_raan_phasing()

                # Reach phasing orbit and add to plan
                phasing = OrbitChange(f"({self.id}) goes to ideal phasing orbit",
                                      self.plan,
                                      phasing_orbit,
                                      raan_specified=False,
                                      delta_v_contingency=delta_v_contingency)

                # Assign propulsion module to OrbitChange phase
                phasing.assign_module(self.get_main_propulsion_module())

                # Change orbit back to target orbit and add to plan
                raising = OrbitChange(f"({self.id}) goes to next target ({current_target.ID})",
                                      self.plan,
                                      current_target.insertion_orbit,
                                      raan_specified=True,
                                      initial_orbit=phasing_orbit,
                                      delta_v_contingency=delta_v_contingency,
                                      raan_cutoff=raan_cutoff)

                # Assign propulsion module to OrbitChange phase
                raising.assign_module(self.get_main_propulsion_module())
            
            # Add Release phase to the plan
            deploy = Release(f"Satellites ({current_target.ID}) released",
                             self.plan,
                             current_target,
                             duration=20 * u.min)

            # Assign capture module to the Release phase
            deploy.assign_module(self.get_capture_module())

            # Set current_target to deployed
            current_target.state = "Deployed"

            # Update current orbit
            current_orbit = current_target.insertion_orbit

        ##########
        # Step 4: De-orbit the launcher
        ##########
        # Add OrbitChange to the plan
        removal = OrbitChange(f"({self.id}) goes to disposal orbit", self.plan, self.disposal_orbit,delta_v_contingency=delta_v_contingency)

        # Assign propulsion module to OrbitChange phase
        removal.assign_module(self.get_main_propulsion_module())

    def print_report(self):
        self.plan.print_report()
        """ Print quick summary for debugging purposes."""
        print(f"""---\n---
Launch Vehicles:
    ID: {self.id}
    Launch vehicle name: {self.launcher_name}
    Dry mass: {self.get_dry_mass():.01f}
    Wet mass: {self.get_wet_mass():.01f}
    Fuel mass margin: {self.get_main_propulsion_module().current_propellant_mass:.2f}
    Payload mass available: {self.mass_available}
    Number of satellites: {self.sats_number}
    Dispenser mass: {self.disp_mass:.1f}
    Mass filling ratio: {self.mass_filling_ratio * 100:.1f}%
    Dispenser volume: {self.disp_volume:.1f}
    Volume filling ratio: {self.volume_filling_ratio * 100:.1f}%
    Targets assigned to the Launch vehicle:""")

        for x in range(len(self.assigned_targets)):
            print(f"\t\t{self.assigned_targets[x]}")

        print("---")

        print('Modules:')
        for _, module in self.modules.items():
            print(f"\tModule ID: {module}")
        print('\tPhasing Module ID: ' + self.main_propulsion_module_ID)
        print('\tRDV module ID: ' + self.rcs_propulsion_module_ID)
        print('\tCapture module ID : ' + self.capture_module_ID)