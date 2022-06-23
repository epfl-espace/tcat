from Spacecrafts.Spacecraft import Spacecraft
import logging
import warnings
from Modules.PropulsionModule import PropulsionModule
from Phases.Approach import Approach
from Phases.OrbitChange import OrbitChange
from Scenario.Plan_module import Plan
from astropy import units as u

class ActiveSpacecraft(Spacecraft):
    """
    General Attributs
    """

    """
    Init
    """
    def __init__(self,id,group,dry_mass,mass_contingency,starting_epoch):
        super().__init__(id,dry_mass)
        # Set id parameters
        self.group = group

        # Instanciate modules
        self.modules = dict()
        self.main_propulsion_module = None
        self.rcs_propulsion_module = None
        self.capture_module = None

        # Satellite related
        self.initial_sats = dict()
        self.current_sats = dict()
        self.assigned_tanker = None
        self.assigned_targets = []

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
        """  Adds module to the list

        Args:
            module (GenericModule): module to be added
        """
        if module in self.modules:
            warnings.warn('Module ', module.id, ' already in servicer ', self.id, '.', UserWarning)
        else:
            self.modules[module.id] = module

    def assign_sats(self, targets_assigned_to_servicer):
        """ Adds satellites to the Servicer as Target. The Servicer becomes the sat's mothership.

        Args:
            targets_assigned_to_servicer:
        """
        # TODO: check if can be put into scenario
        for target in targets_assigned_to_servicer:
            if target in self.current_sats:
                warnings.warn('Satellite ', target.get_id(), ' already in Servicer ', self.id, '.', UserWarning)
            else:
                self.initial_sats[target.get_id()] = target
                self.current_sats[target.get_id()] = target
                target.mothership = self
            self.assigned_targets.append(target)

    def separate_sat(self, satellite):
        """ Separate a sat from the launcher. This is used during simulation.
            The sat is still assigned to the launcher and will be linked if the launcher is reset.

        Args:
            sat (Client): sat to be removed from launcher
        """
        if satellite.get_id() in self.current_sats:
            del self.current_sats[satellite.get_id()]
        else:
            logging.warning('No sat '+ satellite.get_id() +' in '+ self.id+ '.')

    def change_orbit(self, orbit):
        """ Changes the current_orbit of the servicer and linked objects.

        Args:
            orbit (poliastro.twobody.Orbit): orbit where the servicer will be after update
        """
        # Update upperstage own orbit
        self.previous_orbit = self.current_orbit
        self.current_orbit = orbit

        # Update capture module orbit
        capture_module = self.get_capture_module()
        if capture_module.captured_object:
            capture_module.captured_object.current_orbit = orbit

    def set_capture_module(self,module):
        """ Returns default capture module of servicer. Used to simplify scenario creation.

        Args:
            (Module): module
        """
        # Assign capture_module
        self.capture_module = module

        # Add the module to the list
        self.add_module(module)

    def set_main_propulsion_module(self,module):
        """ Returns default main propulsion module of servicer. Used to simplify scenario creation.

        Args:
            (Module): module
        """
        # Assign main_propulsion_module
        self.main_propulsion_module = module

        # Add the module to the list
        self.add_module(module)

    def set_rcs_propulsion_module(self,module):
        """ Returns default rcs propulsion module of servicer. Used to simplify scenario creation.

        Args:
            (Module): module
        """
        # Assign rcs_propulsion_module
        self.rcs_propulsion_module = module

        # Add the module to the list
        self.add_module(module)

    def get_capture_module(self):
        """ Returns default capture module of servicer. Used to simplify scenario creation.

        Return:
            (Module): module
        """
        try:
            return self.capture_module
        except KeyError:
            return False

    def get_main_propulsion_module(self):
        """ Returns default main propulsion module of servicer. Used to simplify scenario creation.

        Return:
            (Module): module
        """
        try:
            return self.main_propulsion_module
        except KeyError:
            return None

    def get_rcs_propulsion_module(self):
        """ Returns default rcs propulsion module of servicer. Used to simplify scenario creation.

        Return:
            (Module): module
        """
        try:
            return self.rcs_propulsion_module
        except KeyError:
            return None

    def get_dry_mass(self, contingency=True):
        """Returns the total dry mass of the servicer. Does not include kits.

        Args:
            contingency (boolean): if True, apply contingencies

        Return:
            (u.kg): total dry mass
        """
        temp_mass = super().dry_mass()
        for _, module in self.modules.items():
            temp_mass = temp_mass + module.get_dry_mass(contingency=contingency)
        if contingency:
            temp_mass = temp_mass * (1 + self.mass_contingency)
        return temp_mass

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

        # Return computed non_recurring_cost
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

    def print_report(self):
        print(f"Built-in function print report not defined for Class: {type(self)}")

    def __str__(self):
        return (super().__str__()
                + "\n\t  dry mass: " + '{:.01f}'.format(self.get_dry_mass())) 