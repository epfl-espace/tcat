"""
Created:        23.06.2022
Last Revision:  23.06.2022
Author:         Malo Goury
Description:    Parent class for all active spacecrafts
"""
# Import class
from numpy import isin
from Spacecrafts.Spacecraft import Spacecraft
from Plan.Plan import Plan
from Modules.PropulsionModule import PropulsionModule
from Phases.Approach import Approach
from Phases.OrbitChange import OrbitChange

# Import libraries
import logging
import warnings
from astropy import units as u

# Import methods

class ActiveSpacecraft(Spacecraft):
    """ ActiveSpacecraft acts ase a child Class implementing all necessary attributes relative to active spacercraft such as upperstages and servicers.

    :param activespacecraft_id: ActiveSpacecraft identification name
    :type activespacecraft_id: str
    :param group: Group name
    :type group: str
    :param dry_mass: ActiveSpacecraft dry mass
    :type dry_mass: u*kg
    :param mass_contingency: ActiveSpacecraft mass contingency
    :type mass_contingency: float
    :param scenario: Scenario
    :type scenario: :class:`~Scenarios.Scenario.Scenario`
    :param insertion_orbit: Insertion orbit
    :type insertion_orbit: poliastro.twobody.Orbit
    :param initial_orbit: Initial orbit
    :type initial_orbit: poliastro.twobody.Orbit
    :param operational_orbit: Operational orbit
    :type operational_orbit: poliastro.twobody.Orbit
    :param disposal_orbit: Disposal orbit
    :type disposal_orbit: poliastro.twobody.Orbit
    """
    def __init__(self,activespacecraft_id,group,dry_mass,mass_contingency,scenario,insertion_orbit = None,initial_orbit = None,operational_orbit = None,disposal_orbit = None):
        super().__init__(activespacecraft_id,dry_mass,insertion_orbit = insertion_orbit,operational_orbit = operational_orbit, disposal_orbit=disposal_orbit)
        # Set id parameters
        self.group = group

        # Instanciate modules
        self.modules = dict()
        self.main_propulsion_module = None
        self.capture_module = None
        
        # Keep a satellite as reference
        self.constellation_reference_spacecraft = scenario.reference_satellite

        # Spacecraft dict and ordered list
        self.initial_spacecraft = dict()
        self.current_spacecraft = dict()
        self.ordered_target_spacecraft = []

        self.mass_contingency = mass_contingency

        # Disposal orbit triggered at end of mission
        self.initial_orbit = initial_orbit

        # Instanciate Plan
        self.plan = Plan(f"Plan_{self.id}",scenario.starting_epoch)

    """
    Methods
    """
    def empty_plan(self):
        """ Empty own plan before restart
        """
        self.plan.empty()

    def add_module(self, module):
        """ Add a module to its list

        :param module: new module
        :type module: :class:`~Modules.GenericModule.GenericModule`
        """
        if module in self.modules:
            warnings.warn('Module ', module.id, ' already in servicer ', self.id, '.', UserWarning)
        else:
            self.modules[module.id] = module

    def assign_spacecraft(self, spacecraft_to_assign):
        """ Assign a list of spacecrafts as targets

        :param spacecraft_to_assign: list of spacecrafts or child class instances
        :type spacecraft_to_assign: list(:class:`~Spacecrafts.Spacecraft.Spacecraft`)
        """
        if not isinstance(spacecraft_to_assign,list):
            spacecraft_to_assign = [spacecraft_to_assign]

        for target in spacecraft_to_assign:
            if target in self.current_spacecraft:
                warnings.warn('Satellite ', target.get_id(), ' already in Servicer ', self.id, '.', UserWarning)
            else:
                self.initial_spacecraft[target.get_id()] = target
                self.current_spacecraft[target.get_id()] = target
                target.mothership = self
            self.ordered_target_spacecraft.append(target)
        
        self.capture_module.add_captured_spacecrafts(spacecraft_to_assign)

    def separate_spacecraft(self, satellite):
        """ Remove a satellite from current spacecraft list when released

        :param satellite: spacecraft to be removed
        :type satellite: :class:`~Spacecrafts.Spacecraft.Spacecraft`
        """
        if satellite.get_id() in self.current_spacecraft:
            del self.current_spacecraft[satellite.get_id()]
        else:
            logging.warning('No sat '+ satellite.get_id() +' in '+ self.id+ '.')
    
    def add_spacecraft(self, satellite):
        """ Add a satellite to current spacecraft list when captured or taken as payload

        :param satellite: spacecraft to be removed
        :type satellite: :class:`~Spacecrafts.Spacecraft.Spacecraft`
        """
        if satellite.get_id() in self.current_spacecraft:
            logging.warning('Sat '+ satellite.get_id() +' already in '+ self.id+ '.')
        else:
            self.current_spacecraft[satellite.get_id()] = satellite

    def execute_plan(self):
        """ Apply own plan
        """
        # Apply plan
        self.plan.apply()

    def reset(self):
        """ Reset the Activespacecraft to initial parameters. Ready for a restart
        """
        # Reset Spacecraft
        super().reset()
        self.current_orbit = self.get_initial_orbit()

        # Empty the plan
        self.empty_plan()

        # Empty spacecrafts
        self.ordered_target_spacecraft = []

    def change_orbit(self, orbit):
        """ Change current orbit to supplied orbit

        :param orbit: new current orbit
        :type orbit: poliastro.twobody.Orbit
        """
        # Spacecraft orbit
        super().change_orbit(orbit)

        # Update all spacecraft within capture module
        capture_module = self.get_capture_module()

        for key in capture_module.get_captured_spacecrafts().keys():
            capture_module.get_captured_spacecrafts()[key].change_orbit(orbit)

    def set_capture_module(self,module):
        """ Set the capture module

        :param module: capture module
        :type module: :class:`~Modules.CaptureModule.CaptureModule`
        """
        # Assign capture_module
        self.capture_module = module

        # Add the module to the list
        self.add_module(module)

    def set_main_propulsion_module(self,module):
        """ Set the main propulsion module

        :param module: propulsion module
        :type module: :class:`~Modules.PropulsionModule.PropulsionModule`
        """
        # Assign main_propulsion_module
        self.main_propulsion_module = module

        # Add the module to the list
        self.add_module(module)

    def get_ordered_target_spacecraft(self):
        """ Get the list of ordered spacecraft target

        :return: ordered targets
        :rtype: list(:class:`~Spacecrafts.Spacecraft.Spacecraft`)
        """
        return self.ordered_target_spacecraft

    def get_capture_module(self):
        """ Get the capture module

        :return: capture module
        :rtype: :class:`~Modules.CaptureModule.CaptureModule`
        """
        try:
            return self.capture_module
        except KeyError:
            return False

    def get_main_propulsion_module(self):
        """ Get the main propulsion module

        :return: capture module
        :rtype: :class:`~Modules.PropulsionModule.PropulsionModule`
        """
        try:
            return self.main_propulsion_module
        except KeyError:
            return None

    def get_current_mass(self):
        """ Get the current mass.

        :return: current mass
        :rtype: (u.kg)
        """
        # Instanciate current mass
        current_mass = 0

        # Instanciate current mass
        current_mass += super().get_current_mass()

        # Add propulsion current mass
        current_mass += self.main_propulsion_module.get_current_mass()

        # Add capture module mass (including linked satellite)
        current_mass += self.capture_module.get_current_mass()

        # Return current mass
        return current_mass

    def get_initial_orbit(self):
        """ Get the initial orbit

        :return: initial orbit
        :rtype orbit: poliastro.twobody.Orbit
        """
        return self.initial_orbit

    def get_initial_prop_mass(self):
        """ Get the initial propulsion mass.

        :return: initial propulsion mass
        :rtype: (u.kg)
        """
        return self.main_propulsion_module.get_initial_prop_mass()

    def get_wet_mass(self):
        """ Get the wet mass.

        :return: wet mass
        :rtype: (u.kg)
        """
        return self.get_dry_mass() + self.get_initial_prop_mass()

    def get_hardware_recurring_cost(self):
        """ Get hardware recurring cost.

        :return: recurring cost
        :rtype: float
        """
        recurring_cost = 0.
        # modules cost
        for _, module in self.modules.items():
            recurring_cost = recurring_cost + module.get_recurring_cost()
        return recurring_cost

    def get_development_cost(self):
        """ Get developpement recurring cost.

        :return: development cost
        :rtype: float
        """
        non_recurring_cost = 0.
        # modules non recurring cost
        for _, module in self.modules.items():
            non_recurring_cost = non_recurring_cost + module.get_non_recurring_cost()

        # Return computed non_recurring_cost
        return non_recurring_cost

    def get_phases(self, plan):
        """ Get all phases assigned to this ActiveSpacecraft

        :param plan: propulsion module
        :type plan: :class:`~Plan.Plan.Plan`
        :return: phases
        :rtype: list(:class:`~Phases.GenericPhase.GenericPhase`)
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

        :param plan: propulsion module
        :type plan: :class:`~Plan.Plan.Plan`
        :param module: module
        :type module: :class:`~Modules.GenericModule.GenericModule`
        :return: reference detla v
        :rtype: u.m / u.s
        :return: rcs prop mass
        :rtype: u.kg
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
        """ Get the reference power

        :return: nominal_power_draw
        :rtype: u.W
        """
        nominal_power_draw = 0. * u.W
        for _, module in self.modules.items():
            nominal_power_draw = nominal_power_draw + module.get_reference_power()
        return nominal_power_draw

    def print_report(self):
        """ Print the report
        """
        print(f"Built-in function print report not defined for Class: {type(self)}")