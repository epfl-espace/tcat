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

        # Dictionnaries of servicers and kickstages
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

        # Create reference ADR servicer for loop control
        reference_servicer = Servicer(f"Servicer_test",self.scenario,self.scenario.servicer_struct_mass,volume=self.scenario.servicer_default_volume)

        # Spacecraft launcher counter
        kickstage_count = 0

        # Instanciate iteration limits
        execution_limit = max(100,len(unassigned_satellites))
        execution_count = 1

        # Strategy depend on architecture
        if self.scenario.mission_architecture == "single_picker":
            while len(unassigned_satellites)>0 and execution_count <= execution_limit:
                # Create KickStage
                kickstage_count += 1
                kickstage = self.create_kickstage(f"KickStage_{kickstage_count:04d}")
                kickstage_converged = False

                launcher_kickstage_allowance = kickstage.compute_allowance_ADR(unassigned_satellites, reference_servicer.get_initial_wet_mass(), reference_servicer.get_initial_volume())

                # Instanciate assigned_servicers list
                assigned_servicers = []
                servicer_count = 0

                # Fill the kickstage as long as there is fuel left in kick stage and servicer(s) mass doesn't exceed LV allowance
                while not(kickstage_converged) and servicer_count < launcher_kickstage_allowance:
                    # Create Servicer
                    servicer_count += 1
                    current_servicer = Servicer(f"Servicer_{kickstage_count}{servicer_count:03d}",self.scenario,self.scenario.servicer_struct_mass,volume=self.scenario.servicer_default_volume)
                    current_servicer.assign_spacecraft(unassigned_satellites[len(assigned_servicers)])

                    # Assign the servicer
                    assigned_servicers.append(current_servicer)

                    # Compute kickstage based on servicer assigned to this kickstage
                    kickstage.execute(assigned_servicers,constellation_precession=clients.get_global_precession_rotation()) # No RAAN margin and a single servicer per kickstage
                    kickstage_main_propulsion_module = kickstage.get_main_propulsion_module()

                    if kickstage_main_propulsion_module.get_current_prop_mass() < 0:
                        # Remove last
                        current_servicer.remove_last_spacecraft(current_servicer)
                        del assigned_servicers[-1]
                        servicer_count -= 1
                        kickstage.execute(assigned_servicers,constellation_precession=clients.get_global_precession_rotation())

                        # KickStage has converged if last servicers is discared
                        kickstage_converged = True
                    
                    elif len(assigned_servicers) == len(unassigned_satellites):
                        # No more servicer necessary
                        kickstage_converged = True

                # If converged, execute with updated assigned servicers
                kickstage.execute_with_fuel_usage_optimisation(assigned_servicers,constellation_precession=clients.get_global_precession_rotation())

                # Add kickstage to fleet
                self.add_kickstage(kickstage)

                # Execute all servicers
                for servicer in assigned_servicers:
                    # Execute servicer
                    servicer.execute()
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
            (int): length of self.kickstages
        """
        return len(self.servicers)

    def get_number_of_assigned_debris(self):
        nb_debris = 0
        for servicer in self.servicers.values():
            nb_debris += servicer.get_nb_target_spacecraft()
        return nb_debris

    def print_nb_fleet_spacecraft(self):
        """ Adds the number of servicers and removed debris.
        """
        super().print_nb_fleet_spacecraft()
        if self.get_number_servicers() > 1:
            print(f"Servicers: {self.get_number_servicers()}")
        else:
            print(f"Servicer: {self.get_number_servicers()}")
        print(f"Removed debris: {self.get_number_of_assigned_debris()}")