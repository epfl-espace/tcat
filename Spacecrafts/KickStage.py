import copy
import logging
import math

import numpy as np
from Modules.CaptureModule import CaptureModule
from Modules.PropulsionModule import PropulsionModule
from Phases.Insertion import Insertion
from Phases.OrbitChange import OrbitChange
from Phases.Release import Release
from SpacecraftDatabase.LauncherDatabaseReader import get_launcher_fairing_dimensions, get_launcher_performance
from Scenarios.ScenarioParameters import *
from Spacecrafts.ActiveSpacecraft import ActiveSpacecraft
from astropy import units as u
from poliastro.bodies import Earth
from poliastro.twobody import Orbit


class KickStage(ActiveSpacecraft):
    """ KickStage acts ase a child Class implementing all necessary attributes relative kickstages.

    :param kickstage_id: KickStage identification name
    :type kickstage_id: str
    :param scenario: Scenario
    :type scenario: :class:`~Scenarios.Scenario.Scenario`
    :param additional_dry_mass: Additionnal dry mass
    :type additional_dry_mass: u*kg
    :param mass_contingency: Mass contingency
    :type mass_contingency: float
    """
    def __init__(self,kickstage_id,scenario,structure_mass=0. * u.kg,mass_contingency=0.2):
        # Init ActiveSpacecraft
        super().__init__(kickstage_id,"kickstage",structure_mass,mass_contingency,scenario,disposal_orbit = scenario.kickstage_disposal_orbit,insertion_orbit = scenario.launcher_insertion_orbit)

        # Launcher name
        self.launcher_name = scenario.launcher_name

        # Set mass, volumes and filling ratio
        self.volume_available = None
        self.mass_available = None
        self.mass_filling_ratio = 1
        self.volume_filling_ratio = 1
        self.dispenser_mass = 0. * u.kg
        self.dispenser_volume = 0. * u.m ** 3
        self.satellites_allowance = 0
        self.fuel_margin = scenario.kickstage_remaining_fuel_margin
        self.ordered_target_spacecraft = []

        # Add dispenser as CaptureModule
        dispenser = CaptureModule(self.id + '_Dispenser',
                                self,
                                mass_contingency=0.0,
                                dry_mass_override=scenario.kickstage_dispenser_dry_mass)

        self.set_capture_module(dispenser)

        # Add propulsion as PropulsionModule
        mainpropulsion = PropulsionModule(self.id + '_MainPropulsion',
                                          self, scenario.kickstage_propulsion_type, 
                                          scenario.kickstage_prop_thrust,
                                          scenario.kickstage_prop_thrust, 
                                          scenario.kickstage_prop_isp, 
                                          scenario.kickstage_initial_fuel_mass,
                                          KICKSTAGE_MAXTANK_CAPACITY, 
                                          reference_power_override=0 * u.W,
                                          propellant_contingency=KICKSTAGE_FUEL_CONTINGENCY, 
                                          dry_mass_override=scenario.kickstage_propulsion_dry_mass,
                                          mass_contingency=KICKSTAGE_PROP_MODULE_MASS_CONTINGENCY)
        self.set_main_propulsion_module(mainpropulsion)

        # Compute initial performances
        self.compute_kickstage(scenario)

    def execute_with_fuel_usage_optimisation(self,satellites,constellation_precession=0):
        """ Iteratively reduce total mission time by using all propellant mass

        :param satellites: Spacecraft assigned to the kickstage
        :type satellites: list(:class:`~Spacecrafts.Spacecraft.Spacecraft`)
        :param constellation_precession: Reference satellite precession speed
        :type constellation_precession: float
        :return: convergence flag
        :rtype: bool
        """
        # check default cases
        if self.main_propulsion_module.get_current_prop_mass() < 0.:
            logging.info(f"Remaining fuel is negative, remove a satellite")
            return False

        # initialise algorithm's variables
        remaining_fuel_prev = 0.
        self.ratio_inc_raan_from_opti = 0. # % of MODEL_RAAN_DELTA_INCLINATION_HIGH

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
            remaining_fuel_prev = self.main_propulsion_module.get_current_prop_mass()
            nb_iter += 1

            # compute remaining fuel for new inclination change
            self.ratio_inc_raan_from_opti = (delta_inc_up+delta_inc_low)/2
            self.execute(satellites,constellation_precession=constellation_precession)

            # define new inclination's range
            if self.main_propulsion_module.get_current_prop_mass()-self.fuel_margin >= 0:
                delta_inc_low = self.ratio_inc_raan_from_opti
            else:
                delta_inc_up = self.ratio_inc_raan_from_opti

            # detect algorithm's convergence
            if MODEL_RAAN_DELTA_INCLINATION_HIGH*(delta_inc_up-delta_inc_low) <= 2*MODEL_RAAN_DELTA_INCLINATION_LOW \
            or abs(self.main_propulsion_module.get_current_prop_mass()-remaining_fuel_prev) <= KICKSTAGE_REMAINING_FUEL_TOLERANCE:
                converged = True

        # ensure remaining fuel is positive
        if self.main_propulsion_module.get_current_prop_mass()-self.fuel_margin < 0.:
            self.ratio_inc_raan_from_opti = delta_inc_low
            self.execute(satellites,constellation_precession=constellation_precession)

        return converged

    def execute(self,assigned_satellites,constellation_precession=0):
        """ Reset, design and compute plan based on a list of assigned satellites

        :param assigned_satellites: Spacecraft assigned to the kickstage
        :type assigned_satellites: list(:class:`~Spacecrafts.Spacecraft.Spacecraft`)
        :param constellation_precession: Reference satellite precession speed
        :type constellation_precession: float
        """
        # Perform initial setup (mass and volume available)
        self.reset()

        # Assign target as per mass and volume allowance
        self.assign_spacecraft(assigned_satellites)

        # Compute launcher design for custom satellite allowance
        self.design(assigned_satellites)

        # Define spacecraft mission profile
        self.define_mission_profile(constellation_precession)

        # Execute kickstage (Apply owned plan)
        self.execute_plan()


    def reset(self):
        """ Reset the object to inital parameters. Empty the plan
        """
        # Reset ActiveSpacecraft
        super().reset()
        self.initial_spacecraft = dict()
        self.current_spacecraft = dict()
        self.reset_modules()

        # Reset attribut
        self.ordered_target_spacecraft = []
        self.mass_filling_ratio = 1
        self.volume_filling_ratio = 1
        self.dispenser_mass = 0. * u.kg
        self.dispenser_volume = 0. * u.m ** 3
    
    def design(self,assigned_satellites,tech_level=1):
        """ Design the kickstage based on allowance, tech_level and current performances

        :param assigned_satellites: Spacecraft assigned to the kickstage
        :type assigned_satellites: list(:class:`~Spacecrafts.Spacecraft.Spacecraft`)
        :param tech_level: Dispenser tech level (0-1)
        :type tech_level: float
        """
        # Compute filling ratio and disp mass and volume
        self.mass_filling_ratio = self.get_initial_payload_mass() / self.mass_available
        self.volume_filling_ratio = sum([satellite.get_current_volume() for satellite in assigned_satellites]) / self.volume_available

    def assign_spacecraft(self, spacecraft_to_assign):
        """ Assign a list of spacecrafts as targets

        :param spacecraft_to_assign: list of spacecrafts or child class instances
        :type spacecraft_to_assign: list(:class:`~Spacecrafts.Spacecraft.Spacecraft`)
        """
        super().assign_spacecraft(spacecraft_to_assign)
        self.capture_module.add_captured_spacecrafts(spacecraft_to_assign)

    def remove_last_spacecraft(self, spacecraft_to_remove):
        super().remove_last_spacecraft(spacecraft_to_remove)
        self.capture_module.release_single_spacecraft(spacecraft_to_remove)

    def compute_kickstage(self,scenario):
        """ Compute kickstage available mass and volume based on launcher type

        :param scenario: Scenario
        :type scenario: :class:`~Scenarios.Scenario.Scenario`
        """
        # Interpolate launcher performance + correction
        self.compute_mass_available(scenario)

        # Interpolate launcher fairing capacity + correction
        self.compute_volume_available(scenario)

    def compute_mass_available(self,scenario):
        """ Compute kickstage available mass based on launcher type

        :param scenario: Scenario
        :type scenario: :class:`~Scenarios.Scenario.Scenario`
        """
        # Check for custom launcher_name values
        if scenario.launcher_use_database is True:
            logging.info(f"Gathering Launch Vehicle performance from database...")
            # Compute launcher capabilities to deliver into orbit
            launcher_performance = get_launcher_performance(scenario.fleet,
                                                            scenario.launcher_name,
                                                            scenario.launcher_launch_site,
                                                            self.insertion_orbit.inc.value,
                                                            scenario.apogee_launcher_insertion.value,
                                                            scenario.perigee_launcher_insertion.value,
                                                            scenario.launcher_orbit_type,
                                                            method=scenario.launcher_perf_interpolation_method,
                                                            verbose=scenario.verbose,
                                                            save="InterpolationGraph",
                                                            save_folder=scenario.dir_path_for_output_files)

            if scenario.launcher_name in ["Soyuz_2.1a_Fregat", "Soyuz_2.1b_Fregat"] and scenario.kickstage_use_database and scenario.kickstage_name in ["Fregat", "Fregat_M"]:
                self.mass_available = launcher_performance
            elif super().get_initial_wet_mass() > launcher_performance:
                raise ValueError(f"The kickstage is heavier than the launcher performance.")
            else:
                self.mass_available = launcher_performance - super().get_initial_wet_mass()
        else:
            logging.info(f"Using custom Launch Vehicle performance...")
            self.mass_available = scenario.launcher_performance - super().get_initial_wet_mass()
        pass

    def compute_volume_available(self,scenario):
        """ Compute kickstage available volume based on launcher type

        :param scenario: Scenario
        :type scenario: :class:`~Scenarios.Scenario.Scenario`
        """
        fairing_diameter = 0 * u.m
        fairing_cylinder_height = 0 *u.m
        fairing_total_height = 0*u.m

        # Check for custom launcher_name values
        if scenario.launcher_use_database is True:
            fairing_diameter,fairing_cylinder_height,fairing_total_height = get_launcher_fairing_dimensions(self.launcher_name) 
        else:
            fairing_diameter = scenario.launcher_fairing_diameter
            fairing_cylinder_height = scenario.launcher_fairing_cylinder_height
            fairing_total_height = scenario.launcher_fairing_total_height

        if scenario.kickstage_height >= fairing_cylinder_height:
            self.volume_available = 0 *u.m**3
            print("Kickstage is taller than launcher's fairing")
            
        else:
            cylinder_volume = np.pi * (fairing_diameter/ 2) ** 2 * (fairing_cylinder_height - scenario.kickstage_height)
            cone_volume = np.pi * (fairing_diameter/ 2) ** 2 * (fairing_total_height - fairing_cylinder_height) / 3
            self.volume_available = cylinder_volume + cone_volume
    
    def compute_allowance(self,unassigned_satellites):
        """ Returns maximum number of satellites that can be onboard the kick stage, either due to limitation of mass, of volume or the number of servicers still to carry

        :param unassigned_satellites: Spacecraft unassigned to an kickstage
        :type unassigned_satellites: list(:class:`~Spacecrafts.Spacecraft.Spacecraft`)
        :return: satellites allowance
        :rtype: int
        """
        # Compute limit in mass terms
        limit_mass = math.floor(self.mass_available/self.constellation_reference_spacecraft.get_initial_wet_mass())

        # Compute limit in volume terms
        limit_volume = math.floor(self.volume_available/self.constellation_reference_spacecraft.get_current_volume())

        # Minimal value is of interest
        self.satellites_allowance =  min([limit_volume,limit_mass,len(unassigned_satellites)])

        # Return allowance
        return self.satellites_allowance

    def compute_allowance_ADR(self,unassigned_satellites, servicer_mass, servicer_volume):
        """ Returns maximum number of ADR servicers that can be onboard the kick stage, either due to limitation of mass, of volume or the number of servicers still to carry

        :param unassigned_satellites: Spacecraft unassigned to an kickstage
        :type unassigned_satellites: list(:class:`~Spacecrafts.Spacecraft.Spacecraft`)
        :return: satellites allowance
        :rtype: int
        """
        # Compute limit in mass terms
        limit_mass = math.floor(self.mass_available/servicer_mass)

        # Compute limit in volume terms
        limit_volume = math.floor(self.volume_available/servicer_volume)

        # Minimal value is of interest
        self.satellites_allowance =  min([limit_volume,limit_mass,len(unassigned_satellites)])

        # Return allowance
        return self.satellites_allowance

    def get_satellites_allowance(self):
        """ Return maximum allowable of the kickstage

        :return: satellites allowance
        :rtype: int
        """
        return self.satellites_allowance

    def define_mission_profile(self,precession_direction):
        """ Compute mission profile based on a basic canvas

        :param precession_direction: satellite precession direction
        :type precession_direction: u.deg /u.s
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
        if len(self.ordered_target_spacecraft) == 0:
            raise ValueError(f"No satellite can be added as payload because kickstage takes too much of the performance.")
        else:
            first_target = self.ordered_target_spacecraft[0]

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
        raising = OrbitChange(f"({self.get_id()}) goes to first target orbit ({first_target.get_id()})",
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
        for i, current_target in enumerate(self.ordered_target_spacecraft):
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
                raising = OrbitChange(f"({self.id}) goes to next target ({current_target.get_id()})",
                                      self.plan,
                                      current_target.insertion_orbit,
                                      raan_specified=True,
                                      initial_orbit=phasing_orbit,
                                      delta_v_contingency=delta_v_contingency,
                                      raan_cutoff=raan_cutoff)

                # Assign propulsion module to OrbitChange phase
                raising.assign_module(self.get_main_propulsion_module())
            
            # Add Release phase to the plan
            deploy = Release(f"Satellites ({current_target.get_id()}) released",
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

    def get_initial_wet_mass(self):
        """Return the wet mass including payload mass.

        :return: dry mass + propellant mass + payload mass
        :rtype: flt (u.kg)
        """
        wet_mass = super().get_initial_wet_mass()
        wet_mass += self.get_initial_payload_mass()
        return wet_mass

    def get_initial_payload_mass(self):
        return sum([satellite.get_initial_wet_mass() for satellite in self.initial_spacecraft.values()])

    def get_modules_initial_wet_mass_str(self):
        """ Adds the payload mass to the list of initial wet masses

        :return: Text listing all modules mass and the payload mass
        :rtype: str
        """
        str_mass = super().get_modules_initial_wet_mass_str()
        str_mass += f"\n\t\tInitial payload = {self.get_initial_payload_mass():.2f}"
        return str_mass

    def generate_snapshot_string(self):
        """ Call the super() method with "kickstage" as parameter

        :return: string generated by the super() method
        :rtype: str
        """
        return super().generate_snapshot_string("KickStage")

    def print_spacecraft_specific_data(self):
        """ Prints values of some speicif attributes.
        """
        print(f"\tTotal payload mass available: {self.mass_available:.1f}"
        + f"\n\tTotal initial payload = {self.get_initial_payload_mass():.1f}"
        + f"\n\tLauncher mass filling ratio: {self.mass_filling_ratio * 100:.1f}%"
        + f"\n\tLauncher volume filling ratio: {self.volume_filling_ratio * 100:.1f}%"
        + f"\n\tNumber of spacecrafts onboard: {len(self.ordered_target_spacecraft)}")
