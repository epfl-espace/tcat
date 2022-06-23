import warnings
from Modules.CaptureModule import CaptureModule
from Modules.PropulsionModule import PropulsionModule
from Spacecrafts.ActiveSpacecraft import ActiveSpacecraft
from astropy import units as u

class Servicer(ActiveSpacecraft):
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

    def get_capture_modules(self):
        """ Returns only modules that can capture targets of simulation at current time.

        Return:
            (dict(Module)): dictionary of the modules
        """
        capture_modules = {ID: module for ID, module in self.modules.items() if isinstance(module, CaptureModule)}
        return capture_modules

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
