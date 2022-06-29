"""
Created:        28.06.2022
Last Revision:  28.06.2022
Author:         Emilien Mingard
Description:    FleetADR related class
"""

# Import Classes
from Scenarios.Fleet import Fleet
from Spacecrafts.Servicer import Servicer
from Spacecrafts.UpperStage import UpperStage

# Import libraries
import warnings
import copy

class FleetADR(Fleet):
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

        # Dictionnaries of servicers and upperstages
        self.servicers = dict()

    """
    Methods
    """
    def execute(self,clients):
        """ This function calls all appropriate methods to design the fleet to perform a particular plan.

        Args:
            clients (Constellation): full or tailored constellation containing satellite treated as targets to reach by any spacecraft
            verbose (boolean): if True, print convergence information
        """
        # Retrieve unassigned broken satellites
        unassigned_satellites = clients.get_optimized_ordered_satellites()

        # Spacecraft launcher counter
        upperstage_count = 0
        servicer_count = 0

        # Instanciate iteration limits
        execution_limit = max(100,len(unassigned_satellites))
        execution_count = 1

        # Servicer list
        servicer_assigned_to_upperstage = []

        # Strategy depend on architecture
        if self.scenario.architecture == "single_picker":
            # Create UpperStage
            upperstage_count += 1
            upperstage = UpperStage(f"UpperStage_{upperstage_count:04d}",self.scenario)

            while len(unassigned_satellites)>0 and execution_count <= execution_limit:
                # Create Servicer
                servicer_count += 1
                current_servicer = Servicer(f"Servicer_{servicer_count:04d}",self.scenario)
                servicer_assigned_to_upperstage.append(current_servicer)

                # Compute upperstage based on servicer assigned to this upperstage
                upperstage.set_reference_spacecraft(current_servicer)
                upperstage.execute(servicer_assigned_to_upperstage,constellation_precession=0,custom_sat_allowance=1) # No RAAN margin and a single servicer per upperstage
                upperstage_main_propulsion_module = upperstage.get_main_propulsion_module()

                # Check if the upperstage still has fuel for more servicer
                if upperstage_main_propulsion_module.get_current_prop_mass() < 0:
                    # Remove last servicer
                    del servicer_assigned_to_upperstage[-1]

                    # Re-execute upperstage and update servicer starting epoch
                    upperstage.execute(servicer_assigned_to_upperstage,constellation_precession=0,custom_sat_allowance=1) # No RAAN margin and a single servicer per upperstage

                    # Create new UpperStage
                    upperstage_count += 1
                    upperstage = UpperStage(f"UpperStage_{upperstage_count:04d}",self.scenario,mass_contingency=0.0)

                    # Execute servicer from updated starting epoch
                    for i,servicer in enumerate(servicer_assigned_to_upperstage):
                        # Execute servicer
                        servicer.execute(unassigned_satellites[i])

                        # Remove target from ordered satellites
                        clients.remove_in_ordered_satellites(servicer.get_ordered_target_spacecraft())

                    # Reset list
                    servicer_assigned_to_upperstage = [current_servicer]
                
                # Check remaining satellites to be assigned
                unassigned_satellites = clients.get_optimized_ordered_satellites()
            
        elif self.scenario.architecture == "multi_picker":
            raise Exception('multi_picker option not available')

    def add_servicer(self, servicer):
        """ Adds a servicer to the Fleet class.

        Args:
            servicer (Servicer): servicer to add to the fleet
        """
        if servicer in self.servicers:
            warnings.warn('Servicer ', servicer.get_id(), ' already in fleet ', self.id, '.', UserWarning)
        else:
            self.servicers[servicer.get_id()] = servicer

        self.add_activespacecraft(servicer)

    def get_number_servicers(self):
        """ Compute and return size of self.servicers dict

        Return:
            (int): length of self.upperstages
        """
        return len(self.servicers)