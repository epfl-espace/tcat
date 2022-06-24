import copy
import logging
import math

import numpy as np
from Modules.CaptureModule import CaptureModule
from Modules.PropulsionModule import PropulsionModule
from Phases.Insertion import Insertion
from Phases.OrbitChange import OrbitChange
from Phases.Release import Release
from Scenario.Interpolation import get_launcher_fairing, get_launcher_performance
from Scenario.ScenarioParameters import *
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
        super(UpperStage, self).__init__(id,"upperstage",additional_dry_mass,mass_contingency,scenario.starting_epoch,disposal_orbit = scenario.launcher_disposal_orbit,insertion_orbit = scenario.launcher_insertion_orbit)

        # Launcher name
        self.launcher_name = scenario.launcher_name

        # Keep a satellite as reference
        self.reference_satellite = scenario.reference_satellite

        # Set mass, volumes and filling ratio
        self.volume_available = None
        self.mass_available = None
        self.mass_filling_ratio = 1
        self.volume_filling_ratio = 1
        self.dispenser_mass = 0. * u.kg
        self.dispenser_volume = 0. * u.m ** 3
        self.satellites_allowance = 0

        # Init ratio of inclination change in raan drift model
        self.ratio_inc_raan_from_scenario = scenario.mission_cost_vs_duration_factor
        self.ratio_inc_raan_from_opti = 0.

        # Compute initial performances
        self.compute_upperstage(scenario)

    """
    Methods
    """
    def execute_with_fuel_usage_optimisation(self,clients):
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
            self.execute(clients,self.satellites_allowance)

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
        # Reset ActiveSpacecraft
        super().reset()

        # Reset attribut
        self.mass_filling_ratio = 1
        self.volume_filling_ratio = 1
        self.dispenser_mass = 0. * u.kg
        self.dispenser_volume = 0. * u.m ** 3

        # Empty targets
        self.sats_number = 0
    
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
        dispenser = CaptureModule(self.id + '_Dispenser',
                                            self,
                                            mass_contingency=0.0,
                                            dry_mass_override=dispenser_mass)

        self.set_capture_module(dispenser)

        # Add propulsion as PropulsionModule
        mainpropulsion = PropulsionModule(self.id + '_MainPropulsion',
                                                        self, 'bi-propellant', 294000 * u.N,
                                                        294000 * u.N, 330 * u.s, UPPERSTAGE_INITIAL_FUEL_MASS,
                                                        5000 * u.kg, reference_power_override=0 * u.W,
                                                        propellant_contingency=0.05, dry_mass_override=UPPERSTAGE_PROPULSION_DRY_MASS,
                                                        mass_contingency=0.2)
        self.set_main_propulsion_module(mainpropulsion)

    def assign_ordered_satellites(self,clients):
        """ Assigned remaining ordered satellites to current launcher within allowance

        Args:
            clients (Scenario.ConstellationSatellite.Constellation): clients/constellation to consider
        """
        # Remaining satellite to be delivered
        available_satellites = clients.get_optimized_ordered_satellites()

        # Assign sats
        self.assign_spacecraft(available_satellites[0:self.satellites_allowance])

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

    def get_satellites_allowance(self):
        """ Return maximum allowable of the upperstage
        """
        return self.satellites_allowance

    def get_current_mass(self):
        """ Returns the total mass of the launcher, including all modules and kits at the current time in the simulation.

        Return:
            (u.kg): current mass, including kits
        """
        # Instanciate current mass
        current_mass = 0

        # Add propulsion current mass
        current_mass += self.main_propulsion_module.get_current_prop_mass() + self.main_propulsion_module.get_dry_mass()

        # Add capture module mass
        current_mass += self.capture_module.get_dry_mass()

        # Add satellites masses
        current_mass += sum([self.current_spacecraft[key].get_current_mass() for key in self.current_spacecraft.keys()])

        # Return current mass
        return current_mass

    def get_initial_mass(self):
        """ Returns the total mass of the launcher, including all modules and kits at the launch time in the simulation.

        Return:
            (u.kg): current mass, including kits
        """
        # Instanciate initial mass
        initial_mass = 0

        # Add propulsion initial mass
        initial_mass += self.main_propulsion_module.get_initial_prop_mass() + self.main_propulsion_module.get_dry_mass()

        # Add capture module mass
        initial_mass += self.capture_module.get_dry_mass()

        # Add satellites masses
        initial_mass += sum([satellite.get_initial_mass() for satellite in self.ordered_target_spacecraft])

        # Return initial mass
        return initial_mass

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
        self.plan.print_report()
        """ Print quick summary for debugging purposes."""
        print(f"""---\n---
Launch Vehicles:
    ID: {self.get_id()}
    Launch vehicle name: {self.launcher_name}
    Dry mass: {self.get_dry_mass():.01f}
    Wet mass: {self.get_wet_mass():.01f}
    Fuel mass margin: {self.get_main_propulsion_module().current_propellant_mass:.2f}
    Payload mass available: {self.mass_available}
    Number of satellites: {self.sats_number}
    Dispenser mass: {self.dispenser_mass:.1f}
    Mass filling ratio: {self.mass_filling_ratio * 100:.1f}%
    Dispenser volume: {self.dispenser_volume:.1f}
    Volume filling ratio: {self.volume_filling_ratio * 100:.1f}%
    Targets assigned to the Launch vehicle:""")

        for x in range(len(self.ordered_target_spacecraft)):
            print(f"\t\t{self.ordered_target_spacecraft[x]}")

        print("---")

        print('Modules:')
        for _, module in self.modules.items():
            print(f"\tModule ID: {module}")
        print('\tPhasing Module ID: ' + self.main_propulsion_module.id)
        print('\tCapture module ID : ' + self.capture_module.id)