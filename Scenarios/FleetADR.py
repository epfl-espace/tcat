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
        spacecraft_count = 0

        # Strategy depend on architecture
        if self.scenario.architecture == "single_picker":
            for unassigned_satellite in unassigned_satellites:
                # Create Servicer and compute servicer plan
                servicer = Servicer(f"Servicer_{spacecraft_count:04d}",self.scenario,mass_contingency=0.0)
                servicer.execute(unassigned_satellite)

                # Create UpperStage
                spacecraft_count += 1
                upperstage = UpperStage(f"UpperStage_{spacecraft_count:04d}",self.scenario,mass_contingency=0.0)
                upperstage.execute(servicer,constellation_precession=0,custom_sat_allowance=1) # No RAAN margin and a single servicer per upperstage

                # Add converged UpperStage
                self.add_servicer(servicer)

                # Add converged UpperStage
                self.add_upperstage(upperstage)
                
                # Remove latest assigned satellites
                clients.remove_in_ordered_satellites(servicer.get_ordered_target_spacecraft())
                
                # Check remaining satellites to be assigned
                unassigned_satellites = clients.get_optimized_ordered_satellites()

                # Update execution counter
                execution_count += 1
            
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