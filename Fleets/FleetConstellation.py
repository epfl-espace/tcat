"""
Created:        28.06.2022
Last Revision:  28.06.2022
Author:         Emilien Mingard
Description:    FleetConstellation related class
"""

# Import Classes
from Fleets.Fleet import Fleet
from Scenarios.ScenarioParameters import *

# Import libraries
import math

class FleetConstellation(Fleet):
    """ A Fleet consists of a dictionary of servicers.
        The class is initialized with an emtpy dictionary of servicers.
        It contains methods used during simulation and convergence of the servicers design.
    """

    """
    Init
    """
    def __init__(self, fleet_id, scenario):
        # Init super
        super().__init__(fleet_id,scenario)

    """
    Methods
    """
    def execute(self,clients):
        """ This function calls all appropriate methods to design the fleet to perform a particular plan.

        Args:
            clients (Constellation): full or tailored constellation containing satellite treated as targets to reach by any spacecraft
            verbose (boolean): if True, print convergence information
        """
        # Instanciate iteration limits
        execution_limit = EXECUTION_LIMIT
        execution_count = 1

        # Retrieve unassigned satellites
        unassigned_satellites = clients.get_optimized_ordered_satellites()

        # Spacecraft launcher counter
        spacecraft_count = 0

        # Start execution loop
        while len(unassigned_satellites)>0 and execution_count <= execution_limit:
            # Instanciate kickstage execution limit
            kickstage_execution_limit = EXECUTION_LIMIT
            kickstage_execution_count = 0
            kickstage_converged = False

            # Create KickStage
            spacecraft_count += 1
            kickstage = self.create_kickstage(f"KickStage_{spacecraft_count:04d}")
            kickstage_low_sat_allowance = 0
            kickstage_up_sat_allowance = kickstage.compute_allowance(unassigned_satellites)

            # Iterate until kickstage allowance is converged
            while kickstage_execution_count <= kickstage_execution_limit and not(kickstage_converged):
                # Check if converged
                if kickstage_low_sat_allowance == kickstage_up_sat_allowance:
                    # exit loop flat
                    kickstage_converged = True

                # Compute new current allowance
                kickstage_cur_sat_allowance = math.ceil((kickstage_low_sat_allowance+kickstage_up_sat_allowance)/2)

                # Execute kickstage
                assigned_satellites = unassigned_satellites[0:kickstage_cur_sat_allowance]
                kickstage.execute(assigned_satellites,constellation_precession=clients.get_global_precession_rotation())
                kickstage_main_propulsion_module = kickstage.get_main_propulsion_module()

                # Check for exit condition
                if kickstage_up_sat_allowance - kickstage_low_sat_allowance <= 1:
                    # If fuel mass > 0 and cur == up, then up is the solution
                    if kickstage_main_propulsion_module.get_current_prop_mass() > 0 and kickstage_cur_sat_allowance == kickstage_up_sat_allowance:
                        kickstage_low_sat_allowance = kickstage_up_sat_allowance
                    # If fuel mass < 0 then low is the solution for sure, hoping it is not zero.
                    else:
                        kickstage_up_sat_allowance = kickstage_low_sat_allowance

                # Apply dichotomia to remaining values
                else:
                    if kickstage_main_propulsion_module.get_current_prop_mass() > 0:
                        # If extra fuel, increase lower bound
                        kickstage_low_sat_allowance = kickstage_cur_sat_allowance

                    else:
                        # If lacking fuel, decrease upper bound
                        kickstage_up_sat_allowance = kickstage_cur_sat_allowance

                kickstage_execution_count += 1

            # Iterate until kickstage total deployment time is computed (If phasing existing)
            kickstage.execute_with_fuel_usage_optimisation(assigned_satellites,constellation_precession=clients.get_global_precession_rotation())
                         
            # Add converged KickStage and remove newly assigned satellite
            self.add_kickstage(kickstage)
            
            # Remove latest assigned satellites
            clients.remove_in_ordered_satellites(kickstage.get_ordered_target_spacecraft())
            
            # Check remaining satellites to be assigned
            unassigned_satellites = clients.get_optimized_ordered_satellites()

            # Update execution counter
            execution_count += 1
