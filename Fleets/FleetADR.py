"""
Created:        28.06.2022
Last Revision:  28.06.2022
Author:         Emilien Mingard
Description:    FleetADR related class
"""

# Import Classes
from Fleets.Fleet import Fleet
from Scenarios.ScenarioParameters import *
from Spacecrafts.Servicer import Servicer

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
        unassigned_satellites = clients.get_optimized_ordered_satellites().copy()

        # Spacecraft launcher counter
        upperstage_count = 0
        servicer_count = 0

        # Instanciate iteration limits
        execution_limit = max(100,len(unassigned_satellites))
        execution_count = 1

        # Strategy depend on architecture
        if self.scenario.architecture == "single_picker":
            while len(unassigned_satellites)>0 and execution_count <= execution_limit:
                # Create UpperStage
                upperstage_count += 1
                upperstage = self.create_upperstage(f"UpperStage_{upperstage_count:04d}")
                upperstage_converged = False

                # Instanciate assigned_servicers list
                assigned_servicers = []

                # Fill the upperstage as long as there is fuel left
                while not(upperstage_converged):
                    # Create Servicer
                    servicer_count += 1
                    current_servicer = Servicer(f"Servicer_{servicer_count:04d}",self.scenario,SERVICER_STRUCT_MASS,volume=SERVICER_DEFAULT_VOLUME)

                    # Assign the servicer
                    assigned_servicers.append(current_servicer)

                    # Compute upperstage based on servicer assigned to this upperstage
                    upperstage.execute(assigned_servicers,constellation_precession=0) # No RAAN margin and a single servicer per upperstage
                    upperstage_main_propulsion_module = upperstage.get_main_propulsion_module()

                    if upperstage_main_propulsion_module.get_current_prop_mass() < 0:
                        # Remove last
                        del assigned_servicers[-1]
                        servicer_count -= 1

                        # Upperstage has converged if last servicers is discared
                        upperstage_converged = True
                    
                    elif len(assigned_servicers) == len(unassigned_satellites):
                        # No more servicer necessary
                        upperstage_converged = True

                # If converged, execute with updated assigned servicers
                upperstage.execute(assigned_servicers,constellation_precession=0)

                # Add upperstage to fleet
                self.add_upperstage(upperstage)

                # Execute all servicers
                for i,servicer in enumerate(assigned_servicers):
                    # Execute servicer
                    servicer.execute(unassigned_satellites[i])
                    clients.remove_in_ordered_satellites(servicer.get_ordered_target_spacecraft())

                    # Add servicer to fleet
                    self.add_servicer(servicer)
                
                # Update remaining satellites to be assigned
                unassigned_satellites = clients.get_optimized_ordered_satellites().copy()

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

    def get_number_of_assigned_debris(self):
        nb_debris = 0
        for servicer in self.servicers.values():
            nb_debris += servicer.get_nb_target_spacecraft()
        return nb_debris

    def print_nb_fleet_spacecraft(self):
        super().print_nb_fleet_spacecraft()
        if self.get_number_servicers() > 1:
            print(f"Servicers: {self.get_number_servicers()}")
        else:
            print(f"Servicer: {self.get_number_servicers()}")
        print(f"Removed debris: {self.get_number_of_assigned_debris()}")