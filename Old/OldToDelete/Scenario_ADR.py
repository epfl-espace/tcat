from ADRClient_module import *
from Fleet_module import *
from Plan_module import *
from Phases.Approach import Approach
from Phases.Capture import Capture
from Phases.Insertion import Insertion
from Phases.OrbitChange import OrbitChange
from Phases.Refueling import Refueling
from Phases.Release import Release
from Modules.AOCSModule import AOCSModule
from Modules.ApproachSuiteModule import ApproachSuiteModule
from Modules.CaptureModule import CaptureModule
from Modules.CommunicationModule import CommunicationModule
from Modules.DataHandlingModule import DataHandlingModule
from Modules.EPSModule import EPSModule

from Modules.PropulsionModule import PropulsionModule
from Modules.StructureModule import StructureModule
from Modules.ThermalModule import ThermalModule

from astropy.time import Time
import warnings
# warnings.filterwarnings("error")
warnings.filterwarnings("ignore")



class Scenario:
    """ A scenario is a class to represent one option within the tradespace of ADR service.
    It consist of objects describing the clients, the servicer fleet and the operational plan.

    The scenario is created based on the following tradespace parameters:
        - overall architecture (picker, shuttle or mothership with current_kits)
        - number of servicers
        - number of targets per servicer (not applicable for picker)
        - main propulsion technology
        - clients orbits at different times
        - servicers orbits at insertion
        
    The scenario is also dependant on parameters defined inside the following object:
        - client_module (target mass, constellation parameters, reliability models)
        - plan_module
            -phases (duration, cost model parameters)
        - fleet_module (convergence_margin criteria, fleet cost models)
            - servicers
                -modules (mass model parameters, cost model parameters, contingencies)
                
    Args:
        scenario_id (str): Standard id. Needs to be unique.
        architecture (str): String representing the main architecture assumption (picker, shuttle or current_kits)
        prop_type (str): Strong representing the technology used for the main propulsion of the servicer
                         (chemical or electrical)

    Attributes:
        ID (str): Standard id. Needs to be unique.
        clients (ADRClient_module.ADRClients): object describing the client constellation
        fleet (Fleet_module.Fleet): object describing the servicer fleet
        plan (Plan_module.Plan): object describing the operations of the service
        architecture (str): String representing the main architecture assumption (picker, shuttle or current_kits)
        prop_type (str): Strong representing the technology used for the main propulsion of the servicer
                         (chemical or electrical)
        starting_epoch (astropy.Time): reference time of first servicer launch
    """
    def __init__(self, scenario_id, architecture='shuttle', prop_type='electrical'):
        self.ID = scenario_id
        self.clients = None
        self.fleet = None
        self.plan = None
        self.architecture = architecture
        self.prop_type = prop_type
        self.starting_epoch = Time("2025-01-01 12:00:00", scale="tdb")
    
    def setup(self, targets_per_servicer=4, number_of_servicers=3, clients=None):
        """ Create the clients, fleet and plan based on inputs and assumptions.
        If clients is given in argument, it is used instead of redefining clients.
        Using clients as argument allows us to run different scenarios with the same constellation for comparison.

        Args:
            targets_per_servicer (int): number of targets that will be assigned to each servicer
            number_of_servicers (int): number of servicers that will be considered in the fleet
            clients (ADRClient_module.ADRClients): (optional) clients that serve as input; re-generated if not given
        """
        # If clients as argument, assign it to the class and reset it, otherwise define clients form scratch.

        if not clients:
            self.define_clients()
        else:
            self.clients = clients
            self.clients.reset()

        # check if picker has been defined correctly (without multiple targets per servicer)
        if self.architecture == 'picker' and targets_per_servicer > 1:
            raise Exception('Picker scenario only accepts one target per servicer.')

        # Define fleet given attributes of the class and parameters in arguments.
        self.define_fleet(targets_per_servicer=targets_per_servicer, number_of_servicers=number_of_servicers)

        # Define plan, given attributes of the class.
        self.define_plan()

    def execute(self, verbose=False):
        """ Execute the scenario until the fleet converges using a method from the fleet class.
        If Verbose is True, convergence_margin information will be printed.

        Args:
            verbose (boolean): if True, print information during scenario execution
        """
        # self.fleet.design(self.plan, self.clients, verbose=verbose)
        try:
            self.fleet.design(self.plan, self.clients, verbose=verbose)
            return True
        except RuntimeWarning as warning:
            return warning
        
    def define_fleet(self, targets_per_servicer=4, number_of_servicers=10):
        """ Define fleet object. This method depends on the given arguments as well as the architecture
        and propulsion type attributes of the class.

        Args:
            targets_per_servicer (int): number of targets that will be assigned to each servicer
            number_of_servicers (int): number of servicers that will be considered in the fleet
        """
        # Define relevant orbits
        servicer_insertion_orbit = self.define_servicers_orbits()
        # Define fleet
        fleet = Fleet('Servicers', self.architecture)
        # Iterate for the number of servicers, create appropriate servicers and add it to the fleet
        for index in range(0, number_of_servicers):
            servicer_id = 'servicer' + '{:04d}'.format(index)
            if self.architecture == 'shuttle':
                temp_servicer = self.create_shuttle(servicer_id, servicer_insertion_orbit, targets_per_servicer)
                fleet.add_servicer(temp_servicer)
            elif self.architecture == 'current_kits':
                temp_servicer = self.create_mothership(servicer_id, servicer_insertion_orbit, targets_per_servicer)
                fleet.add_servicer(temp_servicer)
            elif self.architecture == 'picker':
                temp_servicer = self.create_shuttle(servicer_id, servicer_insertion_orbit, targets_per_servicer)
                fleet.add_servicer(temp_servicer)
            elif self.architecture in ['refueled_shuttle_low', 'refueled_shuttle_high']:
                temp_servicer = self.create_shuttle(servicer_id, servicer_insertion_orbit, targets_per_servicer)
                temp_tanker = self.create_tanker("tanker_"+servicer_id, servicer_insertion_orbit, targets_per_servicer)
                fleet.add_servicer(temp_tanker)
                temp_servicer.assign_tanker(temp_tanker)
                fleet.add_servicer(temp_servicer)
            else:
                raise Exception('Unknown architecture {}'.format(self.architecture))
        # Assign fleet as attribute of class
        self.fleet = fleet

    def create_shuttle(self, servicer_id,  servicer_insertion_orbit, targets_per_servicer):
        """ Create a servicer based on the shuttle architecture.

        Args:
            servicer_id (str): id of the servicer to be created
            servicer_insertion_orbit (poliastro.twobody.Orbit): insertion orbit of the servicer to be created
            targets_per_servicer (int): number of targets that will be assigned to each servicer

        Return:
            (Fleet_module.Servicer): created servicer
        """
        # Create reference servicer
        reference_servicer = Servicer(servicer_id, 'ADR_servicers', expected_number_of_targets=targets_per_servicer)
        # Create propulsion depending on class attribute
        if self.prop_type == 'electrical':
            # phasing propulsion (electrical)
            guess = 0. * u.kg
            assumed_duty_cycle = 0.25
            if self.architecture in ['shuttle']:
                guess = 7. * u.kg * 2 ** (targets_per_servicer-1)
            elif self.architecture in ['current_kits']:
                guess = 6. * u.kg * 2 ** (targets_per_servicer - 1)
            elif self.architecture in ['refueled_shuttle_low']:
                guess = 20. * u.kg
                assumed_duty_cycle = 0.25
            elif self.architecture in ['refueled_shuttle_high']:
                guess = 80. * u.kg
            reference_phasing_propulsion = PropulsionModule(servicer_id + '_phasing_propulsion',
                                                            reference_servicer, 'electrical', 0.5 * u.N,
                                                            0.001 * u.N, 1500 * u.s,  guess,
                                                            50 * u.kg, propellant_contingency=0.05,
                                                            assumed_duty_cycle=assumed_duty_cycle)
            reference_phasing_propulsion.define_as_main_propulsion()
            # rendezvous propulsion (chemical)
            guess = 0. * u.kg
            if self.architecture in ['shuttle']:
                guess = 2. * u.kg * 2 ** (targets_per_servicer - 1)
            elif self.architecture in ['current_kits']:
                guess = 4.5 * u.kg * 2 ** (targets_per_servicer - 1)
            elif self.architecture in ['refueled_shuttle_low']:
                guess = 0.5 * u.kg * 2 ** (targets_per_servicer - 1)
            elif self.architecture in ['refueled_shuttle_high']:
                guess = 5. * u.kg * 2 ** (targets_per_servicer - 1)
            reference_rendezvous_propulsion = PropulsionModule(servicer_id + '_rendezvous_propulsion',
                                                               reference_servicer, 'mono-propellant', 22 * u.N,
                                                               0.01 * u.N, 249 * u.s, guess,
                                                               50. * u.kg, propellant_contingency=0.05)
            reference_rendezvous_propulsion.define_as_rcs_propulsion()
        elif self.prop_type == 'chemical':
            # one propulsion for both phasing and rendezvous (chemical)
            guess = 0. * u.kg
            if self.architecture in ['shuttle']:
                guess = 160. * u.kg * 2 ** (targets_per_servicer - 1)
            elif self.architecture in ['current_kits']:
                guess = 85. * u.kg * 2 ** (targets_per_servicer - 1)
            elif self.architecture in ['refueled_shuttle_low']:
                guess = 500. * u.kg
            elif self.architecture in ['refueled_shuttle_high']:
                guess = 70. * u.kg
            reference_phasing_propulsion = PropulsionModule(servicer_id + '_propulsion',
                                                            reference_servicer, 'mono-propellant', 22 * u.N,
                                                            0.01 * u.N, 249 * u.s, guess,
                                                            50 * u.kg, propellant_contingency=0.05)
            reference_phasing_propulsion.define_as_main_propulsion()
            reference_phasing_propulsion.define_as_rcs_propulsion()
        elif self.prop_type == 'water':
            # one propulsion for both phasing and rendezvous (chemical)
            guess = 0. * u.kg
            if self.architecture in ['shuttle']:
                guess = 140. * u.kg * 2 ** (targets_per_servicer - 1)
            elif self.architecture in ['current_kits']:
                guess = 90. * u.kg * 2 ** (targets_per_servicer - 1)
            elif self.architecture in ['refueled_shuttle_low']:
                guess = 500. * u.kg
            elif self.architecture in ['refueled_shuttle_high']:
                guess = 60. * u.kg
            reference_phasing_propulsion = PropulsionModule(servicer_id + '_propulsion',
                                                            reference_servicer, 'water', 4 * u.N,
                                                            0.01 * u.N, 450 * u.s, guess,
                                                            50 * u.kg, propellant_contingency=0.05)
            reference_phasing_propulsion.define_as_main_propulsion()
            reference_phasing_propulsion.define_as_rcs_propulsion()
        else:
            raise Exception('Unknown propulsion specified for scenario {}'.format(self.ID))
        # Define other modules
        reference_capture = CaptureModule(servicer_id + '_capture', reference_servicer)
        reference_capture.define_as_capture_default()
        reference_structure = StructureModule(servicer_id + '_structure', reference_servicer)
        reference_thermal = ThermalModule(servicer_id + '_thermal', reference_servicer)
        reference_aocs = AOCSModule(servicer_id + '_aocs', reference_servicer)
        reference_eps = EPSModule(servicer_id + '_eps', reference_servicer)
        reference_com = CommunicationModule(servicer_id + '_communication', reference_servicer)
        reference_data_handling = DataHandlingModule(servicer_id + '_data_handling', reference_servicer)
        reference_approach_suite = ApproachSuiteModule(servicer_id + '_approach_suite', reference_servicer)
        return reference_servicer
        
    def create_mothership(self, servicer_id, servicer_insertion_orbit, targets_per_servicer):
        """ Create a servicer based on the current_kits architecture.

        Args:
            servicer_id (str): id of the servicer to be created
            servicer_insertion_orbit (poliastro.twobody.Orbit): insertion orbit of the servicer to be created
            targets_per_servicer (int): number of targets that will be assigned to each servicer

        Return:
            (Fleet_module.Servicer): created servicer
        """
        # Create reference servicer
        reference_mothership = self.create_shuttle(servicer_id,  servicer_insertion_orbit, targets_per_servicer)
        # Iterate for the number of targets per servicer, create appropriate current_kits and add it to the mothership
        for index in range(0, targets_per_servicer):
            kit_id = servicer_id + '_kit{:04d}'.format(index)
            temp_kit = self.create_kit(kit_id, servicer_insertion_orbit)
            reference_mothership.assign_kit(temp_kit)
        return reference_mothership
        
    def create_kit(self, kit_id, kit_insertion_orbit):
        """ Create a kit.

        Args:
            kit_id (str): id of the kit to be created
            kit_insertion_orbit (poliastro.twobody.Orbit): insertion orbit of the kit to be created
                                                           this must match the mothership insertion orbit

        Return:
            (Fleet_module.Servicer): created servicer
        """
        # Create reference kit
        reference_kit = Servicer(kit_id, 'ADR_servicers', expected_number_of_targets=1,
                                 additional_dry_mass=0. * u.kg)
        # identify the servicer as a kit (useful to easily identify current_kits in other functions)
        reference_kit.is_kit = True
        # Define modules
        guess = 25. * u.kg
        kit_capture = CaptureModule(kit_id + '_capture', reference_kit, dry_mass_override=5 * u.kg)
        kit_capture.define_as_capture_default()
        kit_phasing_propulsion = PropulsionModule(kit_id + '_phasing_propulsion', reference_kit,
                                                  'solid', 20 * u.N, 0.1 * u.N, 240 * u.s, guess,
                                                  50 * u.kg, propellant_contingency=0.15)
        kit_phasing_propulsion.define_as_main_propulsion()
        kit_structure = StructureModule(kit_id + '_structure', reference_kit)
        kit_aocs = AOCSModule(kit_id + '_aocs', reference_kit)
        kit_eps = EPSModule(kit_id + '_eps', reference_kit, dry_mass_override=5 * u.kg)
        kit_com = CommunicationModule(kit_id + '_communication', reference_kit)
        return reference_kit

    def create_tanker(self, servicer_id, servicer_insertion_orbit, targets_per_servicer):
        """ Create a assigned_tanker to use in the refueling architecture.

        Args:
            servicer_id (str): id of the assigned_tanker to be created
            servicer_insertion_orbit (poliastro.twobody.Orbit): insertion orbit of the assigned_tanker to be created
            targets_per_servicer (int): number of targets that will be assigned to each servicer

        Return:
            (Fleet_module.Servicer): created assigned_tanker
        """
        # Create reference servicer
        reference_servicer = Servicer(servicer_id, servicer_insertion_orbit, 'refueling',
                                      expected_number_of_targets=targets_per_servicer)
        # Create propulsion depending on class attribute
        if self.prop_type == 'electrical':
            # phasing propulsion (electrical)
            if self.architecture == 'refueled_shuttle_low':
                guess = 50. * u.kg * targets_per_servicer
            elif self.architecture == 'refueled_shuttle_high':
                guess = 35. * u.kg * targets_per_servicer
            reference_phasing_propulsion = PropulsionModule(servicer_id + '_phasing_propulsion',
                                                            reference_servicer, 'electrical', 0.5 * u.N,
                                                            0.001 * u.N, 1500 * u.s, guess,
                                                            300 * u.kg, propellant_contingency=0.05)
        elif self.prop_type == 'chemical':
            # one propulsion for both phasing and rendezvous (chemical)
            if self.architecture == 'refueled_shuttle_low':
                guess = 200. * u.kg * targets_per_servicer
            elif self.architecture == 'refueled_shuttle_high':
                guess = 75. * u.kg * targets_per_servicer
            reference_phasing_propulsion = PropulsionModule(servicer_id + '_propulsion',
                                                            reference_servicer, 'mono-propellant', 22 * u.N,
                                                            0.01 * u.N, 249 * u.s, guess,
                                                            300 * u.kg, propellant_contingency=0.05)
        elif self.prop_type == 'water':
            # one propulsion for both phasing and rendezvous (chemical)
            if self.architecture == 'refueled_shuttle_low':
                guess = 250. * u.kg * targets_per_servicer
            elif self.architecture == 'refueled_shuttle_high':
                guess = 70. * u.kg * targets_per_servicer
            reference_phasing_propulsion = PropulsionModule(servicer_id + '_propulsion',
                                                            reference_servicer, 'water', 4 * u.N,
                                                            0.01 * u.N, 450 * u.s, guess,
                                                            300 * u.kg, propellant_contingency=0.05)
        else:
            raise Exception('Unknown propulsion specified for scenario {}'.format(self.ID))
        reference_phasing_propulsion.is_refueler = True
        reference_phasing_propulsion.define_as_main_propulsion()
        # Define other modules
        reference_capture = CaptureModule(servicer_id + '_capture', reference_servicer, dry_mass=5. * u.kg)
        reference_capture.define_as_capture_default()
        reference_structure = StructureModule(servicer_id + '_structure', reference_servicer)
        reference_thermal = ThermalModule(servicer_id + '_thermal', reference_servicer)
        reference_aocs = AOCSModule(servicer_id + '_aocs', reference_servicer)
        reference_eps = EPSModule(servicer_id + '_eps', reference_servicer)
        reference_com = CommunicationModule(servicer_id + '_communication', reference_servicer, dry_mass=5.*u.kg)
        reference_data_handling = DataHandlingModule(servicer_id + '_data_handling', reference_servicer, dry_mass=5.*u.kg)
        return reference_servicer

    def define_plan(self):
        """ Define plan according to clients and fleet."""
        # create plan
        self.plan = Plan('Plan', self.starting_epoch)
        # if there are targets to service, create plan
        if any(self.clients.get_failed_satellites()):
            self.assign_targets(self.architecture, self.prop_type, self.clients, self.fleet, number_of_planes=12)
            # define phases for the assigned targets
            self.define_fleet_mission_profile(self.architecture, self.fleet, self.clients)

    def assign_targets(self, architecture, prop_type, clients, fleet, number_of_planes=12):
        """Function that creates a plan based on an architecture, clients and fleet.

        Args:
            architecture (str): 'shuttle', 'current_kits' or 'picker',
                                for shuttle, the servicer raise its orbit back after each servicing
                                for current_kits, the servicer only visits each target and a kit performs deobriting
                                for picker, the servicer only services one target
            clients (ADRClient_module.ADRClients): population to be serviced
            fleet (Fleet_module.Fleet): servicers available to perform plan
        """
        # Determine if precession is turning counter-clockwise (1) or clockwise (-1)
        precession_direction = clients.get_global_precession_rotation()

        # Order targets by their current raan following precession direction, then by true anomaly
        ordered_targets_id = sorted(clients.get_failed_satellites(), key=lambda satellite_id:
        (precession_direction *
         clients.get_failed_satellites()[satellite_id].current_orbit.raan.value,
         clients.get_failed_satellites()[satellite_id].current_orbit.nu.value))

        # For each servicer, find optimal sequence of targets
        for servicer_ID, servicer in fleet.get_servicers_from_group('ADR_servicers').items():
            if ordered_targets_id:
                # initialize list which will contain the ideal sequence for each first target
                # initialized with -1 to avoid confusion with positive indexes
                sequence_list = np.full((len(ordered_targets_id),
                                         min(servicer.expected_number_of_targets, len(ordered_targets_id))), -1)
                print(sequence_list)
                # for the servicer, explore which target should be serviced first for optimal sequence
                for first_tgt_index in range(0, len(sequence_list)):
                    # set first target of sequence
                    sequence_list[first_tgt_index, 0] = first_tgt_index
                    first_tgt_id = ordered_targets_id[first_tgt_index]
                    first_tgt = clients.targets[first_tgt_id]

                    # for the first target, explore which next targets are achievable in terms of raan phasing
                    # first, initialize to the closest target and find which plane it is in
                    next_tgt_index = first_tgt_index
                    next_tgt_id = ordered_targets_id[next_tgt_index]
                    next_tgt = clients.targets[next_tgt_id]
                    reference_plane_id = next_tgt.ID.split('_')[1]
                    reference_plane_index = int(reference_plane_id[-2:])

                    # then, for each target slot available in the servicer after the first, check validity
                    for target_assigned_to_servicer in range(1, min(servicer.expected_number_of_targets,
                                                                    len(ordered_targets_id))):
                        if architecture == 'picker':
                            # no need to check this for picker architecture as only one target per servicer
                            pass
                        elif architecture in ['shuttle', 'current_kits', 'refueled_shuttle_low', 'refueled_shuttle_high']:
                            skip = 0
                            # if imposed by drift, introduce the need to skip to another plane between each servicing
                            if architecture in ['shuttle'] and prop_type in ['electrical']:
                                skip = 1
                            if architecture in ['refueled_shuttle_low'] and prop_type in ['chemical', 'water']:
                                skip = 1
                            if architecture in ['refueled_shuttle_low'] and prop_type in ['electrical']:
                                skip = 2
                            # find next valid target from previous target depending on number of skipped planes
                            counter = 0
                            valid_sequencing = False
                            while not valid_sequencing:
                                counter += 1
                                next_tgt_index = int((next_tgt_index + 1) % len(ordered_targets_id))
                                next_tgt_id = ordered_targets_id[next_tgt_index]
                                next_tgt = clients.targets[next_tgt_id]
                                current_plane_index = int(next_tgt.ID.split('_')[1][-2:])
                                valid_planes = [(reference_plane_index + precession_direction * step) % number_of_planes
                                                for step in list(range(skip, number_of_planes))]
                                # if the target is not already assigned, check validity
                                if next_tgt_index not in sequence_list[first_tgt_index, :]:
                                    # if no plane skip, the target is valid
                                    if skip == 0:
                                        valid_sequencing = True
                                    # otherwise, we check if plane is adequate
                                    elif current_plane_index in valid_planes:
                                        valid_sequencing = True
                                    # if no target could be found, then the first next target is chosen
                                    if counter > len(ordered_targets_id):
                                        valid_sequencing = True
                            reference_plane_id = next_tgt.ID.split('_')[1]
                            reference_plane_index = int(reference_plane_id[-2:])

                        else:
                            raise Exception('Unknown architecture {}'.format(architecture))

                        if architecture != 'picker':
                            # when a valid target is found, update sequence
                            sequence_list[first_tgt_index, target_assigned_to_servicer] = next_tgt_index

                # after establishing feasible options, compute criterium to prioritize between them
                raan_spread = []
                altitude = []
                for i in range(0, len(ordered_targets_id)):
                    # get targets id
                    target_id_list = [ordered_targets_id[i] for i in sequence_list[i, :]]

                    # find spread between first and last target raan in sequence
                    temp_raan_spread = (clients.targets[target_id_list[-1]].current_orbit.raan
                                        - clients.targets[target_id_list[0]].current_orbit.raan)
                    # make sure angles are all expressed correctly and adapt to precession direction
                    if temp_raan_spread == 0. * u.deg:
                        raan_spread.append(temp_raan_spread.to(u.deg).value)
                    elif np.sign(temp_raan_spread) == precession_direction:
                        raan_spread.append((precession_direction * temp_raan_spread).to(u.deg).value)
                    else:
                        temp_raan_spread = temp_raan_spread + precession_direction * 365 * u.deg
                        raan_spread.append((precession_direction * temp_raan_spread).to(u.deg).value)

                    # find sum of altitudes of all targets, this is used to prioritize sequences with lower targets
                    temp_altitude = sum([clients.targets[tgt_ID].current_orbit.a.to(u.km).value
                                         for tgt_ID in target_id_list])
                    altitude.append(temp_altitude)

                # find ideal sequence by merging raan and alt. in a table and ranking, first by raan, then by altitude
                ranking = [list(range(0, len(ordered_targets_id))), raan_spread, altitude]
                ranking = np.array(ranking).T.tolist()
                ranking = sorted(ranking, key=lambda element: (element[1], element[2]))
                best_first_target_index = int(ranking[0][0])

                # assign targets
                targets_assigned_to_servicer = [clients.targets[ordered_targets_id[int(tgt_id_in_list)]]
                                                for tgt_id_in_list in sequence_list[best_first_target_index, :]]
                for tgt in targets_assigned_to_servicer:
                    ordered_targets_id.remove(tgt.ID)
                servicer.assign_targets(targets_assigned_to_servicer)
                targets_assigned_to_servicer.clear()

    def define_fleet_mission_profile(self, architecture, fleet, clients):
        """ Call the appropriate servicer servicer_group profile definer for the whole fleet
        based on architecture and expected precession direction of the constellation.

        Args:
            architecture (str): 'shuttle', 'current_kits' or 'picker',
                                for shuttle, the servicer raise its orbit back after each servicing
                                for current_kits, the servicer only visits each target and a kit performs deobriting
                                for picker, the servicer only services one target
            fleet (Fleet_module.Fleet): fleet of servicers to assign the plan to
            clients (ADRClient_module.ADRClients): population to be serviced
        """
        precession_direction = clients.get_global_precession_rotation()
        for servicer_ID, servicer in fleet.servicers.items():
            if servicer.assigned_targets and architecture == 'shuttle':
                self.define_shuttle_mission_profile(servicer, precession_direction)
            elif servicer.assigned_targets and architecture == 'current_kits':
                self.define_kits_mission_profile(servicer, precession_direction)
            elif servicer.assigned_targets and architecture == 'picker':
                self.define_shuttle_mission_profile(servicer, precession_direction)
            elif servicer.assigned_targets and architecture == 'refueled_shuttle_low':
                if servicer.assigned_tanker:
                    self.define_refueled_shuttle_low_mission_profile(servicer, precession_direction)
            elif servicer.assigned_targets and architecture == 'refueled_shuttle_high':
                if servicer.assigned_tanker:
                    self.define_refueled_shuttle_high_mission_profile(servicer, precession_direction)
            elif servicer.assigned_targets:
                raise Exception('Unknown architecture {}'.format(architecture))

    def define_shuttle_mission_profile(self, servicer, precession_direction):
        """ Define shuttle servicer_group profile by creating and assigning adequate phases for a typical servicer_group profile.

        Args:
            servicer (Fleet_module.Servicer): servicer to which the profile will be assigned
            precession_direction (int): 1 if counter clockwise, -1 if clockwise (right hand convention)
        """
        # Update insertion raan, supposing each target can be sent to an ideal raan for operation
        # TODO : implement a launch optimizer
        first_target = servicer.assigned_targets[0]
        if servicer.get_main_propulsion_module().prop_type == 'electrical':
            insertion_raan_margin = 20. * u.deg
            delta_v_contingency = 0.2
            raan_cutoff = 0.6 * u.deg
        else:
            insertion_raan_margin = 15 * u.deg
            delta_v_contingency = 0.1
            raan_cutoff = 0.6 * u.deg
        insertion_orbit = Orbit.from_classical(Earth, self.define_servicers_orbits().a, self.define_servicers_orbits().ecc,
                                               self.define_servicers_orbits().inc,
                                               servicer.assigned_targets[0].operational_orbit.raan
                                               - precession_direction * insertion_raan_margin,
                                               self.define_servicers_orbits().argp, self.define_servicers_orbits().nu,
                                               self.define_servicers_orbits().epoch)
        # Servicer insertion
        insertion = Insertion('Insertion_' + servicer.ID, self.plan, insertion_orbit)
        insertion.assign_module(servicer.get_main_propulsion_module())

        # define starting orbit
        initial_phasing_orbit = insertion_orbit
        for i, target in enumerate(servicer.assigned_targets):
            # Raise to phasing orbit
            raising = OrbitChange('Orbit_raise_' + servicer.ID + '_' + target.ID, self.plan, target.current_orbit,
                                  raan_specified=True, initial_orbit=initial_phasing_orbit, raan_cutoff=raan_cutoff,
                                  delta_v_contingency=delta_v_contingency)
            raising.assign_module(servicer.get_main_propulsion_module())

            # Perform approach and capture
            approach = Approach('Approach_' + servicer.ID + '_' + target.ID, self.plan, target, 5. * u.kg)
            approach.assign_module(servicer.get_rcs_propulsion_module())
            capture = Capture('Capture_' + servicer.ID + '_' + target.ID, self.plan, target)
            capture.assign_module(servicer.get_capture_module())

            # Deorbit and release
            removal = OrbitChange('Removal_' + servicer.ID + '_' + target.ID, self.plan, target.disposal_orbit,
                                  initial_orbit=target.operational_orbit, delta_v_contingency=delta_v_contingency)
            removal.assign_module(servicer.get_main_propulsion_module())
            release = Release('Release_' + servicer.ID + '_' + target.ID, self.plan, target)
            release.assign_module(servicer.get_capture_module())

            # update starting orbit after
            initial_phasing_orbit = target.disposal_orbit

    def define_kits_mission_profile(self, servicer, precession_direction):
        """ Define current_kits servicer_group profile by creating and assigning adequate phases for a typical servicer_group profile.

        Args:
            servicer (Fleet_module.Servicer): servicer to which the profile will be assigned
            precession_direction (int): 1 if counter clockwise, -1 if clockwise (right hand convention)
        """
        # Update insertion raan, supposing each target can be sent to an ideal raan for operation
        # TODO : implement a launch optimizer
        first_target = servicer.assigned_targets[0]
        if servicer.get_main_propulsion_module().prop_type == 'electrical':
            insertion_raan_margin = 32. * u.deg
            delta_v_contingency = 0.2
            raan_cutoff = 0.1 * u.deg
        else:
            insertion_raan_margin = 15 * u.deg
            delta_v_contingency = 0.1
            raan_cutoff = 0.3 * u.deg
        insertion_orbit = Orbit.from_classical(Earth, self.define_servicers_orbits().a, self.define_servicers_orbits().ecc,
                                               self.define_servicers_orbits().inc,
                                               servicer.assigned_targets[0].operational_orbit.raan
                                               - precession_direction * insertion_raan_margin,
                                               self.define_servicers_orbits().argp, self.define_servicers_orbits().nu,
                                               self.define_servicers_orbits().epoch)
        # Servicer insertion
        insertion = Insertion('Insertion_' + servicer.ID, self.plan, insertion_orbit)
        insertion.assign_module(servicer.get_main_propulsion_module())

        # define starting orbit
        for i, target in enumerate(servicer.assigned_targets):
            if i == 0:
                raising = OrbitChange('Orbit_raise_' + servicer.ID, self.plan, target,
                                      raan_specified=True, initial_orbit=insertion_orbit,
                                      delta_v_contingency=delta_v_contingency, raan_cutoff=raan_cutoff)
                raising.assign_module(servicer.get_main_propulsion_module())

            # Perform approach and capture
            approach = Approach('Approach_' + servicer.ID + '_' + target.ID, self.plan, target, 5. * u.kg)
            approach.assign_module(servicer.get_rcs_propulsion_module())

            # Get kit
            relevant_kit = servicer.current_kits[servicer.ID + '_kit' + '{:04d}'.format(i)]
            capture = Capture('Capture_' + servicer.ID + '_' + target.ID, self.plan, target)
            capture.assign_module(relevant_kit.get_capture_module())

            # Deorbit and release
            removal = OrbitChange('Removal_' + servicer.ID + '_' + target.ID, self.plan, target.disposal_orbit,
                                  delta_v_contingency=delta_v_contingency)
            removal.assign_module(relevant_kit.get_main_propulsion_module())

            # for last one, deorbit mothership
            if i == len(servicer.assigned_targets) - 1:
                removal = OrbitChange('Removal_' + servicer.ID, self.plan, target.disposal_orbit,
                                      delta_v_contingency=delta_v_contingency)
                removal.assign_module(servicer.get_main_propulsion_module())
            else:
                # check if there needs to be some phasing to next plane
                next_raan = servicer.assigned_targets[i + 1].current_orbit.raan
                if abs(next_raan - target.current_orbit.raan) > 1 * u.deg:
                    phasing_orbit = Orbit.from_classical(Earth, target.disposal_orbit.a - 100 * u.km,
                                                         target.disposal_orbit.ecc, target.disposal_orbit.inc,
                                                         target.disposal_orbit.raan, target.disposal_orbit.argp,
                                                         target.disposal_orbit.nu, target.disposal_orbit.epoch)

                    phasing = OrbitChange('Orbit_phasing_' + servicer.ID + '_' + target.ID, self.plan, phasing_orbit,
                                          raan_specified=False, delta_v_contingency=delta_v_contingency)
                    phasing.assign_module(servicer.get_main_propulsion_module())

                    raising = OrbitChange('Orbit_raise_' + servicer.ID + '_' + target.ID, self.plan, servicer.assigned_targets[i + 1],
                                          raan_specified=True, initial_orbit=phasing_orbit,
                                          delta_v_contingency=delta_v_contingency, raan_cutoff=raan_cutoff)
                    raising.assign_module(servicer.get_main_propulsion_module())

    def define_refueled_shuttle_low_mission_profile(self, servicer, precession_direction):
        """ Define shuttle servicer_group profile by creating and assigning adequate phases for a typical servicer_group profile.

        Args:
            servicer (Fleet_module.Servicer): servicer to which the profile will be assigned
            precession_direction (int): 1 if counter clockwise, -1 if clockwise (right hand convention)
        """
        # Update insertion raan, supposing each target can be sent to an ideal raan for operation
        # TODO : implement a launch optimizer
        tanker = servicer.assigned_tanker
        first_target = servicer.assigned_targets[0]
        if servicer.get_main_propulsion_module().prop_type == 'electrical':
            insertion_raan_margin = 20. * u.deg
            raan_cutoff = 0.1 * u.deg
            delta_v_contingency = 0.2
        else:
            insertion_raan_margin = 10. * u.deg
            raan_cutoff = 0.3 * u.deg
            delta_v_contingency = 0.1
        insertion_orbit = Orbit.from_classical(Earth, servicer.insertion_orbit.a, servicer.insertion_orbit.ecc,
                                               servicer.insertion_orbit.inc,
                                               servicer.assigned_targets[0].operational_orbit.raan
                                               - precession_direction * insertion_raan_margin,
                                               servicer.insertion_orbit.argp, servicer.insertion_orbit.nu,
                                               servicer.insertion_orbit.epoch)

        # Servicer and assigned_tanker insertion
        insertion = Insertion('Insertion_' + servicer.ID, self.plan, insertion_orbit)
        insertion.assign_module(servicer.get_main_propulsion_module())
        insertion = Insertion('Insertion_' + tanker.ID, self.plan, insertion_orbit)
        insertion.assign_module(tanker.get_main_propulsion_module())

        # define starting orbit
        initial_phasing_orbit = insertion_orbit
        for i, target in enumerate(servicer.assigned_targets):
            # Raise to phasing orbit
            raising = OrbitChange('Orbit_raise_' + servicer.ID + '_' + target.ID, self.plan, target.current_orbit,
                                  raan_specified=True, initial_orbit=initial_phasing_orbit, raan_cutoff=raan_cutoff,
                                  delta_v_contingency=delta_v_contingency)
            raising.assign_module(servicer.get_main_propulsion_module())

            # Perform approach and capture
            approach = Approach('Approach_' + servicer.ID + '_' + target.ID, self.plan, target, 5. * u.kg)
            approach.assign_module(servicer.get_rcs_propulsion_module())
            capture = Capture('Capture_' + servicer.ID + '_' + target.ID, self.plan, target)
            capture.assign_module(servicer.get_capture_module())

            # Deorbit and release
            removal = OrbitChange('Removal_' + servicer.ID + '_' + target.ID, self.plan, tanker, initial_orbit=target,
                                  raan_specified=False, delta_v_contingency=delta_v_contingency)
            removal.assign_module(servicer.get_main_propulsion_module())
            release = Release('Release_' + servicer.ID + '_' + target.ID, self.plan, target)
            release.assign_module(servicer.get_capture_module())

            # unless last trip, refuel
            if i != len(servicer.assigned_targets) - 1:
                # RDV with assigned_tanker and refuel
                tanker_approach = Approach('Tanker_Approach_' + servicer.ID + '_' + target.ID, self.plan, tanker, 5. * u.kg,
                                           duration=3. * u.day)
                tanker_approach.assign_module(servicer.get_rcs_propulsion_module())
                tanker_capture = Capture('Tanker_Capture_' + servicer.ID + '_' + target.ID, self.plan, tanker,
                                         duration=2. * u.day)
                tanker_capture.assign_module(servicer.get_capture_module())
                refueling_as_servicer = Refueling('Refueling_' + servicer.ID + '_' + target.ID, self.plan)
                refueling_as_servicer.assign_module(servicer.get_main_propulsion_module())
                refueling_as_tanker = Refueling('Tanking_' + servicer.ID + '_' + target.ID, self.plan,
                                                refuel_mass=0. * u.kg)
                refueling_as_tanker.assign_module(tanker.get_main_propulsion_module())
                if i == len(servicer.assigned_targets) - 2:
                    refueling_as_servicer.last_refuel_for_recipient = True
                tanker_release = Release('Tanker_Release_' + servicer.ID + '_' + target.ID, self.plan, tanker,
                                         duration=1. * u.day)
                tanker_release.assign_module(servicer.get_capture_module())

            # update starting orbit after
            initial_phasing_orbit = tanker

    def define_refueled_shuttle_high_mission_profile(self, servicer, precession_direction):
        """ Define shuttle servicer_group profile by creating and assigning adequate phases for a typical servicer_group profile.

        Args:
            servicer (Fleet_module.Servicer): servicer to which the profile will be assigned
            precession_direction (int): 1 if counter clockwise, -1 if clockwise (right hand convention)
        """
        # Update insertion raan, supposing each target can be sent to an ideal raan for operation
        # TODO : implement a launch optimizer
        tanker = servicer.assigned_tanker
        first_target = servicer.assigned_targets[0]
        if servicer.get_main_propulsion_module().prop_type == 'electrical':
            raan_cutoff = 10. * u.deg
            delta_v_contingency = 0.2
        else:
            raan_cutoff = 10.0 * u.deg
            delta_v_contingency = 0.1
        insertion_orbit = Orbit.from_classical(Earth, first_target.current_orbit.a, first_target.current_orbit.ecc,
                                               first_target.current_orbit.inc,
                                               first_target.operational_orbit.raan,
                                               first_target.current_orbit.argp, first_target.current_orbit.nu,
                                               servicer.insertion_orbit.epoch)
        # Servicer and assigned_tanker insertion
        insertion = Insertion('Insertion_' + servicer.ID, self.plan, insertion_orbit)
        insertion.assign_module(servicer.get_main_propulsion_module())
        insertion = Insertion('Insertion_' + tanker.ID, self.plan, insertion_orbit)
        insertion.assign_module(tanker.get_main_propulsion_module())

        # define starting orbit
        for i, target in enumerate(servicer.assigned_targets):
            # Perform approach and capture
            approach = Approach('Approach_' + servicer.ID + '_' + target.ID, self.plan, target, 5. * u.kg)
            approach.assign_module(servicer.get_rcs_propulsion_module())
            capture = Capture('Capture_' + servicer.ID + '_' + target.ID, self.plan, target)
            capture.assign_module(servicer.get_capture_module())

            # Deorbit and release
            removal = OrbitChange('Removal_' + servicer.ID + '_' + target.ID, self.plan, target.disposal_orbit,
                                  delta_v_contingency=delta_v_contingency)
            removal.assign_module(servicer.get_main_propulsion_module())
            release = Release('Release_' + servicer.ID + '_' + target.ID, self.plan, target)
            release.assign_module(servicer.get_capture_module())

            # Raise to phasing orbit unless last target
            # unless last trip, refuel
            if i != len(servicer.assigned_targets) - 1:
                # if a change of plane is needed
                next_raan = servicer.assigned_targets[i + 1].current_orbit.raan
                if abs(next_raan - target.current_orbit.raan) > 10 * u.deg:
                    print('assigned_tanker phasing')
                    tanker_phasing_orbit = Orbit.from_classical(Earth, servicer.assigned_targets[i + 1].operational_orbit.a - 200 * u.km,
                                                         servicer.assigned_targets[i + 1].operational_orbit.ecc, servicer.assigned_targets[i + 1].operational_orbit.inc,
                                                         servicer.assigned_targets[i + 1].operational_orbit.raan, servicer.assigned_targets[i + 1].operational_orbit.argp,
                                                         servicer.assigned_targets[i + 1].operational_orbit.nu, servicer.assigned_targets[i + 1].operational_orbit.epoch)

                    tanker_phasing = OrbitChange('Tanker_phasing_' + servicer.ID + '_' + servicer.assigned_targets[i + 1].ID,
                                                 self.plan, tanker_phasing_orbit, raan_specified=False,
                                                 delta_v_contingency=delta_v_contingency)
                    tanker_phasing.assign_module(tanker.get_main_propulsion_module())

                    tanker_raising = OrbitChange('Tanker_raise_' + servicer.ID + '_' + servicer.assigned_targets[i + 1].ID,
                                                 self.plan, servicer.assigned_targets[i + 1], raan_specified=True, initial_orbit=tanker_phasing_orbit,
                                                 raan_cutoff=raan_cutoff, delta_v_contingency=delta_v_contingency)
                    tanker_raising.assign_module(tanker.get_main_propulsion_module())

                raising = OrbitChange('Orbit_raise_' + servicer.ID + '_' + servicer.assigned_targets[i + 1].ID,
                                      self.plan, servicer.assigned_tanker, raan_specified=True, initial_orbit=target.disposal_orbit,
                                      raan_cutoff=raan_cutoff, delta_v_contingency=delta_v_contingency)
                raising.assign_module(servicer.get_main_propulsion_module())

                # RDV with assigned_tanker and refuel
                tanker_approach = Approach('Tanker_Approach_' + servicer.ID + '_' + servicer.assigned_targets[i + 1].ID, self.plan, tanker, 5. * u.kg,
                                           duration=3. * u.day)
                tanker_approach.assign_module(servicer.get_rcs_propulsion_module())
                tanker_capture = Capture('Tanker_Capture_' + servicer.ID + '_' + servicer.assigned_targets[i + 1].ID, self.plan, tanker,
                                         duration=2. * u.day)
                tanker_capture.assign_module(servicer.get_capture_module())
                refueling_as_servicer = Refueling('Refueling_' + servicer.ID + '_' + servicer.assigned_targets[i + 1].ID, self.plan)
                refueling_as_servicer.assign_module(servicer.get_main_propulsion_module())
                refueling_as_tanker = Refueling('Tanking_' + servicer.ID + '_' + servicer.assigned_targets[i + 1].ID, self.plan,
                                                refuel_mass=0. * u.kg)
                refueling_as_tanker.assign_module(tanker.get_main_propulsion_module())
                if i == len(servicer.assigned_targets) - 2:
                    refueling_as_servicer.last_refuel_for_recipient = True
                tanker_release = Release('Tanker_Release_' + servicer.ID + '_' + servicer.assigned_targets[i + 1].ID, self.plan, tanker,
                                         duration=1. * u.day)
                tanker_release.assign_module(servicer.get_capture_module())

            # if last trip, deorbit assigned_tanker
            else:
                tanker_deorbit = OrbitChange('Tanker_deorbit_' + servicer.ID, self.plan, target.disposal_orbit,
                                             initial_orbit=target, delta_v_contingency=delta_v_contingency)
                tanker_deorbit.assign_module(tanker.get_main_propulsion_module())

    def define_clients(self, reliability=0.95):
        """ Define clients object.
        Given arguments can specify the reliability to use as input for reliability model.

        Args:
            reliability (float): (optional) satellite reliability at end of life

        Return:
            (ADRClient_module.ADRClients): created clients
        """
        # Define relevant orbits
        tgt_insertion_orbit, tgt_operational_orbit, tgt_disposal_orbit = self.define_clients_orbits()
        # Define reference satellite
        reference_satellite = Target('reference_OW_satellite', 150.*u.kg, tgt_insertion_orbit,
                                     tgt_operational_orbit, tgt_disposal_orbit)
        # Define the clients based on reference satellite
        clients = ADRClients('OneWeb')
        clients.populate_constellation('OneWeb', reference_satellite, number_of_planes=12, sat_per_plane=49)
        # Generate snapshot based on reliability model
        clients.randomly_fail_satellites(reliability=reliability, verbose=True)
        # Assign clients as class attribute
        self.clients = clients
        return clients

    def define_clients_orbits(self):
        """ Define orbits needed for clients definition.

        Return:
            (poliastro.twobody.Orbit): target insertion orbit
            (poliastro.twobody.Orbit): target operational orbit
            (poliastro.twobody.Orbit): target disposal orbit
        """
        # TODO: move this and possibly other assumptions and parameters to a configuration file
        # target insertion orbit
        a = 500 * u.km + Earth.R
        ecc = 0. * u.rad / u.rad
        inc = 86.0 * u.deg
        raan = 0. * u.deg
        argp = 90. * u.deg
        nu = 0. * u.deg
        target_insertion_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, self.starting_epoch)
        # target operational orbit
        a = 1200 * u.km + Earth.R
        ecc = 0.002 * u.rad / u.rad
        inc = 87.9 * u.deg
        raan = 0. * u.deg
        argp = 90. * u.deg
        nu = 0. * u.deg
        target_operational_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, self.starting_epoch)
        # target disposal orbit
        per_alt = 450. * u.km
        perigee = per_alt + Earth.R
        ap_alt = 1200. * u.km
        apogee = ap_alt + Earth.R
        a = (apogee + perigee) / 2
        ecc = (apogee - perigee) / (apogee + perigee)
        inc = 87.9 * u.deg
        raan = 0. * u.deg
        argp = 90. * u.deg
        nu = 0. * u.deg
        target_disposal_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, self.starting_epoch)
        return target_insertion_orbit, target_operational_orbit, target_disposal_orbit
    
    def define_servicers_orbits(self):
        """ Define orbits needed for servicers definition.

        Return:
            (poliastro.twobody.Orbit): servicers insertion orbit
        """
        # TODO: move this and possibly other assumptions and parameters to a configuration file
        # Servicer insertion orbit
        per_alt = 500. * u.km
        perigee = per_alt + Earth.R
        ap_alt = 500. * u.km
        apogee = ap_alt + Earth.R
        a = (apogee + perigee) / 2
        ecc = (apogee - perigee) / (apogee + perigee)
        inc = 86.0 * u.deg
        raan = 0. * u.deg
        argp = 0. * u.deg
        nu = 0. * u.deg
        service_insertion_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, self.starting_epoch)
        return service_insertion_orbit
    
    def get_total_cost(self, with_development=True):
        """ Returns total internal cost of the service in EUR.
        This cost only represent the internal cost of removal, not the cost of the service payed by the customer.

        Return:
            (float): cost in Euros
        """
        return self.fleet.get_total_cost(self.plan, with_development=with_development) + self.plan.get_total_cost(self.fleet)
    
    def get_number_of_serviced_targets(self):
        """ Returns total number of targets serviced at the end of service.

        Return:
            (int): number of failed targets that reached their disposal orbit
        """
        total_targets_serviced = 0
        for _, servicer in self.fleet.servicers.items():
            total_targets_serviced += len(servicer.assigned_targets)
        return total_targets_serviced
    
    def get_cost_per_target(self, with_development=True):
        """ Returns internal cost per target in EUR.
        This cost only represent the internal cost of removal, not the cost of the service payed by the customer.

        Return:
            (float): cost in Euros
        """
        return self.get_total_cost(with_development=with_development) / self.get_number_of_serviced_targets()
    
    def get_cost_summary(self):
        """ Returns information in a convenient way for plotting purposes.
        What is returned depends on the module_names list (currently hard coded).

        Return:
            ([str]): list of modules or module names
            ([[float]]): list that contains, for each element of module name, and for each servicer, its mass
        """
        # Define what will be returned by the function
        # (String has as to match a "get_" method from the scenario, fleet or plan class.)
        module_names = ['ground_segment_cost', 'servicers_recurring_cost', 'ait_cost', 'launch_cost',
                        'baseline_operations_cost', 'labour_operations_cost', 'moc_location_cost', 'gnd_stations_cost']

        # Initialize output as empty list
        output = []
        # for each quantity to plot, retrieve it and add it to the output
        for i, module_name in enumerate(module_names):
            output.append([self.get_attribute("get_" + module_name)/1000000*u.m/u.m])
        return module_names, output

    def get_attribute(self, attribute_name):
        """ Retrieve a specific information about the scenario.
        The information needs to be defined in a method of one of the following classes:
            - scenario, fleet, plan

        Args:
            attribute_name (str): attribute name, must be linked to a method or attribute

        Return:
            <>: attribute value
        """
        # check if this is available in the Scenario class
        if hasattr(self, attribute_name):
            return getattr(self, attribute_name)()
        # check if this is available in the Fleet class
        elif hasattr(self.fleet, attribute_name):
            return getattr(self.fleet, attribute_name)(self.plan)
        # check if this is available in the plan class
        elif hasattr(self.plan, attribute_name):
            return getattr(self.plan, attribute_name)(self.fleet)
        else:
            raise Exception('Unknown attribute {}'.format(attribute_name))
            return 0.
    
    def __str__(self):
        return self.ID
