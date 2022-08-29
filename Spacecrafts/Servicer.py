import copy
import logging
import math

import numpy as np
from Modules.CaptureModule import CaptureModule
from Modules.PropulsionModule import PropulsionModule
from Phases.Insertion import Insertion
from Phases.OrbitChange import OrbitChange
from Phases.Capture import Capture
from Phases.Release import Release
from Scenarios.ScenarioParameters import *
from Spacecrafts.ActiveSpacecraft import ActiveSpacecraft
from astropy import units as u
from poliastro.bodies import Earth
from poliastro.twobody import Orbit

class Servicer(ActiveSpacecraft):
    """ UpperStage acts ase a child Class implementing all necessary attributes relative upperstages.

    :param servicer_id: Servicer identification name
    :type servicer_id: str
    :param scenario: Scenario
    :type scenario: :class:`~Scenarios.Scenario.Scenario`
    :param additional_dry_mass: Additionnal dry mass
    :type additional_dry_mass: u*kg
    :param mass_contingency: Mass contingency
    :type mass_contingency: float
    """
    def __init__(self,servicer_id,scenario,structure_mass=0. * u.kg, mass_contingency = 0.0,volume=0.*u.m**3):
        # Init ActiveSpacecraft
        super(Servicer, self).__init__(servicer_id,"servicer",structure_mass,mass_contingency,scenario,volume=volume,disposal_orbit=scenario.servicer_disposal_orbit,insertion_orbit = scenario.servicer_insertion_orbit)

        # Design the launcher
        self.design()

    def execute(self,assigned_satellites):
        """ Reset, design and compute plan based on a list of assigned satellites

        :param assigned_satellites: Spacecraft assigned to the upperstage
        :type assigned_satellites: list(:class:`~Spacecrafts.Spacecraft.Spacecraft`)
        """
        # Perform initial setup (mass and volume available)
        self.reset()

        # Compute servicer modules
        self.design()

        # Assign target as per mass and volume allowance
        self.assign_spacecraft(assigned_satellites)

        # Define spacecraft mission profile
        self.define_mission_profile()

        # Execute upperstage (Apply owned plan)
        self.execute_plan()

    def design(self):
        """ Design the servicer main modules
        """
        # Add dispenser as CaptureModule
        dispenser = CaptureModule(self.id + '_Dispenser',
                                  self,
                                  mass_contingency=0.0,
                                  dry_mass_override=SERVICER_CAPTURE_DRY_MASS)

        self.set_capture_module(dispenser)

        # Add propulsion as PropulsionModule
        mainpropulsion = PropulsionModule(self.id + '_MainPropulsion',
                                          self, 'bi-propellant', SERVICER_MAX_THRUST,
                                          SERVICER_MIN_THRUST, SERVICER_ISP_THRUST, SERVICER_INITIAL_FUEL_MASS,
                                          SERVICER_MAXTANK_CAPACITY, reference_power_override=0 * u.W,
                                          propellant_contingency=SERVICER_FUEL_CONTINGENCY, dry_mass_override=SERVICER_PROPULSION_DRY_MASS,
                                          mass_contingency=SERVICER_PROP_MODULE_MASS_CONTINGENCY)
        self.set_main_propulsion_module(mainpropulsion)

    def define_mission_profile(self):
        """ Compute mission profile based on a basic canvas
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
                                               self.insertion_orbit.raan,
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
                              first_target.operational_orbit,
                              raan_specified=False,
                              delta_v_contingency=delta_v_contingency)

        # Assign propulsion module to raising phase
        raising.assign_module(self.get_main_propulsion_module())

        ##########
        # Step 3: Iterate through organised assigned targets
        ##########
        # Initialise current orbit object
        current_orbit = first_target.operational_orbit

        # Loop over assigned targets
        for i, current_target in enumerate(self.ordered_target_spacecraft):
            # Print target info
            #print(i,current_target,current_target.insertion_orbit,current_target.current_orbit)

            # Check for RAAN drift
            if abs(current_target.operational_orbit.raan - current_orbit.raan) > insertion_raan_window:
                # TODO Compute ideal phasing orgit
                phasing_orbit = copy.deepcopy(current_target.operational_orbit)
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
            
            ##########
            # Step 3.1: Capture the satellite
            ##########
            # Capture the satellite
            capture = Capture(f"Satellites ({current_target.get_id()}) captured", 
                                         self.plan,
                                         current_target,
                                         duration=20 * u.min)

            # Assign capture module to the Capture phase
            capture.assign_module(self.get_capture_module())

            # Set current_target to deployed
            current_target.state = "Captured"

            ##########
            # Step 3.2: Change orbit to satellite disposal
            ##########
            # Reach phasing orbit and add to plan
            satellite_disposal = OrbitChange(f"({self.id}) goes to satellite {current_target.get_id()} disposal orbit",
                                  self.plan,
                                  current_target.get_disposal_orbit(),
                                  raan_specified=False,
                                  delta_v_contingency=delta_v_contingency)

            # Assign propulsion module to OrbitChange phase
            satellite_disposal.assign_module(self.get_main_propulsion_module())

            ##########
            # Step 3.3: Release satellite
            ##########
            # Release the satellite
            deploy = Release(f"Satellites ({current_target.get_id()}) released",
                             self.plan,
                             current_target,
                             duration=20 * u.min)

            # Assign capture module to the Release phase
            deploy.assign_module(self.get_capture_module())

            # Set current_target to deployed
            current_target.state = "Released"

            # Update current orbit
            current_orbit = current_target.get_disposal_orbit()

            # Check current orbit altitude
            if (1-current_orbit.ecc)*current_orbit.a < ALTITUDE_ATMOSPHERE_LIMIT + Earth.R:
                # Return 0 as the servicer burnt
                return 0

        ##########
        # Step 4: De-orbit the servicer if necessary
        ##########
        # Add OrbitChange to the plan
        removal = OrbitChange(f"({self.id}) goes to disposal orbit", self.plan, self.disposal_orbit,delta_v_contingency=delta_v_contingency)

        # Assign propulsion module to OrbitChange phase
        removal.assign_module(self.get_main_propulsion_module())

        # Return 1 if success
        return 1

    def generate_snapshot_string(self):
        return super().generate_snapshot_string("Servicer")