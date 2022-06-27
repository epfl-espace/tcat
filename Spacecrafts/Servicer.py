import copy
import logging
import math

import numpy as np
from Modules.CaptureModule import CaptureModule
from Modules.PropulsionModule import PropulsionModule
from Phases.Insertion import Insertion
from Phases.OrbitChange import OrbitChange
from Phases.Release import Release
from Scenario.ScenarioParameters import *
from Spacecrafts.ActiveSpacecraft import ActiveSpacecraft
from astropy import units as u
from poliastro.bodies import Earth
from poliastro.twobody import Orbit

class Servicer(ActiveSpacecraft):
    """ TO BE FILLED
    """

    """
    Init
    """
    def __init__(self,id,scenario,additional_dry_mass = 0. * u.kg, mass_contingency = 0.2):
        # Init ActiveSpacecraft
        super(Servicer, self).__init__(id,"upperstage",additional_dry_mass,mass_contingency,scenario.starting_epoch,disposal_orbit = scenario.launcher_disposal_orbit,insertion_orbit = scenario.launcher_insertion_orbit)

    """
    Methods
    """
    def assign_ordered_satellites(self,clients,targetperservicers):
        """ Assigned remaining ordered satellites to current servicer

        Args:
            clients (Scenario.ConstellationSatellite.Constellation): clients/constellation to consider
        """
        # Remaining satellite to be delivered
        available_satellites = clients.get_optimized_ordered_satellites()

        # Assign sats
        self.assign_spacecraft(available_satellites[0:targetperservicers])

    def design(self,tech_level=1):
        """ Design the servicer

        Args:
            tech_level: dispenser technology level
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
Servicer:
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
