"""
Created:        28.06.2022
Last Revision:  28.06.2022
Author:         Emilien Mingard
Description:    FleetConstellation related class
"""

# Import Classes
from Scenarios.Fleet import Fleet
from Spacecrafts.UpperStage import UpperStage

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
        execution_limit = 100
        execution_count = 1

        # Retrieve unassigned satellites
        unassigned_satellites = clients.get_optimized_ordered_satellites()

        # Spacecraft launcher counter
        spacecraft_count = 0

        # Start execution loop
        while len(unassigned_satellites)>0 and execution_count <= execution_limit:
            # Instanciate upperstage execution limit
            upperstage_execution_limit = 20
            upperstage_execution_count = 0
            upperstage_converged = False

            # Create UpperStage
            spacecraft_count += 1
            upperstage = UpperStage(f"UpperStage_{spacecraft_count:04d}",self.scenario,mass_contingency=0.0)
            upperstage_low_sat_allowance = 0
            upperstage_up_sat_allowance = upperstage.compute_allowance(unassigned_satellites)

            # Iterate until upperstage allowance is converged
            while upperstage_execution_count <= upperstage_execution_limit and not(upperstage_converged):
                # Check if converged
                if upperstage_low_sat_allowance == upperstage_up_sat_allowance:
                    # exit loop flat
                    upperstage_converged = True

                # Compute new current allowance
                upperstage_cur_sat_allowance = math.ceil((upperstage_low_sat_allowance+upperstage_up_sat_allowance)/2)

                # Execute upperstage
                assigned_satellites = unassigned_satellites[0:upperstage_cur_sat_allowance]
                upperstage.execute(assigned_satellites,constellation_precession=clients.get_global_precession_rotation())
                upperstage_main_propulsion_module = upperstage.get_main_propulsion_module()

                # Check for exit condition
                if upperstage_up_sat_allowance - upperstage_low_sat_allowance <= 1:
                    # If fuel mass > 0 and cur == up, then up is the solution
                    if upperstage_main_propulsion_module.get_current_prop_mass() > 0 and upperstage_cur_sat_allowance == upperstage_up_sat_allowance:
                        upperstage_low_sat_allowance = upperstage_up_sat_allowance
                    # If fuel mass < 0 then low is the solution for sure, hoping it is not zero.
                    else:
                        upperstage_up_sat_allowance = upperstage_low_sat_allowance

                # Apply dichotomia to remaining values
                else:
                    if upperstage_main_propulsion_module.get_current_prop_mass() > 0:
                        # If extra fuel, increase lower bound
                        upperstage_low_sat_allowance = upperstage_cur_sat_allowance

                    else:
                        # If lacking fuel, decrease upper bound
                        upperstage_up_sat_allowance = upperstage_cur_sat_allowance

            # Iterate until upperstage total deployment time is computed (If phasing existing)
            upperstage.execute_with_fuel_usage_optimisation(assigned_satellites,constellation_precession=clients.get_global_precession_rotation())
                         
            # Add converged UpperStage and remove newly assigned satellite
            self.add_upperstage(upperstage)
            
            # Remove latest assigned satellites
            clients.remove_in_ordered_satellites(upperstage.get_ordered_target_spacecraft())
            
            # Check remaining satellites to be assigned
            unassigned_satellites = clients.get_optimized_ordered_satellites()

            # Update execution counter
            execution_count += 1
