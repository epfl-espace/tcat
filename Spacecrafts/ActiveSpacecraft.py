"""
Created:        23.06.2022
Last Revision:  23.06.2022
Author:         Malo Goury
Description:    Parent class for all active spacecrafts
"""
# Import class
from numpy import isin
from Phases.Common_functions import orbit_string, update_orbit
from Spacecrafts.Spacecraft import Spacecraft
from Plan.Plan import Plan
from Phases.Approach import Approach
from Phases.OrbitChange import OrbitChange
from Scenarios.ScenarioParameters import *

# Import libraries
import logging
import warnings
from astropy import units as u

# Import methods

class ActiveSpacecraft(Spacecraft):
    """ ActiveSpacecraft acts ase a child Class implementing all necessary attributes relative to active spacercraft such as kickstages and servicers.

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
    :param operational_orbit: Operational orbit
    :type operational_orbit: poliastro.twobody.Orbit
    :param disposal_orbit: Disposal orbit
    :type disposal_orbit: poliastro.twobody.Orbit
    """
    def __init__(self,activespacecraft_id,group,structure_mass,mass_contingency,scenario,volume=0.*u.m**3,insertion_orbit = None,operational_orbit = None,disposal_orbit = None):
        super().__init__(activespacecraft_id,structure_mass,volume=volume,insertion_orbit = insertion_orbit,operational_orbit = operational_orbit, disposal_orbit=disposal_orbit)
        # Set id parameters
        self.group = group

        # Instanciate modules
        self.main_propulsion_module = None
        self.capture_module = None
        
        # Keep a satellite as reference
        self.constellation_reference_spacecraft = scenario.reference_satellite

        # Spacecraft dict and ordered list
        self.initial_spacecraft = dict()
        self.current_spacecraft = dict()
        self.ordered_target_spacecraft = []

        self.mass_contingency = mass_contingency

        # Init ratio of inclination change in raan drift model
        self.ratio_inc_raan_from_scenario = scenario.tradeoff_mission_price_vs_duration
        self.ratio_inc_raan_from_opti = 0.

        # Instanciate Plan
        self.plan = Plan(f"Plan_{self.id}",scenario.starting_epoch)

    """
    Methods
    """
    def empty_plan(self):
        """ Empty own plan before restart
        """
        self.plan.empty()

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

    def compute_delta_inclination_for_raan_phasing(self):
        """ Computes the inclination change for RAAN phasing based on two ratios: 
            1) self.ratio_inc_raan_from_scenario: lets the senario define how much dV should be used to accelrate phasing
            2) self.ratio_inc_raan_from_opti: used by optimisation loop minimising phasing duration with the available fuel

        :return: phasing inclination
        :rtype: u.deg
        """
        total_ratio = self.ratio_inc_raan_from_scenario + self.ratio_inc_raan_from_opti
        range = MODEL_RAAN_DELTA_INCLINATION_HIGH - MODEL_RAAN_DELTA_INCLINATION_LOW
        return total_ratio*range + MODEL_RAAN_DELTA_INCLINATION_LOW

    def reset(self):
        """ Reset the Activespacecraft to initial parameters. Ready for a restart
        """
        # Reset Spacecraft
        super().reset()

        # Empty the plan
        self.empty_plan()

    def design(self):
        """ Resets all modules
        """
        self.reset_modules()

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

    def get_starting_epoch(self):
        return self.plan.get_starting_epoch()

    def get_ending_epoch(self):
        return self.plan.get_ending_epoch()

    def get_ordered_target_spacecraft(self):
        """ Get the list of ordered spacecraft target

        :return: ordered targets
        :rtype: list(:class:`~Spacecrafts.Spacecraft.Spacecraft`)
        """
        return self.ordered_target_spacecraft

    def get_nb_target_spacecraft(self):
        """ Get the number of spacecraft assigned to this servicer

        :return: number of spacecraft assigned to this servicer
        :rtype: int
        """
        return len(self.get_ordered_target_spacecraft())

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

    def get_initial_prop_mass(self):
        """ Get the initial propulsion mass.

        :return: initial propulsion mass
        :rtype: (u.kg)
        """
        return self.main_propulsion_module.get_initial_prop_mass()

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

    def generate_snapshot_string(self,spacecraft_type_str="Spacecraft"):
        return (str("")
        + "\n\tStarting Epoch: " + str(self.previous_orbit.epoch)
        + "\n\tEnding Epoch: " + str(self.current_orbit.epoch)
        + "\n\t" + spacecraft_type_str + ": " + str(self.get_id())
        + "\n\tInitial Orbit: " + orbit_string(self.previous_orbit)
        + "\n\tFinal Orbit: " + orbit_string(self.current_orbit)
        + "\n\tReference Satellite Orbit: " + orbit_string(update_orbit(self.constellation_reference_spacecraft.get_default_orbit(),self.current_orbit.epoch))
        + "\n\t" + spacecraft_type_str + " Mass After Phase: {0:.1f}".format(self.get_current_mass())
        + "\n\tFuel Mass After Phase: " + "{0:.1f}".format(self.get_main_propulsion_module().current_propellant_mass))

    def print_spacecraft_specific_data(self):
        pass

    def get_reference_power(self):
        """ Get the reference power

        :return: nominal_power_draw
        :rtype: u.W
        """
        nominal_power_draw = 0. * u.W
        for _, module in self.modules.items():
            nominal_power_draw = nominal_power_draw + module.get_reference_power()
        return nominal_power_draw

    def print_metadata(self):
        print(f""
        + f"Metadata:"
        + f"\n\tSpacecraft id: {self.get_id()}"
        + f"\n\tDry mass: {self.get_dry_mass():.01f}"
        # + self.get_modules_dry_mass_str()
        + f"\n\tInitial wet mass: {self.get_initial_wet_mass():.01f}"
        # + self.get_modules_initial_wet_mass_str()
        + f"\n\tFuel mass margin: {self.get_main_propulsion_module().current_propellant_mass:.1f}"
        + f"\n\tNb of phases: {self.plan.get_nb_phases()}"
        + f"\n\tNb of manoeuveres: {self.plan.get_nb_manoeuvers()}")
        self.print_spacecraft_specific_data()
        print(f"\tAssigned Spacecrafts:")

    def print_report(self):
        """ Print the report
        """
        print("")
        print(self.get_id())
        print("="*72)
        self.print_metadata()

        for target in self.ordered_target_spacecraft:
            print(f"\t\t{target}")

        print(f"-"*72)
        print('Modules:')
        for _, module in self.modules.items():
            print(f"\tModule ID: {module}")

        print(f"-"*72)
        self.plan.print_report()