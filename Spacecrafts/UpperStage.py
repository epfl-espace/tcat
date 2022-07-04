import copy
import logging
import math

import numpy as np
from Modules.CaptureModule import CaptureModule
from Modules.PropulsionModule import PropulsionModule
from Phases.Insertion import Insertion
from Phases.OrbitChange import OrbitChange
from Phases.Release import Release
from Commons.Interpolation import get_launcher_fairing, get_launcher_performance
from Scenarios.ScenarioParameters import *
from Spacecrafts.ActiveSpacecraft import ActiveSpacecraft
from astropy import units as u
from poliastro.bodies import Earth
from poliastro.twobody import Orbit


class UpperStage(ActiveSpacecraft):
    """ TO BE FILLED
    """


    """
    Init
    """
    def __init__(self,id,scenario,additional_dry_mass=0. * u.kg,mass_contingency=0.2):
        # Init ActiveSpacecraft
        super(UpperStage, self).__init__(id,"upperstage",additional_dry_mass,mass_contingency,scenario,disposal_orbit = scenario.launcher_disposal_orbit,insertion_orbit = scenario.launcher_insertion_orbit)

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

        # Init ratio of inclination change in raan drift model
        self.ratio_inc_raan_from_scenario = scenario.mission_cash_limitor
        self.ratio_inc_raan_from_opti = 0.

        # Compute initial performances
        self.compute_upperstage(scenario)

    """
    Methods
    """
    def execute_with_fuel_usage_optimisation(self,satellites,constellation_precession=0):
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
            if self.main_propulsion_module.get_current_prop_mass()-UPPERSTAGE_REMAINING_FUEL_MARGIN >= 0:
                delta_inc_low = self.ratio_inc_raan_from_opti
            else:
                delta_inc_up = self.ratio_inc_raan_from_opti

            # detect algorithm's convergence
            if MODEL_RAAN_DELTA_INCLINATION_HIGH*(delta_inc_up-delta_inc_low) <= 2*MODEL_RAAN_DELTA_INCLINATION_LOW \
            or abs(self.main_propulsion_module.get_current_prop_mass()-remaining_fuel_prev) <= UPPERSTAGE_REMAINING_FUEL_TOLERANCE:
                converged = True

        # ensure remaining fuel is positive
        if self.main_propulsion_module.get_current_prop_mass()-UPPERSTAGE_REMAINING_FUEL_MARGIN < 0.:
            self.ratio_inc_raan_from_opti = delta_inc_low
            self.execute(satellites,constellation_precession=constellation_precession)

        return converged

    def execute(self,assigned_satellites,constellation_precession=0):
        """ Reset, redesign and compute the upperstage plan based on clients and satellite allowance

        Args:
            clients (Scenario.ConstellationSatellite.Constellation): clients/constellation to consider
            upperstage_cur_sat_allowance: allowance to assign to the launcher (for iterative purpose)
        """
        # Perform initial setup (mass and volume available)
        self.reset()

        # Compute launcher design for custom satellite allowance
        self.design(assigned_satellites)

        # Assign target as per mass and volume allowance
        self.assign_spacecraft(assigned_satellites)

        # Define spacecraft mission profile
        self.define_mission_profile(constellation_precession)

        # Execute upperstage (Apply owned plan)
        self.execute_plan()

    def reset(self):
        """ Reset the object to inital parameters. Empty the plan
        """
        # Reset ActiveSpacecraft
        super().reset()

        # Reset attribut
        self.mass_filling_ratio = 1
        self.volume_filling_ratio = 1
        self.dispenser_mass = 0. * u.kg
        self.dispenser_volume = 0. * u.m ** 3

        # Empty targets
        self.sats_number = 0
    
    def design(self,assigned_satellites,tech_level=1):
        """ Design the upperstage based on allowance, tech_level and current performances

        Args:
            custom_sat_allowance: allowance to assign to the launcher (for iterative purpose)
            tech_level: dispenser technology level
        """
        # Compute filling ratio and disp mass and volume
        self.total_satellites_mass = sum([satellite.get_initial_mass() for satellite in assigned_satellites])
        self.mass_filling_ratio = self.total_satellites_mass / self.mass_available
        self.volume_filling_ratio = sum([satellite.get_initial_volume() for satellite in assigned_satellites]) / self.volume_available

        # Add dispenser as CaptureModule
        dispenser_mass = 0.1164 * self.total_satellites_mass / tech_level
        dispenser = CaptureModule(self.id + '_Dispenser',
                                            self,
                                            mass_contingency=0.0,
                                            dry_mass_override=dispenser_mass)

        self.set_capture_module(dispenser)

        # Add propulsion as PropulsionModule
        mainpropulsion = PropulsionModule(self.id + '_MainPropulsion',
                                          self, 'bi-propellant', UPPERSTAGE_MAX_THRUST,
                                          UPPERSTAGE_MIN_THRUST, UPPERSTAGE_ISP_THRUST, UPPERSTAGE_INITIAL_FUEL_MASS,
                                          UPPERSTAGE_MAXTANK_CAPACITY, reference_power_override=0 * u.W,
                                          propellant_contingency=UPPERSTAGE_FUEL_CONTINGENCY, dry_mass_override=UPPERSTAGE_PROPULSION_DRY_MASS,
                                          mass_contingency=UPPERSTAGE_PROP_MODULE_MASS_CONTINGENCY)
        self.set_main_propulsion_module(mainpropulsion)

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
        limit_mass = math.floor(self.mass_available/self.constellation_reference_spacecraft.get_initial_mass())

        # Compute limit in volume terms
        limit_volume = math.floor(self.volume_available/self.constellation_reference_spacecraft.get_current_volume())

        # Minimal value is of interest
        self.satellites_allowance =  min([limit_volume,limit_mass,len(unassigned_satellites)])

        # Return allowance
        return self.satellites_allowance

    def get_satellites_allowance(self):
        """ Return maximum allowable of the upperstage
        """
        return self.satellites_allowance

    def compute_delta_inclination_for_raan_phasing(self):
        """ Computes the inclination change for RAAN phasing basd on two ratios:
        self.ratio_inc_raan_from_scenario: lets the senario define how much dV should be used to accelrate phasing
        self.ratio_inc_raan_from_opti: used by optimisation loop minimising phasing duration with the available fuel
        """
        total_ratio = self.ratio_inc_raan_from_scenario + self.ratio_inc_raan_from_opti
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

    def print_report(self):
        print(f"-"*72
        + "\nActiveSpacecraft.UpperStage:"
        + f"\n\tSpacecraft id: {self.get_id()}"
        + f"\n\tLaunch vehicle name: {self.launcher_name}"
        + f"\n\tDry mass: {self.get_dry_mass():.01f}"
        + f"\n\tWet mass: {self.get_wet_mass():.01f}"
        + f"\n\tFuel mass margin: {self.get_main_propulsion_module().current_propellant_mass:.1f}"
        + f"\n\tTotal payload mass available: {self.mass_available:.1f}"
        + f"\n\tMass filling ratio: {self.mass_filling_ratio * 100:.1f}%"
        + f"\n\tVolume filling ratio: {self.volume_filling_ratio * 100:.1f}%"
        + f"\n\tNumber of spacecrafts onboard: {self.sats_number}"
        + f"\n\tAssigned Spacecrafts:")

        for target in self.ordered_target_spacecraft:
            print(f"\t\t{target}")

        print("---")
        self.plan.print_report()
        print("---")

        print('Modules:')
        for _, module in self.modules.items():
            print(f"\tModule ID: {module}")