import logging
import warnings

import numpy as np
from astropy import units as u

from Modules.CaptureModule import CaptureModule
from Modules.PropulsionModule import PropulsionModule
from Phases.Approach import Approach
from Phases.OrbitChange import OrbitChange


class Fleet:
    """ A Fleet consists of a dictionary of servicers.
    The class is initialized with an emtpy dictionary of servicers.
    It contains methods used during simulation and convergence of the servicers design.

    Args:
        fleet_id (str): Standard id. Needs to be unique.
        architecture (str): descriptor for the overall architecture of the fleet, used to identify scenarios

    Attributes:
        ID (str): Standard id. Needs to be unique.
        architecture (str): descriptor for the overall architecture of the fleet, used to identify scenarios
        servicers (dict): Dictionary of servicers.
    """

    def __init__(self, fleet_id, architecture):
        self.ID = fleet_id
        self.architecture = architecture
        self.servicers = dict()
        self.launchers = dict()
        self.is_performance_graph_already_generated = False

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
            warnings.warn('Servicer ', servicer.ID, ' already in fleet ', self.ID, '.', UserWarning)
        else:
            self.servicers[servicer.ID] = servicer

    def add_launcher(self, launcher):
        """ Adds a launcher to the Fleet class.

        Args:
            launcher (LaunchVehicle): launcher to add to the fleet
        """
        if launcher in self.launchers:
            warnings.warn('Launcher ', launcher.id, ' already in fleet ', self.ID, '.', UserWarning)
        else:
            self.launchers[launcher.id] = launcher

    def design(self, plan, clients, verbose=False, convergence_margin=0.5 * u.kg):
        """ This function calls all appropriate methods to design the fleet to perform a particular plan.
        This is done by first designing each servicer in the fleet to perform its assigned phases in the plan.
        This first convergence determines the design of each module in each servicer, including propellant mass.
        Then, the fleet is homogenized by using the heaviest modules throughout the fleet as basis for the design of
        all servicers. A second convergence is done, this time changing only the propellant mass in each servicer.
        By the end of the method, the fleet is designed so that all servicers are identical and can fulfill their
        assigned plan.

        Args:
            plan (Plan): plan for which the fleet needs to be designed
            clients (<Client module>): class representing the clients of the service
            verbose (boolean): if True, print convergence information
            convergence_margin (u.kg): accuracy required on propellant mass for convergence
        """
        # First, converge fleet so that each servicer is designed for its plan
        if verbose:
            print('\nNon-homogeneous fleet convergence_margin:\n')
        self.converge(plan, clients, convergence_margin=convergence_margin, verbose=verbose, design_loop=True)
        # Make all servicers in fleet the same, based on worst case scenario
        if verbose:
            print('\nHomogenization of fleet:\n')
        for servicer_group in self.get_servicer_groups():
            self.homogenize(plan, servicer_group)
        # Finally, converge fleet again but without redesigning the sub-systems, only changing the propellant masses
        if verbose:
            print('\nHomogeneous fleet convergence_margin:\n')
        self.converge(plan, clients, convergence_margin=convergence_margin, verbose=verbose, design_loop=False)

    def converge(self, plan, clients, convergence_margin=0.5 * u.kg, limit=200, verbose=False, design_loop=True):
        """ Iteratively runs the assigned plan and varies initial propellant mass of the fleet until convergence.
        At each iteration, the fleet is designed for the appropriate propellant mass and the plan is executed.
        Depending on the remaining propellant mass, the initial propellant masses are adjusted until convergence
        within the convergence_margin specified as argument or until the iteration limit specified is reached.

        The first iteration simply adds or remove 1kg of propellant for non converged modules.
        Subsequent iterations use Newton Search with first order finite difference to find the gradient.
        TODO: Implement more advanced convergence algorithm than Newton Search
        
        Note:
            The convergence is dependent on good initial guesses for initial propellant masses.
        
        Args:
            plan (Plan): Dictionary of phases that need to be performed by the fleet.
            clients (<Client module>): Class representing the clients of the service
            convergence_margin (u.kg): accuracy required on propellant mass for convergence
            limit (int): maximal number of iterations before the function quits
            verbose (bool): If True, print information relative to convergence
            design_loop (bool): True if sub-systems dry masses are changed during iterations.
                                False if only the propellant mass is changed.
        """
        # Setup a counter to stop infinite loops and set a convergence flag
        counter = 0
        unconverged = True
        # reset fleet and clients (reset orbits and propellant masses and recompute dry masses if necessary)
        self.reset(plan, design_loop=design_loop, verbose=verbose, convergence_margin=convergence_margin)
        if clients:
            clients.reset()
        # Apply the plan a first time to compute mismatch in propellant
        plan.apply(verbose=False)
        # Enter optimization loop and iterate until limit is reached or all modules converge
        while (unconverged and counter <= limit) or counter < 2:
            if verbose:
                print('Iteration : ' + str(counter) + '/' + str(limit))
            # increase counter
            counter = counter + 1
            # Initialize a dictionary to store unconverged modules
            unconverged = dict()
            # PROPELLANT: For each propulsion module in each servicer, check for remaining fuel at lowest fuel state
            for _, servicer in self.servicers.items():
                for _, module in servicer.get_propulsion_modules().items():
                    # The goal is to have minimal fuel in each tank corresponding to specified mass_contingency
                    min_prop_mass_goal = module.initial_propellant_mass * module.propellant_contingency
                    min_prop_mass = module.get_minimal_propellant_mass(plan)
                    # If the minimal fuel is outside the convergence margin, change initial propellant mass
                    if abs(min_prop_mass.to(u.kg).value - min_prop_mass_goal.to(u.kg).value) > convergence_margin.value:
                        unconverged[module.id] = module
                        # If this is the first run (bo previous step initial propellant mass defined,
                        # the code uses an arbitrary 1kg of propellant opposite the sign of the mismatch as first guess
                        # If not, then this means a previously converged module is not converged anymore after another
                        # module changed. The solution is to restart the convergence of this module with the 1kg guess.
                        # This is not ideal, as it's possible to get stuck in a recursive loop.
                        if (module.previous_initial_propellant_mass is None or
                                module.initial_propellant_mass == module.previous_initial_propellant_mass):
                            new_propellant_mass = (module.initial_propellant_mass
                                                   - np.sign(min_prop_mass - min_prop_mass_goal) * 1. * u.kg)
                        # If this is not the first run, compute gradient using first order finite difference and apply
                        # Newton Search algorithm.
                        else:
                            new_propellant_mass = (module.initial_propellant_mass - (min_prop_mass - min_prop_mass_goal)
                                                   / (((min_prop_mass - min_prop_mass_goal)
                                                       - (module.previous_minimal_propellant_mass - min_prop_mass_goal))
                                                      / (module.initial_propellant_mass
                                                         - module.previous_initial_propellant_mass)))
                        # Reset the module with the new propellant mass while ensuring this mass is positive.
                        new_propellant_mass = max(0. * u.kg, new_propellant_mass)
                        if verbose:
                            print(module.id + " - remaining / initial / new mass : "
                                  + str(min_prop_mass - min_prop_mass_goal)
                                  + " / " + str(module.initial_propellant_mass)
                                  + " / " + str(new_propellant_mass))
                        module.update_initial_propellant_mass(new_propellant_mass, plan)
                    # if by chance the module was already converged on declaration
                    elif counter == 1:
                        if verbose:
                            print(module.id + " - remaining / initial / new mass : "
                                  + str(min_prop_mass - min_prop_mass_goal)
                                  + " / " + str(module.initial_propellant_mass))
                        module.update_initial_propellant_mass(module.initial_propellant_mass, plan)
            # Reset the fleet
            self.reset(plan, design_loop=design_loop, verbose=verbose, convergence_margin=convergence_margin)
            # Reset the clients
            if clients:
                clients.reset()
            # Rerun the plan
            plan.apply(verbose=False)
        if unconverged:
            warnings.warn('No convergence in propellant mass.', RuntimeWarning)

    def homogenize(self, plan, servicer_group):
        """ This method finds the heaviest modules within a group of servicers and redesigns every servicer to match
        these modules. The group of servicers are made based on the group type they are assigned (for instance,
        all motherships will have the same design, all tanks will have the same design, all kits will have the same
        design, etc).

        Args:
            plan (Plan): Dictionary of phases that need to be performed by the fleet.
            servicer_group (str): string identifier for every group in the fleet (group types: servicer, tanker, etc.)
        """
        # Find all servicers with the appropriate servicer_group
        servicers = self.get_servicers_from_group(servicer_group)

        # Find maximum propellants for main prop module
        max_main_propellant_mass = max([servicer.get_main_propulsion_module().initial_propellant_mass
                                        for _, servicer in servicers.items() if servicer.get_main_propulsion_module()],
                                       default=0. * u.kg)
        # Find maximum propellants for rcs prop module (might be the same as the main propulsion module)
        max_rcs_propellant_mass = max([servicer.get_rcs_propulsion_module().initial_propellant_mass
                                       for _, servicer in servicers.items() if servicer.get_rcs_propulsion_module()],
                                      default=0. * u.kg)
        # Find maximum propellants for kit propulsion modules
        max_kits_propellant = 0. * u.kg
        for _, servicer in servicers.items():
            for _, kit in servicer.initial_kits.items():
                max_kits_propellant = max(max_kits_propellant, kit.get_main_propulsion_module().initial_propellant_mass)

        # Reset the servicers with these propellant masses
        for _, servicer in servicers.items():
            if servicer.get_main_propulsion_module():
                # remember the initial propellant mass, replace it by maximum for fleet and redesign the module
                initial_prop_mass = servicer.get_main_propulsion_module().initial_propellant_mass
                servicer.get_main_propulsion_module().initial_propellant_mass = max_main_propellant_mass
                servicer.get_main_propulsion_module().design(plan)
                # reassign initial propellant mass to the new design and reset convergence_margin information
                servicer.get_main_propulsion_module().initial_propellant_mass = initial_prop_mass
                servicer.get_main_propulsion_module().previous_final_propellant_mass = None
                servicer.get_main_propulsion_module().last_refuel_amount = None
            if servicer.get_rcs_propulsion_module():
                # remember the initial propellant mass, replace it by maximum for fleet and redesign the module
                initial_prop_mass = servicer.get_rcs_propulsion_module().initial_propellant_mass
                servicer.get_rcs_propulsion_module().initial_propellant_mass = max_rcs_propellant_mass
                servicer.get_rcs_propulsion_module().design(plan)
                # reassign initial propellant mass to the new design and reset convergence_margin information
                servicer.get_rcs_propulsion_module().initial_propellant_mass = initial_prop_mass
                servicer.get_rcs_propulsion_module().previous_final_propellant_mass = None
                servicer.get_rcs_propulsion_module().last_refuel_amount = None
            for _, kit in servicer.initial_kits.items():
                if kit.get_main_propulsion_module():
                    # remember the initial propellant mass, replace it by maximum for fleet and redesign the module
                    initial_prop_mass = kit.get_main_propulsion_module().initial_propellant_mass
                    kit.get_main_propulsion_module().initial_propellant_mass = max_kits_propellant
                    kit.get_main_propulsion_module().design(plan)
                    # reassign initial propellant mass to the new design and reset convergence_margin information
                    kit.get_main_propulsion_module().initial_propellant_mass = initial_prop_mass
                    servicer.get_main_propulsion_module().previous_final_propellant_mass = None
                    servicer.get_main_propulsion_module().last_refuel_amount = None
            # Reset the whole fleet to recompute the dry masses of all other modules (non propulsion)
            servicer.reset(plan, design_loop=True)

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
        for _, launcher in self.launchers.items():
            launcher.reset(plan, design_loop=design_loop, convergence_margin=convergence_margin, verbose=verbose)


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

    def get_launchers_from_group(self, launcher_group):
        """ Return servicers from the fleet that share a servicer_group.

        Arg:
            servicer_group (str): string identifier for every group in the fleet (group types: servicer, tanker, etc.)

        Return:
            (dict(Servicer)): Dictionary of servicers of the given group
        """
        return {launcher_id: launcher for launcher_id, launcher in self.launchers.items()
                if launcher.group == launcher_group}

    def get_servicers_from_group(self, servicer_group):
        """ Return servicers from the fleet that share a servicer_group.

        Arg:
            servicer_group (str): string identifier for every group in the fleet (group types: servicer, tanker, etc.)

        Return:
            (dict(Servicer)): Dictionary of servicers of the given group
        """
        return {servicer_id: servicer for servicer_id, servicer in self.servicers.items()
                if servicer.group == servicer_group}

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
        """ Print a quick summary of which servicer is assigned to which targets. """
        # TODO: deprecate
        temp_string = ''
        for servicer_ID, servicer in self.servicers.items():
            temp_string = temp_string + servicer_ID + ' :\n'
            for tgt in servicer.assigned_targets:
                temp_string = temp_string + '\t' + tgt.ID + '\n'
        print(temp_string)

    def print_report(self):
        """ Print a quick summary of fleet information for debugging purposes."""
        print(self.ID)
        for _, servicer in self.servicers.items():
            servicer.print_report()
        for _, launcher in self.launchers.items():
            launcher.print_report()

    def __str__(self):
        temp = self.ID
        for _, servicer in self.servicers.items():
            temp = temp + '\n\t' + servicer.__str__()
        return temp


class Servicer:
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

    def __init__(self, servicer_id, group, expected_number_of_targets=3, additional_dry_mass=0. * u.kg,
                 mass_contingency=0.2):
        self.ID = servicer_id
        self.group = group
        self.expected_number_of_targets = expected_number_of_targets
        self.additional_dry_mass = additional_dry_mass
        self.current_orbit = None
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

    def add_module(self, module):
        """Adds a module to the Servicer class.

        Args:
            module (GenericModule): module to be added
        """
        if module in self.modules:
            warnings.warn('Module ', module.ID, ' already in servicer ', self.ID, '.', UserWarning)
        else:
            self.modules[module.id] = module

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
            warnings.warn('Kit ', kit.ID, ' already in servicer ', self.ID, '.', UserWarning)
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
            warnings.warn('No kit ', kit.ID, ' in servicer ', self.ID, '.', UserWarning)

    def separate_sat(self, sat):
        """ Separate a sat from the servicer. This is used during simulation.
        The sat is still assigned to the servicer and will be linked if the servicer is reset.

        Args:
            sat (Client): sat to be removed from launcher
        """
        if sat.ID in self.current_sats:
            del self.current_sats[sat.ID]
        else:
            warnings.warn('No sat ', sat.ID, ' in servicer ', self.ID, '.', UserWarning)

    def assign_sats(self, targets_assigned_to_servicer):
        """Adds sats to the Servicer as Target. The Servicer becomes the sat's mothership.

        Args:
            targets_assigned_to_servicer:
        """
        # TODO: check if can be put into scenario
        for target in targets_assigned_to_servicer:
            if target in self.current_sats:
                warnings.warn('Satellite ', target.ID, ' already in Servicer ', self.ID, '.', UserWarning)
            else:
                self.initial_sats[target.ID] = target
                self.current_sats[target.ID] = target
                target.mothership = self
            self.assigned_targets.append(target)

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
                    print('Sub-systems design ', self.ID, ' - Delta: ', delta, iteration_mass, self.get_dry_mass(),
                          self.get_wet_mass())
                if delta <= convergence_margin:
                    unconverged = False
        except RecursionError:
            warnings.warn('No convergence_margin in sub-systems design.', UserWarning)

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

    def get_initial_prop_mass(self):
        """Returns the total mass of propellant inside the servicer at launch. Does not include kits propellant.

        Return:
            (u.kg): initial propellant mass
        """
        temp_mass = 0. * u.kg
        for _, module in self.modules.items():
            if isinstance(module, PropulsionModule):
                temp_mass = temp_mass + module.get_initial_prop_mass()
        return temp_mass

    def get_wet_mass(self, contingency=True):
        """Returns the wet mass of the servicer at launch. Does not include kits.

        Args:
            contingency (boolean): if True, apply contingencies

        Return:
              (u.kg): total wet mass
        """
        return self.get_dry_mass(contingency=contingency) + self.get_initial_prop_mass()

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

    def get_hardware_recurring_cost(self):
        """Returns the recurring cost of the servicer, including all modules and current_kits.

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
        """Returns the non recurring cost of the servicer development, including all modules and the development
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
            if phase.get_assigned_servicer() == self:
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
        """Returns a reference power used as input for different models. This reference represents the mean power
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
                time.append(phase.servicer_snapshot.current_orbit.epoch)
                phase_id.append(phase.ID)
            elif hasattr(phase.servicer_snapshot, attribute_name):
                data.append(getattr(phase.servicer_snapshot, attribute_name)())
                time.append(phase.servicer_snapshot.current_orbit.epoch)
                phase_id.append(phase.ID)
            elif hasattr(phase.servicer_snapshot.current_orbit, attribute_name):
                data.append(getattr(phase.servicer_snapshot.current_orbit, attribute_name))
                time.append(phase.servicer_snapshot.current_orbit.epoch)
                phase_id.append(phase.ID)
            else:
                return False
        return data, time, phase_id

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

    def get_capture_module(self):
        """ Returns default capture module of servicer. Used to simplify scenario creation.

        Return:
            (Module): module
        """
        try:
            return self.modules[self.capture_module_ID]
        except KeyError:
            return False

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
        print(self.ID)
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

    def __str__(self):
        return (self.ID
                + "\n\t  dry mass: " + '{:.01f}'.format(self.get_dry_mass()))


class LaunchVehicle:
    """LaunchVehicle is an object that performs phases in the plan using its modules.
    A LaunchVehicle can have any number of modules of any type. A servicer can also host other servicers as in the
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

    def __init__(self, launch_vehicle_id, launcher, insertion_orbit, rideshare=True, additional_dry_mass=0. * u.kg,
                 mass_contingency=0.2):
        self.id = launch_vehicle_id
        self.launcher_name = launcher
        self.volume_available = None
        self.mass_available = None
        self.additional_dry_mass = additional_dry_mass
        self.insertion_orbit = insertion_orbit
        self.current_orbit = None
        self.modules = dict()
        self.main_propulsion_module_ID = ''
        self.rcs_propulsion_module_ID = ''
        self.capture_module_ID = ""
        self.initial_kits = dict()
        self.current_kits = dict()
        self.initial_sats = dict()
        self.current_sats = dict()
        self.assigned_upper_stage = None
        self.assigned_tanker = None
        self.assigned_targets = []
        self.mothership = None
        self.mass_contingency = mass_contingency
        self.mass_filling_ratio = 1
        self.volume_filling_ratio = 1
        self.rideshare = rideshare
        self.disp_mass = 0. * u.kg
        self.disp_volume = 0. * u.m ** 3
        self.group = "launcher"
        self.max_sats_number = 0

    def add_module(self, module):
        """Adds a module to the Servicer class.
            TODO: change description


        Args:
            module (GenericModule): module to be added
        """
        if module in self.modules:
            warnings.warn('Module ', module.id, ' already in servicer ', self.id, '.', UserWarning)
        else:
            self.modules[module.id] = module

    def assign_upper_stage(self, upper_stage):
        """ Adds another servicer to the Servicer class as assigned_upper_stage.
        TODO: get into scenario

        Args:
            upper_stage (Servicer): servicer to be added as assigned_upper_stage
        """
        self.assigned_upper_stage = upper_stage

    def separate_sat(self, sat):
        """ Separate a sat from the launcher. This is used during simulation.
        The sat is still assigned to the launcher and will be linked if the launcher is reset.

        Args:
            sat (Client): sat to be removed from launcher
        """
        if sat.ID in self.current_sats:
            del self.current_sats[sat.ID]
        else:
            logging.warning('No sat '+ sat.ID +' in launcher '+ self.id+ '.')

    def assign_sats(self, targets_assigned_to_servicer):
        """Adds sats to the LaunchVehicle as Target. The LaunchVehicle becomes the sat's mothership.

        Args:
            targets_assigned_to_servicer:
        """
        # TODO: check if can be put into scenario
        for target in targets_assigned_to_servicer:
            print(target.insertion_orbit)
            if target in self.current_sats:
                logging.warning('Satellite '+ target.ID+ ' already in LaunchVehicle '+ self.id+ '.')
            else:
                self.initial_sats[target.ID] = target
                self.current_sats[target.ID] = target
                target.mothership = self
            self.assigned_targets.append(target)

    def converge_launch_vehicle(self, satellite, serviceable_sats_left, dispenser="Auto", tech_level=1):
        """Converges the number of satellites that can be hosted within the launcher. Takes into account the
        volume and mass of the dispenser. A value can be specified for the technology level to vary the mass
        and volume of the dispenser proportionally. Technology level values greater than 1 make the dispenser heavier
        and bulkier, vice versa with values less than 1.

        Args:
            satellite (Client): Target object, represent a reference satellite inside the fairing of the launcher
            dispenser (str): dispenser to be used
            tech_level (float): technology level is 1 by default, it can be increased or decreased

        Returns:
            max_sats_number (int): maximum number of satellites hostable in the fairing
            total_sats_mass (float): total mass in kg of all satellites in the fairing
        """
        # TODO: add the possibility to manage satellites that are not all identical (i.e. all the same satellites +
        #  one or more different satellites)
        diff = 1
        i = 0

        max_sats_number_m = int((self.mass_available - self.disp_mass) / satellite.get_initial_mass())
        max_sats_number_v = int((self.volume_available - self.disp_volume) / satellite.get_volume())
        self.max_sats_number = min(max_sats_number_m, max_sats_number_v)
        if self.max_sats_number < serviceable_sats_left:
            self.sats_number = self.max_sats_number
        else:
            self.sats_number = serviceable_sats_left

        if not satellite.is_stackable:
            if dispenser == "Auto":
                # Find the maximum number of satellites that can be hosted in the fairing based on mass (m) and volume (v) constraints.
                while diff > 0.001 or self.mass_filling_ratio > 1 or self.volume_filling_ratio > 1:

                    total_sats_mass = self.sats_number * satellite.get_initial_mass()
                    disp_mass = 0.1164 * total_sats_mass / tech_level
                    disp_volume = (0.0114 * disp_mass.to(u.kg).value / tech_level) * u.m ** 3

                    new_mass_filling_ratio = (total_sats_mass + disp_mass) / self.mass_available

                    total_sats_volume = self.sats_number * satellite.get_volume()
                    new_volume_filling_ratio = (total_sats_volume + disp_volume) / self.volume_available

                    if max_sats_number_m < max_sats_number_v:
                        diff = new_mass_filling_ratio - self.mass_filling_ratio
                    else:
                        diff = new_volume_filling_ratio - self.volume_filling_ratio
                    self.mass_filling_ratio = new_mass_filling_ratio
                    self.volume_filling_ratio = new_volume_filling_ratio
                    if self.mass_filling_ratio > 1 or self.volume_filling_ratio > 1:
                        self.sats_number -= 1
                    i += 1
                    if i > 50:
                        raise TimeoutError(f"Launch vehicle {self.id} did not converge.")

                self.disp_volume = disp_volume
                self.disp_mass = disp_mass

            else:
                raise ValueError(f"Dispenser {dispenser} is not yet implemented. Please select 'Auto' instead")
        else:
            max_sats_number_m = int(self.mass_available / satellite.get_initial_mass())
            max_sats_number_v = int(self.volume_available / satellite.get_volume())
            max_sats_number = min(max_sats_number_m, max_sats_number_v)

            total_sats_mass = max_sats_number * satellite.get_initial_mass()
            total_sats_volume = max_sats_number * satellite.get_volume()

            self.mass_filling_ratio = total_sats_mass / self.mass_available
            self.volume_filling_ratio = total_sats_volume / self.volume_available

            self.max_sats_number = self.sats_number

        return self.sats_number, total_sats_mass, self.disp_mass, self.disp_volume

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
                    print('Sub-systems design ', self.id, ' - Delta: ', delta, iteration_mass, self.get_dry_mass(),
                          self.get_wet_mass())
                if delta <= convergence_margin:
                    unconverged = False
        except RecursionError:
            warnings.warn('No convergence_margin in sub-systems design.', UserWarning)

    def get_dry_mass(self, contingency=False):
        """Returns the total dry mass of the servicer. Does not include kits.

        Args:
            contingency (boolean): if True, apply contingencies

        Return:
            (u.kg): total dry mass
        """
        temp_mass = self.additional_dry_mass
        for _, module in self.modules.items():
            temp_mass = temp_mass + module.get_dry_mass(contingency=contingency)
        # for sat in self.assigned_targets:
        #     temp_mass = temp_mass + sat.get_current_mass()
        # TODO: add upper stage dry mass
        if contingency:
            temp_mass = temp_mass * (1 + self.mass_contingency)
        return temp_mass

    def get_initial_prop_mass(self):
        """Returns the total mass of propellant inside the servicer at launch. Does not include kits propellant.

        Return:
            (u.kg): initial propellant mass
        """
        temp_mass = 0. * u.kg
        for _, module in self.modules.items():
            if isinstance(module, PropulsionModule):
                temp_mass = temp_mass + module.get_initial_prop_mass()
        return temp_mass

    def get_wet_mass(self, contingency=False):
        """Returns the wet mass of the servicer at launch. Does not include kits.

        Args:
            contingency (boolean): if True, apply contingencies

        Return:
              (u.kg): total wet mass
        """
        return self.get_dry_mass(contingency=contingency) + self.get_initial_prop_mass()

    def get_current_mass(self):
        """Returns the total mass of the launcher, including all modules and kits at the current time in the simulation.

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

    def get_hardware_recurring_cost(self):
        """Returns the recurring cost of the servicer, including all modules and current_kits.

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
        """Returns the non recurring cost of the servicer development, including all modules and the development
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
            if phase.get_assigned_servicer() == self:
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
        """Returns a reference power used as input for different models. This reference represents the mean power
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
                time.append(phase.servicer_snapshot.current_orbit.epoch)
                phase_id.append(phase.ID)
            elif hasattr(phase.servicer_snapshot, attribute_name):
                data.append(getattr(phase.servicer_snapshot, attribute_name)())
                time.append(phase.servicer_snapshot.current_orbit.epoch)
                phase_id.append(phase.ID)
            elif hasattr(phase.servicer_snapshot.current_orbit, attribute_name):
                data.append(getattr(phase.servicer_snapshot.current_orbit, attribute_name))
                time.append(phase.servicer_snapshot.current_orbit.epoch)
                phase_id.append(phase.ID)
            else:
                return False
        return data, time, phase_id

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

        # reset sats to be deployed
        logging.log(21, f"Resetting sats: current_sats={self.current_sats}, initial_sats={self.initial_sats}...")
        for _, sat in self.initial_sats.items():
            self.current_sats[sat.ID] = sat
        logging.log(21, f"Reset: current_sats={self.current_sats}, initial_sats={self.initial_sats}")

        # reset modules
        for _, module in self.modules.items():
            module.reset()
        if design_loop:
            self.design(plan, convergence_margin=convergence_margin, verbose=verbose)

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

    def print_report(self):
        """ Print quick summary for debugging purposes."""
        print(f"""_____________________________________
\033[1mLaunch Vehicles: \033[0m
    Internal ID: {self.id}
    Launch vehicle name: {self.launcher_name}
    Dry mass: {self.get_dry_mass():.01f}
    Wet mass: {self.get_wet_mass():.01f}
    Payload mass available: {self.mass_available}
    Number of sats in the fairing: {self.sats_number}
    Dispenser mass: {self.disp_mass:.1f}
    Mass filling ratio: {self.mass_filling_ratio * 100:.1f}%
    Dispenser volume: {self.disp_volume:.1f}
    Volume filling ratio: {self.volume_filling_ratio * 100:.1f}%
    Targets assigned to the Launch Vehicle:""")
        for x in range(len(self.assigned_targets)):
            print(f"\t\t{self.assigned_targets[x]}")

        print("-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-")

        print('\033[1mModules: \033[0m')
        for _, module in self.modules.items():
            print(f"Module ID: {module}")
        print('Phasing Module ID: ' + self.main_propulsion_module_ID)
        print('RDV module ID: ' + self.rcs_propulsion_module_ID)
        print('Capture module ID : ' + self.capture_module_ID)

    def __str__(self):
        return (self.id
                + "\n\t  Dry mass: " + '{:.01f}'.format(self.get_dry_mass()))