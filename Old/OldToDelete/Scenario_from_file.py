from Constellation_Client_Module import *
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
from Interpolation import get_launcher_performance, get_launcher_fairing
from astropy.time import Time
import warnings
from json import load as load_json

warnings.filterwarnings("error")


class Scenario:
    """
    The scenario is created based on the following tradespace parameters:
        -
        -
        -

    The scenario is also dependant on parameters defined inside the following object:
        -

    Args:
        scenario_id (str): Standard id. Needs to be unique.

    Attributes:
        ID (str): Standard id. Needs to be unique.
        clients (ADRClient_module.ADRClients): object describing the client constellation
        fleet (Fleet_module.Fleet): object describing the servicer fleet
        plan (Plan_module.Plan): object describing the operations of the service
        starting_epoch (astropy.Time): reference time of first servicer launch
    """

    FIELDS = ['architecture', 'prop_type', 'deployment_strategy', 'verbose', 'constellation_name', 'n_planes',
              'n_sats_per_plane', 'plane_distribution_angle', 'n_sats_simultaneously_deployed', 'launcher',
              'launch_site', 'orbit_type', 'dispenser_tech_level', 'custom_launcher_name',
              'fairing_diameter', 'fairing_cylinder_height', 'fairing_total_height', 'interpolation_method',
              'a_client_insertion', 'ecc_client_insertion', 'inc_client_insertion',
              'a_client_operational', 'ecc_client_operational', 'inc_client_operational',
              'a_launcher_insertion', 'ecc_launcher_insertion', 'inc_launcher_insertion '
              ]
    UNIT_FIELDS = [('target_mass', u.kg), ('target_volume', u.m ** 3), ('custom_launcher_performance', u.kg),
                   # ('fairing_diameter', u.m), ('fairing_cylinder_height', u.m), ('fairing_total_height', u.m)
                   ('a_client_insertion', u.km), ('ecc_client_insertion', u.one),  ('inc_client_insertion', u.deg),
                   ('a_client_operational', u.km), ('ecc_client_operational', u.one), ('inc_client_operational', u.deg),
                   ('a_launcher_insertion', u.km), ('ecc_launcher_insertion', u.one), ('inc_launcher_insertion', u.deg)
                   ]
    MISSING_FIELDS = ['starting_epoch']  # TODO add this field and parse it accordingly.

    def __init__(self, scenario_id, config_file):
        self.ID = scenario_id
        self.clients = None
        self.fleet = None
        self.plan = None
        self.ref_disp_volume = 0. * u.m ** 3
        self.ref_disp_mass = 0. * u.kg
        self.number_of_servicers = 0

        # read properties from json config file
        with open(config_file) as file:
            json = load_json(file)
        for field in self.FIELDS:
            if field in json:  # check for optional fields
                setattr(self, field, json[field])
        for (field, unit) in self.UNIT_FIELDS:
            if field in json:  # check for optional fields
                setattr(self, field, json[field] * unit)

        # missing in current json..
        self.starting_epoch = Time("2025-01-01 12:00:00", scale="tdb")  # needs conversion anyway.
        # self.launch_pad = "ELA-4"

        self.define_servicers_orbits()
        semimajor_axis = self.define_servicers_orbits().a.value
        self.apogee_h = (1 + self.define_servicers_orbits().ecc.value) * semimajor_axis - Earth.R.to(u.km).value
        self.perigee_h = 2 * semimajor_axis - self.apogee_h - 2 * Earth.R.to(u.km).value
        self.inclination = self.define_servicers_orbits().inc.value

    def setup(self, clients=None):
        """ Create the clients, fleet and plan based on inputs and assumptions.
        If clients is given in argument, it is used instead of redefining clients.
        Using clients as argument allows us to run different scenarios with the same constellation for comparison.

        Args:
            clients (Constellation_Client_Module.ConstellationClients): (optional) clients that serve as input; re-generated if not given
        """

        # TODO add capability to add clients via txt file
        # If clients as argument, assign it to the class and reset it, otherwise define clients form scratch.

        if not clients:
            self.define_clients()
        else:
            self.clients = clients
            self.clients.reset()

        # Define fleet given attributes of the class and parameters in arguments.
        self.define_fleet()

        # Define plan, given attributes of the class.
        self.define_plan()

    def execute(self):
        """ Execute the scenario until the fleet converges using a method from the fleet class.
        """
        # self.fleet.design(self.plan, self.clients, verbose=verbose)
        print("executing")
        try:
            self.fleet.design(self.plan, self.clients)
            return True
        except RuntimeWarning as warning:
            return warning

    def define_clients(self):
        """ Define clients object.
        Given arguments can specify the reliability to use as input for reliability model.

        Args:
            reliability (float): (optional) satellite reliability at end of life

        Return:
            (ADRClient_module.ADRClients): created clients
        """
        # TODO add non-standard constellations

        # Define relevant orbits
        tgt_insertion_orbit, tgt_operational_orbit, tgt_disposal_orbit = self.define_clients_orbits()
        # Define reference satellite
        # If satellite's volume is unknown it can be estimated
        if int(self.target_volume.value) == 0:
            x = self.target_mass
            self.target_volume = 9 * 10 ** -9 * x ** 3 - 10 ** -6 * x ** 2 + 0.0028 * x
        reference_satellite = Target('Reference_' + self.constellation_name + 'satellite', self.target_mass,
                                     self.target_volume,
                                     tgt_insertion_orbit,
                                     tgt_operational_orbit, tgt_disposal_orbit, state='standby', is_stackable=False)
        # Define the clients based on reference satellite
        clients = ConstellationClients(self.constellation_name)

        clients.populate_standard_constellation(self.constellation_name, reference_satellite,
                                                number_of_planes=self.n_planes, sat_per_plane=self.n_sats_per_plane,
                                                plane_distribution_angle=self.plane_distribution_angle,
                                                altitude_offset=10 * u.km)
        # Assign clients as class attribute
        self.clients = clients
        # For debug purposes, shows satellites distribution
        if self.verbose:
            clients.plot_3D_distribution(save="3D_plot", save_folder="Figures")
            clients.plot_distribution(save="2D_plot", save_folder="Figures")
        return clients

    def define_clients_orbits(self):
        """ Define orbits needed for clients definition.

        Return:
            (poliastro.twobody.Orbit): target operational orbit
        """
        # target insertion orbit
        target_insertion_orbit = Orbit.from_classical(Earth, self.a_client_insertion + Earth.R, self.ecc_client_insertion,
                                                      self.inc_client_insertion, 0. * u.deg, 90. * u.deg, 0. * u.deg,
                                                      self.starting_epoch)
        # target operational orbit
        target_operational_orbit = Orbit.from_classical(Earth, self.a_client_operational + Earth.R, self.ecc_client_operational,
                                                        self.inc_client_operational, 0. * u.deg, 90. * u.deg,
                                                        0. * u.deg, self.starting_epoch)
        # target disposal orbit
        a = (200 + 1100) / 2 * u.km + Earth.R
        ecc = (1100 - 200) / (1100 + 200) * u.rad / u.rad
        inc = 87.4 * u.deg
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
        # TODO: take this data from a database
        # Servicer insertion orbit
        servicer_insertion_orbit, _, _ = self.define_clients_orbits()
        return servicer_insertion_orbit

    def define_launchers_orbits(self):
        """ Define orbits needed for launchers definition.

        Return:
            (poliastro.twobody.Orbit): launchers insertion orbit
        """
        # TODO: take this data from a database
        # launcher insertion orbit
        launcher_insertion_orbit = Orbit.from_classical(Earth, self.a_launcher_insertion + Earth.R, self.ecc_launcher_insertion,
                                                        self.inc_launcher_insertion, 0. * u.deg, 90. * u.deg,
                                                        0. * u.deg,
                                                        self.starting_epoch)
        return launcher_insertion_orbit

    # def create_upper_stage(self, servicer_id):
    #     """ Create a servicer based on the shuttle architecture.
    #      # TODO: Update description
    #     Args:
    #         servicer_id (str): id of the servicer to be created
    #         servicer_insertion_orbit (poliastro.twobody.Orbit): insertion orbit of the servicer to be created
    #         targets_per_servicer (int): number of targets that will be assigned to each servicer
    #
    #     Return:
    #         (Fleet_module.Servicer): created servicer
    #     """
    #
    #     # Create reference upper stage
    #
    #     reference_upper_stage =
    #
    #     # Create propulsion depending on class attribute
    #     if self.prop_type == 'electrical':
    #         # phasing propulsion (electrical)
    #         guess = 0. * u.kg
    #         assumed_duty_cycle = 0.25
    #         if self.architecture in ['shuttle']:
    #             guess = 7. * u.kg * 2 ** (targets_per_servicer - 1)
    #         elif self.architecture in ['current_kits']:
    #             guess = 6. * u.kg * 2 ** (targets_per_servicer - 1)
    #         elif self.architecture in ['refueled_shuttle_low']:
    #             guess = 20. * u.kg
    #             assumed_duty_cycle = 0.25
    #         elif self.architecture in ['refueled_shuttle_high']:
    #             guess = 80. * u.kg
    #         reference_phasing_propulsion = PropulsionModule(servicer_id + '_phasing_propulsion',
    #                                                         reference_servicer, 'electrical', 0.5 * u.N,
    #                                                         0.001 * u.N, 1500 * u.s, guess,
    #                                                         50 * u.kg, propellant_contingency=0.05,
    #                                                         assumed_duty_cycle=assumed_duty_cycle)
    #         reference_phasing_propulsion.define_as_main_propulsion()
    #         # rendezvous propulsion (chemical)
    #         guess = 0. * u.kg
    #         if self.architecture in ['shuttle']:
    #             guess = 2. * u.kg * 2 ** (targets_per_servicer - 1)
    #         elif self.architecture in ['current_kits']:
    #             guess = 4.5 * u.kg * 2 ** (targets_per_servicer - 1)
    #         elif self.architecture in ['refueled_shuttle_low']:
    #             guess = 0.5 * u.kg * 2 ** (targets_per_servicer - 1)
    #         elif self.architecture in ['refueled_shuttle_high']:
    #             guess = 5. * u.kg * 2 ** (targets_per_servicer - 1)
    #         reference_rendezvous_propulsion = PropulsionModule(servicer_id + '_rendezvous_propulsion',
    #                                                            reference_servicer, 'mono-propellant', 22 * u.N,
    #                                                            0.01 * u.N, 249 * u.s, guess,
    #                                                            50. * u.kg, propellant_contingency=0.05)
    #         reference_rendezvous_propulsion.define_as_rcs_propulsion()
    #     elif self.prop_type == 'chemical':
    #         # one propulsion for both phasing and rendezvous (chemical)
    #         guess = 0. * u.kg
    #         if self.architecture in ['shuttle']:
    #             guess = 160. * u.kg * 2 ** (targets_per_servicer - 1)
    #         elif self.architecture in ['current_kits']:
    #             guess = 85. * u.kg * 2 ** (targets_per_servicer - 1)
    #         elif self.architecture in ['refueled_shuttle_low']:
    #             guess = 500. * u.kg
    #         elif self.architecture in ['refueled_shuttle_high']:
    #             guess = 70. * u.kg
    #         reference_phasing_propulsion = PropulsionModule(servicer_id + '_propulsion',
    #                                                         reference_servicer, 'mono-propellant', 22 * u.N,
    #                                                         0.01 * u.N, 249 * u.s, guess,
    #                                                         50 * u.kg, propellant_contingency=0.05)
    #         reference_phasing_propulsion.define_as_main_propulsion()
    #         reference_phasing_propulsion.define_as_rcs_propulsion()
    #     elif self.prop_type == 'water':
    #         # one propulsion for both phasing and rendezvous (chemical)
    #         guess = 0. * u.kg
    #         if self.architecture in ['shuttle']:
    #             guess = 140. * u.kg * 2 ** (targets_per_servicer - 1)
    #         elif self.architecture in ['current_kits']:
    #             guess = 90. * u.kg * 2 ** (targets_per_servicer - 1)
    #         elif self.architecture in ['refueled_shuttle_low']:
    #             guess = 500. * u.kg
    #         elif self.architecture in ['refueled_shuttle_high']:
    #             guess = 60. * u.kg
    #         reference_phasing_propulsion = PropulsionModule(servicer_id + '_propulsion',
    #                                                         reference_servicer, 'water', 4 * u.N,
    #                                                         0.01 * u.N, 450 * u.s, guess,
    #                                                         50 * u.kg, propellant_contingency=0.05)
    #         reference_phasing_propulsion.define_as_main_propulsion()
    #         reference_phasing_propulsion.define_as_rcs_propulsion()
    #     else:
    #         raise Exception('Unknown propulsion specified for scenario {}'.format(self.ID))
    #     # Define other modules
    #     reference_capture = CaptureModule(servicer_id + '_capture', reference_servicer)
    #     reference_capture.define_as_capture_default()
    #     reference_structure = StructureModule(servicer_id + '_structure', reference_servicer)
    #     reference_thermal = ThermalModule(servicer_id + '_thermal', reference_servicer)
    #     reference_aocs = AOCSModule(servicer_id + '_aocs', reference_servicer)
    #     reference_eps = EPSModule(servicer_id + '_eps', reference_servicer)
    #     reference_com = CommunicationModule(servicer_id + '_communication', reference_servicer)
    #     reference_data_handling = DataHandlingModule(servicer_id + '_data_handling', reference_servicer)
    #     reference_approach_suite = ApproachSuiteModule(servicer_id + '_approach_suite', reference_servicer)
    #     return reference_servicer

    def create_launch_vehicle(self, launch_vehicle_id, launcher, insertion_orbit, serviceable_sats_left,
                              rideshare=True):
        """ Create a launcher based on the shuttle architecture.

        Args:
            launch_vehicle_id (str): id of the launcher to be created
            launcher (str):
            insertion_orbit (poliastro.twobody.Orbit): insertion orbit of the launcher to be created
            rideshare (bool):

        Return:
            (Fleet_module.LaunchVehicle): created launcher
        """
        # TODO: add nationality of the launcher/satellite to automatically exclude some combination of launcher-satellite

        # TODO: make it possible to select a dispenser from a list or to insert custom data

        # Compute the launcher performance in order to assign it to the reference launch vehicle
        if self.custom_launcher_name is None:
            l_performance = get_launcher_performance(launcher, self.launch_site, self.inclination, self.apogee_h,
                                                     self.perigee_h, self.orbit_type, method=self.interpolation_method,
                                                     verbose=self.verbose)
        else:
            l_performance = self.custom_launcher_performance

        # Create reference launch vehicle
        reference_launch_vehicle = LaunchVehicle(launch_vehicle_id, launcher, insertion_orbit, rideshare=rideshare)

        # Assigning the available mass to the launcher
        reference_launch_vehicle.mass_available = l_performance

        # Compute fairing volume
        if self.fairing_diameter is None and self.fairing_cylinder_height is None and self.fairing_total_height is None:
            if self.custom_launcher_name is not None or self.custom_launcher_performance is not None:
                raise ValueError("You have inserted a custom launcher, but forgot to insert its related fairing size.")
            else:
                volume_available = get_launcher_fairing(launcher)
        else:
            cylinder_volume = np.pi * (self.fairing_diameter * u.m / 2) ** 2 * self.fairing_cylinder_height * u.m
            cone_volume = np.pi * (self.fairing_diameter * u.m / 2) ** 2 * (
                    self.fairing_total_height * u.m - self.fairing_cylinder_height * u.m)
            volume_available = (cylinder_volume + cone_volume).to(u.m ** 3)

        # Assigning the available volume to the launcher
        reference_launch_vehicle.volume_available = volume_available

        # Determine the number of equal satellites that can be accommodated in the launcher fairing
        reference_satellite = next(iter(self.clients.targets.values()))

        # Check if dispenser data were already computed to speed up the convergence
        if self.ref_disp_volume != 0. * u.m ** 3:
            reference_launch_vehicle.disp_mass = self.ref_disp_mass
            reference_launch_vehicle.disp_volume = self.ref_disp_volume
        serviced_sats, _, self.ref_disp_mass, self.ref_disp_volume = reference_launch_vehicle.converge_launch_vehicle(
            reference_satellite, serviceable_sats_left, tech_level=self.dispenser_tech_level)
        if self.verbose:
            print("Creating launch vehicle...")
            print(f"Launch vehicle: {launcher}")
            print(f"Mass available: {reference_launch_vehicle.mass_available}")
            print(f"Number of sats in the fairing: {serviced_sats}")
            print(f"Dispenser mass: {reference_launch_vehicle.disp_mass:.1f}")
            print(f"Mass filling ratio: {reference_launch_vehicle.mass_filling_ratio * 100:.1f}%")
            print(f"Dispenser volume: {reference_launch_vehicle.disp_volume:.1f}")
            print(f"Volume filling ratio: {reference_launch_vehicle.volume_filling_ratio * 100:.1f}%")
            print("_____________________________________")

        # Define launcher modules
        reference_dispenser = CaptureModule(launch_vehicle_id + '_dispenser', reference_launch_vehicle,
                                            dry_mass_override=self.ref_disp_mass)
        reference_dispenser.define_as_capture_default()

        guess = 0. * u.kg
        assumed_duty_cycle = 0.25
        reference_phasing_propulsion = PropulsionModule(launch_vehicle_id + '_phasing_propulsion',
                                                        reference_launch_vehicle, 'bi-propellant', 294000 * u.N,
                                                        294000 * u.N, 330 * u.s, guess,
                                                        5000 * u.kg, propellant_contingency=0.05)
        reference_phasing_propulsion.define_as_main_propulsion()

        # if self.architecture == "upper_stage":
        #     temp_upper_stage = self.create_upper_stage(self, servicer_id)
        # total_payload_mass=self.clients.Target().initial_mass*targets_per_servicer

        # for index in range(0, targets_per_servicer):
        #     sat_id = launch_vehicle_id + '_sat{:04d}'.format(index)
        #     temp_sat = self.create_sat(kit_id, servicer_insertion_orbit)
        #     reference_mothership.assign_kit(temp_kit)
        return reference_launch_vehicle, serviced_sats

    def define_fleet(self):
        """ Define fleet object. This method depends on the given arguments as well as the architecture
        and propulsion type attributes of the class.

        #TODO iterate with several launchers combination

        Args:
            targets_per_servicer (int): number of targets that will be assigned to each servicer
            number_of_servicers (int): number of servicers that will be considered in the fleet
        """
        # n_serviceable_sats_guess = 15
        number_of_targets = self.n_sats_per_plane * self.n_planes
        serviceable_sats_left = number_of_targets
        # number_of_servicers = int(number_of_targets / n_serviceable_sats_guess)
        # print(number_of_servicers)
        # Define relevant orbits
        servicer_insertion_orbit = self.define_servicers_orbits()
        # Define launch vehicle
        if self.custom_launcher_name is None:
            launcher = self.launcher
        else:
            launcher = self.custom_launcher_name
        # Define fleet
        fleet = Fleet('Servicers', self.architecture)
        # Iterate for the number of servicers, create appropriate servicers and add it to the fleet
        # TODO verify if it is wise to put here the "serviceable_sat_left" or it is better to have it in the "define_plan" method

        # for index in range(0, self.number_of_servicers):
        index = 0
        while serviceable_sats_left > 0:

            if self.architecture == 'launch_vehicle':
                servicer_id = 'launch_vehicle' + '{:04d}'.format(index)
                temp_launcher, serviced_sats = self.create_launch_vehicle(servicer_id, launcher,
                                                                          servicer_insertion_orbit,
                                                                          serviceable_sats_left,
                                                                          rideshare=True)
                serviceable_sats_left -= serviced_sats
                fleet.add_launcher(temp_launcher)
                index += 1
                # Update the number of servicers during convergence
                self.number_of_servicers = len(fleet.launchers)
            elif self.architecture == 'upper_stage':
                servicer_id = 'servicer' + '{:04d}'.format(index)
                temp_upper_stage = self.create_upper_stage()
                temp_launcher = self.create_launch_vehicle(servicer_id, launcher, servicer_insertion_orbit,
                                                           rideshare=True,
                                                           dispenser="Auto", tech_level=1)
                fleet.add_servicer(temp_upper_stage)
                temp_launcher.assign_upper_stage
                fleet.add_launcher(temp_launcher)
                index += 1

            else:
                raise Exception('Unknown architecture {}'.format(self.architecture))

        # Assign fleet as attribute of class
        self.fleet = fleet

    def define_plan(self):
        """ Define plan according to clients and fleet."""
        # create plan
        self.plan = Plan('Plan', self.starting_epoch)
        # if there are targets to service, create plan
        if any(self.clients.get_standby_satellites()):
            self.assign_targets(self.architecture, self.prop_type, self.clients, self.fleet,
                                number_of_planes=self.n_planes, deployment_strategy=self.deployment_strategy)
            # define phases for the assigned targets
            self.define_fleet_mission_profile(self.architecture, self.fleet, self.clients)

    def assign_targets(self, architecture, prop_type, clients, fleet, number_of_planes=12,
                       deployment_strategy='one_plane_at_a_time_sequential'):
        """Function that creates a plan based on an architecture, clients and fleet.

        Args:
            architecture (str): 'shuttle', 'current_kits' or 'picker',
                                for shuttle, the servicer raise its orbit back after each servicing
                                for current_kits, the servicer only visits each target and a kit performs deobriting
                                for picker, the servicer only services one target
            clients (Constellation_Client_Module.ConstellationClients): population to be serviced
            fleet (Fleet_module.Fleet): servicers available to perform plan
        """
        # Determine if precession is turning counter-clockwise (1) or clockwise (-1)
        precession_direction = clients.get_global_precession_rotation()

        # Order targets by their current raan following precession direction, then by true anomaly
        ordered_targets_id = sorted(clients.get_standby_satellites(), key=lambda satellite_id: (precession_direction *
                                                                                                clients.get_standby_satellites()[
                                                                                                    satellite_id].operational_orbit.raan.value,
                                                                                                clients.get_standby_satellites()[
                                                                                                    satellite_id].operational_orbit.nu.value))
        # For each launcher, find optimal sequence of targets' deployment
        for launcher_id, launcher in fleet.get_launchers_from_group('launcher').items():
            if ordered_targets_id:
                # initialize list which will contain the ideal sequence for each first target
                # initialized with -1 to avoid confusion with positive indexes
                sequence_list = np.full((len(ordered_targets_id),
                                         min(launcher.max_sats_number, len(ordered_targets_id))), -1)

                # for the launchers, explore which target should be deployed first for optimal sequence
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
                    for target_assigned_to_servicer in range(1, min(launcher.max_sats_number,
                                                                    len(ordered_targets_id))):
                        if architecture in ['launch_vehicle', 'upper_stage']:
                            skip = 0
                            # if imposed by drift, introduce the need to skip to another plane between each servicing
                            if architecture in ['launch_vehicle'] and prop_type in ['electrical']:
                                skip = 1
                            if architecture in ['upper_stage'] and prop_type in ['chemical', 'water']:
                                skip = 1
                            if architecture in ['upper_stage'] and prop_type in ['electrical']:
                                skip = 2
                            # if architecture in ['launch_vehicle'] and deployment_strategy in ['one_plane_at_a_time_sequential']:
                            #     skip = number_of_planes-1
                            # find next valid target from previous target depending on number of skipped planes
                            counter = 0
                            valid_sequencing = False
                            while not valid_sequencing:
                                counter += 1
                                next_tgt_index = int((next_tgt_index + 1) % len(ordered_targets_id))
                                next_tgt_id = ordered_targets_id[next_tgt_index]
                                next_tgt = clients.targets[next_tgt_id]
                                current_plane_index = int(next_tgt.ID.split('_')[1][-2:])

                                if deployment_strategy in ['one_plane_at_a_time_sequential']:
                                    valid_planes = [current_plane_index]

                                # TODO: add a distribution one plane at a time with a fixed plane shift

                                else:
                                    valid_planes = [
                                        (reference_plane_index + precession_direction * step) % number_of_planes
                                        for step in list(range(skip, number_of_planes))]
                                print(valid_planes)
                                # if the target is not already assigned, check validity
                                print(next_tgt_index, sequence_list[first_tgt_index, :])
                                if next_tgt_index not in sequence_list[first_tgt_index, :]:

                                    # if no plane skip, the target is valid
                                    if skip == 0:
                                        print("no plane to skip")
                                        valid_sequencing = True
                                    # otherwise, we check if plane is adequate
                                    elif current_plane_index in valid_planes:
                                        print("the plane is valid")
                                        valid_sequencing = True
                                    # if no target could be found, then the first next target is chosen
                                    if counter > len(ordered_targets_id):
                                        print("counter>target number")
                                        valid_sequencing = True
                            reference_plane_id = next_tgt.ID.split('_')[1]
                            reference_plane_index = int(reference_plane_id[-2:])

                        else:
                            raise Exception('Unknown architecture {}'.format(architecture))

                        if architecture != 'picker':
                            # when a valid target is found, update sequence
                            sequence_list[first_tgt_index, target_assigned_to_servicer] = next_tgt_index
                            # print(sequence_list)

                # after establishing feasible options, compute criterium to prioritize between them
                raan_spread = []
                altitude = []
                for i in range(0, len(ordered_targets_id)):
                    # get targets id
                    target_id_list = [ordered_targets_id[i] for i in sequence_list[i, :]]
                    print(target_id_list)
                    # find spread between first and last target raan in sequence
                    temp_raan_spread = (clients.targets[target_id_list[-1]].operational_orbit.raan
                                        - clients.targets[target_id_list[0]].operational_orbit.raan)
                    print(temp_raan_spread)
                    # make sure angles are all expressed correctly and adapt to precession direction
                    if temp_raan_spread == 0. * u.deg:
                        raan_spread.append(temp_raan_spread.to(u.deg).value)
                    elif np.sign(temp_raan_spread) == precession_direction:
                        raan_spread.append((precession_direction * temp_raan_spread).to(u.deg).value)
                    else:
                        temp_raan_spread = temp_raan_spread + precession_direction * 365 * u.deg
                        raan_spread.append((precession_direction * temp_raan_spread).to(u.deg).value)
                    print(raan_spread)

                    # find sum of altitudes of all targets, this is used to prioritize sequences with lower targets
                    temp_altitude = sum([clients.targets[tgt_ID].operational_orbit.a.to(u.km).value
                                         for tgt_ID in target_id_list])
                    altitude.append(temp_altitude)
                    print(altitude)

                # find ideal sequence by merging raan and alt. in a table and ranking, first by raan, then by altitude
                ranking = [list(range(0, len(ordered_targets_id))), raan_spread, altitude]
                ranking = np.array(ranking).T.tolist()
                ranking = sorted(ranking, key=lambda element: (element[1], element[2]))
                best_first_target_index = int(ranking[0][0])

                # TODO implement further sequencing rules (e.g. TSP optimization or other)

                # assign targets
                targets_assigned_to_servicer = [clients.targets[ordered_targets_id[int(tgt_id_in_list)]]
                                                for tgt_id_in_list in sequence_list[best_first_target_index, :]]
                for tgt in targets_assigned_to_servicer:
                    ordered_targets_id.remove(tgt.ID)
                launcher.assign_targets(targets_assigned_to_servicer)
                # ------ for debug purposes
                print(launcher_id)
                for x in range(len(launcher.assigned_targets)):
                    print(launcher.assigned_targets[x])
                # ------ for debug purposes
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
            clients (Constellation_Client_module.ConstellationClients): population to be serviced
        """
        precession_direction = clients.get_global_precession_rotation()
        print('yes')
        for servicer_ID, servicer, in fleet.servicers.items():
            print('working for servicer')
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
        for luncher_ID, launcher in fleet.launchers.items():
            print('working for launchers')
            if launcher.assigned_targets and architecture == 'launch_vehicle':
                self.define_launcher_mission_profile(launcher, precession_direction)

    def define_launcher_mission_profile(self, launcher, precession_direction):
        """ Define shuttle servicer_group profile by creating and assigning adequate phases for a typical servicer_group profile.

        Args:
            launcher (Fleet_module.LaunchVehicle): launcher to which the profile will be assigned
            precession_direction (int): 1 if counter clockwise, -1 if clockwise (right hand convention)
        """
        # Update insertion raan, supposing each target can be sent to an ideal raan for operation
        # TODO : implement a launch optimizer
        first_target = launcher.assigned_targets[0]
        insertion_raan_margin = 11 * u.deg
        delta_v_contingency = 0.1
        raan_cutoff = 10 * u.deg
        print(
            f"--------------------------------------------------------------------raan is {launcher.assigned_targets[0].operational_orbit.raan - precession_direction * insertion_raan_margin, precession_direction}")
        insertion_orbit = Orbit.from_classical(Earth, self.define_launchers_orbits().a - 100 * u.km,
                                               self.define_launchers_orbits().ecc,
                                               self.define_launchers_orbits().inc,
                                               launcher.assigned_targets[0].insertion_orbit.raan
                                               - precession_direction * insertion_raan_margin,
                                               self.define_launchers_orbits().argp, self.define_launchers_orbits().nu,
                                               self.define_launchers_orbits().epoch)
        # launcher insertion
        insertion = Insertion('Insertion_' + launcher.id, self.plan, insertion_orbit, duration=1 * u.h)
        insertion.assign_module(launcher.get_main_propulsion_module())

        # define starting orbit
        initial_phasing_orbit = insertion_orbit
        for i, target in enumerate(launcher.assigned_targets):
            # Initialize with all satellites stacked in the launcher
            capture = Capture('Capture_' + launcher.id + '_' + target.ID, self.plan, target, duration=0. * u.s)
            capture.assign_module(launcher.get_capture_module())
            print("capturing")

        for i, target in enumerate(launcher.assigned_targets):
            if i == 0:
                print("raise orbit")
                # Raise to phasing orbit
                print(target.insertion_orbit.raan, initial_phasing_orbit.raan)
                raising = OrbitChange('Orbit_raise_' + launcher.id + '_' + target.ID, self.plan, target.insertion_orbit,
                                      raan_specified=True, initial_orbit=launcher.insertion_orbit,
                                      raan_cutoff=raan_cutoff, raan_phasing_absolute=True,
                                      delta_v_contingency=delta_v_contingency)
                raising.assign_module(launcher.get_main_propulsion_module())
            if target.state != "Deployed":
                print("deployment")
                # Deployment:
                deploy = Release('Deploy_' + launcher.id + '_' + target.ID, self.plan, target, duration=20 * u.min)
                deploy.assign_module(launcher.get_capture_module())
                # target.current_orbit = launcher.current_orbit
                target.state = "Deployed"
                print(f"{launcher.assigned_targets[i]} state is {launcher.assigned_targets[i].state}")

                # update starting orbit after
                initial_phasing_orbit = target.insertion_orbit
                # for last one, deorbit launcher and dispenser
                if i == len(launcher.assigned_targets) - 1:
                    print("deorbit")
                    removal = OrbitChange('Removal_' + launcher.id, self.plan, target.disposal_orbit,
                                          delta_v_contingency=delta_v_contingency)
                    removal.assign_module(launcher.get_main_propulsion_module())

                else:
                    # check if it is possible to simoultaneously deploy several sats
                    print(launcher.assigned_targets[i + 1])
                    next_raan = launcher.assigned_targets[i + 1].insertion_orbit.raan
                    print(target, abs(next_raan - target.insertion_orbit.raan))

                    for j in list(range(1, self.n_sats_simultaneously_deployed)):
                        # check if there are other sats to be deployed
                        # check if the sats have the same raan and lie in the same orbital plane
                        try:

                            if i + j != len(launcher.assigned_targets) and abs(
                                    next_raan - launcher.assigned_targets[i + j - 1].insertion_orbit.raan) == 0 * u.deg:

                                print(f"deploy simoultaneously {launcher.assigned_targets[i + j]}")
                                deploy = Release('Deploy_' + launcher.id + '_' + launcher.assigned_targets[i + j].ID,
                                                 self.plan, launcher.assigned_targets[i + j],
                                                 duration=0 * u.min)
                                deploy.assign_module(launcher.get_capture_module())
                                launcher.assigned_targets[i + j].state = "Deployed"
                                try:
                                    next_raan = launcher.assigned_targets[i + j + 1].insertion_orbit.raan
                                except IndexError:
                                    next_raan = launcher.assigned_targets[0].insertion_orbit.raan

                            else:

                                # check if there needs to be some phasing to next plane
                                # print(launcher.assigned_targets[i + 1])
                                # # next_raan = launcher.assigned_targets[i + 1].current_orbit.raan
                                # print(target, abs(next_raan - target.current_orbit.raan))
                                if abs(next_raan - target.insertion_orbit.raan) > 1 * u.deg:
                                    print("phasing")
                                    # phasing_orbit = Orbit.from_classical(Earth, target.insertion_orbit.a - 100 * u.km,
                                    #                                      target.insertion_orbit.ecc,
                                    #                                      target.insertion_orbit.inc,
                                    #                                      target.insertion_orbit.raan,
                                    #                                      target.insertion_orbit.argp,
                                    #                                      target.insertion_orbit.nu,
                                    #                                      target.insertion_orbit.epoch)

                                    phasing_orbit = target.insertion_orbit
                                    phasing_orbit.a -= 100 * u.km
                                    print(target.insertion_orbit, phasing_orbit)

                                    phasing = OrbitChange('Orbit_phasing_' + launcher.id + '_' + target.ID, self.plan,
                                                          phasing_orbit,
                                                          raan_specified=False, delta_v_contingency=delta_v_contingency)
                                    phasing.assign_module(launcher.get_main_propulsion_module())

                                    raising = OrbitChange('Orbit_raise_' + launcher.id + '_' + target.ID, self.plan,
                                                          launcher.assigned_targets[i + 1].insertion_orbit,
                                                          raan_specified=True, initial_orbit=phasing_orbit,
                                                          delta_v_contingency=delta_v_contingency,
                                                          raan_cutoff=raan_cutoff)
                                    raising.assign_module(launcher.get_main_propulsion_module())
                        except IndexError:
                            pass
                        continue

        # for i, targets in enumerate(launcher.assigned_targets):
        #     print(f"{launcher.assigned_targets[i]} state is {launcher.assigned_targets[i].state}")

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
        insertion_orbit = Orbit.from_classical(Earth, self.define_servicers_orbits().a,
                                               self.define_servicers_orbits().ecc,
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
        insertion_orbit = Orbit.from_classical(Earth, self.define_servicers_orbits().a,
                                               self.define_servicers_orbits().ecc,
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

                    raising = OrbitChange('Orbit_raise_' + servicer.ID + '_' + target.ID, self.plan,
                                          servicer.assigned_targets[i + 1],
                                          raan_specified=True, initial_orbit=phasing_orbit,
                                          delta_v_contingency=delta_v_contingency, raan_cutoff=raan_cutoff)
                    raising.assign_module(servicer.get_main_propulsion_module())

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
