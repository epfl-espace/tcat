# Created:          15.06.2022
# Last Revision:    30.06.2022
# Authors:          Emilien Mingard, Malo Goury du Roslan
# Emails:           emilien.mingard@tcdc.ch, malo.goury@tcdc.ch
# Description:      Parent class for the different implemented scenarios

# Import Class
from Scenarios.ScenarioParameters import KICKSTAGE_DATABASE, PATH_DB_KICKSTAGE
from SpacecraftDatabase.KickstageDatabaseReader import KickstageDatabaseReader
from Spacecrafts.Satellite import Satellite
from Plan.Plan import *
from Constellations.Constellation import Constellation

# Set logging
logging.getLogger('numba').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.addLevelName(21, "DEBUGGING")

# Class definition
class Scenario:
    """ Parent class for the different implemented Scenarios. 
    A scenario triggers the following tasks:
    
    - setup the simulation based on input json
    - create the :class:`~Fleets.Fleet.Fleet` and :class:`~Constellations.Constellation.Constellation` required for the mission
    - optimises the :class:`~Plans.Plan.Pan`
    - print the result
    """    
    general_fields = ['scenario',
                      'verbose',
                      'starting_epoch',
                      'dir_path_for_output_files',
                      'tradeoff_mission_price_vs_duration',

                      'constellation_name',
                      'n_planes',
                      'n_sats_per_plane',
                      'plane_distribution_angle',

                      'launcher_use_database',
                      'launcher_name',
                      'launcher_launch_site',
                      'launcher_orbit_type',
                      'launcher_perf_interpolation_method',

                      'kickstage_use_database',
                      'kickstage_name',
                      'kickstage_propulsion_type']

    scalable_field = [('sat_mass', u.kg),
                      ('sat_volume', u.m ** 3),

                      ('launcher_performance', u.kg),
                      ('launcher_fairing_diameter', u.m),
                      ('launcher_fairing_cylinder_height', u.m),
                      ('launcher_fairing_total_height', u.m),

                      ('kickstage_height',u.m),
                      ('kickstage_diameter',u.m),
                      ('kickstage_initial_fuel_mass',u.kg),
                      ('kickstage_prop_thrust',u.N),
                      ('kickstage_prop_isp',u.s),
                      ('kickstage_propulsion_dry_mass',u.kg),
                      ('kickstage_dispenser_dry_mass',u.kg),
                      ('kickstage_struct_mass',u.kg),
                      ('kickstage_remaining_fuel_margin',u.kg),
                      
                      ('apogee_launcher_insertion', u.km),
                      ('perigee_launcher_insertion', u.km),
                      ('inc_launcher_insertion', u.deg),
                      ('apogee_kickstage_disposal', u.km),
                      ('perigee_kickstage_disposal', u.km),
                      ('inc_kickstage_disposal', u.deg)]

    # Inits
    def __init__(self,scenario_id,json):    
        # Set identification
        self.id = scenario_id

        # Instanciante Clients, Fleet and Plan
        self.fleet = None
        self.constellation = None

        # Flag
        self.execution_success = False

        # Class attributes
        self.sat_insertion_orbit = None
        self.sat_operational_orbit = None
        self.sat_disposal_orbit = None
        self.sat_default_orbit = None

        self.launcher_insertion_orbit = None
        self.kickstage_disposal_orbit = None

        self.reference_satellite = None

        self.create_attributes_from_input_json(json)

        # Instanciate epoch
        self.starting_epoch = Time(self.starting_epoch, scale="tdb")

        # Enabling logging. Set level >21 to display INFO only
        logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    def create_attributes_from_input_json(self,json):
        """ Create class attributes based on the static fields "general_fields" and "scalable_fields".
        Instantiates these attributes and initilises them with values from inut json file.

        :param json: input json file containing the scenario parameters
        :type json: json
        """
        # Look through general_fields
        for field in self.general_fields:
            # Check if field in file
            if field in json:
                # Add the field as an attribute
                setattr(self, field, json[field])
        
        # Look through scalable_fields
        for (field, unit) in self.scalable_field:
            # Check if field in file
            if field in json:
                # Check if value is defined
                if json[field] is None:
                    setattr(self, field, json[field])
                else:
                    setattr(self, field, json[field] * unit)

    def setup(self,existing_constellation=None):
        """ Create the :class:`~Fleets.Fleet.Fleet` and :class:`~Constellations.Constellation.Constellation` 
        based on json inputs.
        
        Offer the capability of re-using pre-set constellation in case multiple scenario are used. 

        :param existing_constellation: :class:`~Constellations.Constellation.Constellation` that serve as input, defaults to None
        :type existing_constellation: :class:`~Constellations.Constellation.Constellation`, optional
        """
        # Check if existing_clients are provided
        if not existing_constellation:
            logging.info("Start defining Clients...")
            self.define_constellation()
        else:
            logging.info("Recovering Clients...")
            self.constellation = existing_constellation
            self.constellation.reset()
        logging.info("Finish defining Clients...")

        if self.constellation.get_number_satellites() == 0:
            raise Exception("Empty constellation, cannot execute a scenario")

        # Define fleet based on attributes
        logging.info("Start defining Fleet...")
        self.define_fleet()
        logging.info("Finish defining Fleet...")

    def execute(self):
        """ Design the fleet's Plan, execute it and optimises it.

        :return: True of execution was usccessfull
        :rtype: bool
        """
        logging.info("Start executing...")
        try:
            self.fleet.execute(clients=self.constellation)
            logging.info("Finish executing...")
            self.execution_success = True
            return True
        except RuntimeWarning as warning:
            logging.info("Executing failed...")
            self.execution_success = False
            return warning

    def define_constellation(self):
        """ Based on input json, creates the orbits, 
        the :class:`~Constellations.Constellation.Constellation` 
        and fills the latter with :class:`~Spacecrafts.Sattelite.Sattelite` objects. 
        """
        # Define relevant orbits
        logging.info("Gathering satellite orbits...")
        self.define_constellation_orbits()

        # Define a reference satellite
        logging.info("Generating the reference satellite...")
        self.reference_satellite = Satellite('Reference_' + self.constellation_name + '_satellite',
                                             self.sat_mass,
                                             self.sat_volume,
                                             insertion_orbit=self.sat_insertion_orbit,   
                                             operational_orbit=self.sat_operational_orbit,
                                             disposal_orbit=self.sat_disposal_orbit,
                                             state='standby',
                                             default_orbit=self.sat_default_orbit)

        # Instanciate ConstellationSatellites object
        logging.info("Instanciating the constellation...")
        self.constellation = Constellation(self.constellation_name)

        logging.info("Populating the constellation based on the reference satellite...")
        self.constellation.populate_standard_constellation(self.constellation_name,
                                                           self.reference_satellite,
                                                           number_of_planes=self.n_planes,
                                                           sat_per_plane=self.n_sats_per_plane,
                                                           plane_distribution_angle=self.plane_distribution_angle,
                                                           altitude_offset=0 * u.km)

        # Log satellites distribution
        for _, satellite in self.constellation.satellites.items():
            logging.info(f"Sat {satellite.get_id()} has {satellite.get_default_orbit()}, {satellite.get_default_orbit().raan} RAAN, {satellite.get_default_orbit().nu} nu orbit")

    def plot_constellation(self):
        # Plot if verbose
        if self.verbose:
            logging.info("Start plotting Clients...")
            self.constellation.plot_3D_distribution(save="3D_plot", save_folder=self.dir_path_for_output_files)
            self.constellation.plot_distribution(save="2D_plot", save_folder=self.dir_path_for_output_files)
            logging.info("Finish plotting Clients...")

    def define_fleet(self):
        """ Based on input json, define the :class:`~Fleets.Fleet.Fleet`'s orbits,
        create the :class:`~Fleets.Fleet.Fleet` object,
        and organise the targeted :class:`~Constellations.Constellation.Constellation`.
        """
        self.define_kickstage_parameters()

        # Define launcher relevant orbit
        logging.info("Gathering launchers orbits...")
        self.define_fleet_orbits()
        # Define fleet
        logging.info("Instanciate Fleet object...")
        self.create_fleet()

        # Compute optimal order to release once spacecraft is known
        self.organise_satellites()

    def define_kickstage_parameters(self):
        """ If user specifies a kickstage from the database, sets all kickstage parameters from database.
        """
        if self.kickstage_use_database is True:
            ks_db = KickstageDatabaseReader(PATH_DB_KICKSTAGE+KICKSTAGE_DATABASE)
            self.kickstage_height = ks_db.get_kickstage_height(self.kickstage_name)
            self.kickstage_diameter = ks_db.get_kickstage_diameter(self.kickstage_name)
            self.kickstage_initial_fuel_mass = ks_db.get_kickstage_initial_fuel_mass(self.kickstage_name)
            self.kickstage_prop_thrust = ks_db.get_kickstage_prop_thrust(self.kickstage_name)
            self.kickstage_prop_isp = ks_db.get_kickstage_prop_isp(self.kickstage_name)
            self.kickstage_propulsion_dry_mass = ks_db.get_kickstage_prop_dry_mass(self.kickstage_name)
            self.kickstage_dispenser_dry_mass = ks_db.get_kickstage_dispenser_dry_mass(self.kickstage_name)
            self.kickstage_struct_mass = ks_db.get_kickstage_struct_mass(self.kickstage_name)
            self.kickstage_propulsion_type = ks_db.get_kickstage_prop_type(self.kickstage_name)

    def define_constellation_orbits(self):
        """ Define orbits needed for :class:`~Constellations.Constellation.Constellation` and :class:`~Spacecrafts.Satellite.Satellite` definition.

        :raises NotImplementedError: Virtual method
        """
        raise NotImplementedError()

    def define_fleet_orbits(self):
        """ Define the :class:`~Spacecrafts.KickStage.KickStage` orbits based on input json.
        """
        self.define_kickstages_orbits()

    def create_fleet(self):
        """ Create the :class:`~Fleets.Fleet.Fleet` object.

        :raises NotImplementedError: Virtual method
        """
        raise NotImplementedError()

    def define_kickstages_orbits(self):
        """ Define orbits needed for :class:`~Spacecrafts.KickStage.KickStage` definition based on input json.
        """
        # launcher insertion orbit
        a_launcher_insertion_orbit = (self.apogee_launcher_insertion + self.perigee_launcher_insertion)/2 + Earth.R
        e_launcher_insertion_orbit = ((self.apogee_launcher_insertion + Earth.R)/a_launcher_insertion_orbit - 1)*u.one
        self.launcher_insertion_orbit = Orbit.from_classical(Earth,
                                                             a_launcher_insertion_orbit,
                                                             e_launcher_insertion_orbit,
                                                             self.inc_launcher_insertion,
                                                             0. * u.deg,
                                                             90. * u.deg,
                                                             0. * u.deg,
                                                             self.starting_epoch)

        # kickstage disposal orbit
        a_kickstage_disposal_orbit = (self.apogee_kickstage_disposal + self.perigee_kickstage_disposal)/2 + Earth.R
        e_kickstage_disposal_orbit = ((self.apogee_kickstage_disposal + Earth.R)/a_kickstage_disposal_orbit - 1)*u.one
        self.kickstage_disposal_orbit = Orbit.from_classical(Earth,
                                                            a_kickstage_disposal_orbit,
                                                            e_kickstage_disposal_orbit,
                                                            self.inc_kickstage_disposal,
                                                            0. * u.deg,
                                                            90. * u.deg,
                                                            0. * u.deg,
                                                            self.starting_epoch)

    def organise_satellites(self):
        """ Organise :class:`~Spacecrafts.Satellite.Satellite` release order based on :class:`~Scenarios.Scenario.Scenario`.
        """
        # Determine if precession is turning counter-clockwise (1) or clockwise (-1)
        global_precession_direction = self.constellation.get_global_precession_rotation()

        # Extract launcher and satellite precession speeds
        targets_J2_speed = nodal_precession(self.launcher_insertion_orbit)[1]
        launchers_J2_speed = nodal_precession(self.sat_default_orbit)[1]

        # Compute precession direction based on knowledge from Launcher and Servicers
        relative_precession_direction = np.sign(launchers_J2_speed-targets_J2_speed)

        # Order targets by their current raan following precession direction, then by true anomaly
        ordered_satellites_id = sorted(self.constellation.get_standby_satellites(), key=lambda satellite_id: (relative_precession_direction *
                                    self.constellation.get_standby_satellites()[satellite_id].get_default_orbit().raan.value,
                                    self.constellation.get_standby_satellites()[satellite_id].get_default_orbit().nu.value))

        logging.info("Computing 'optimal' deployement sequence ...")
        # For each launcher, find optimal sequence of targets' deployment
        # Extract number of satellites
        number_satellites = self.constellation.get_number_satellites()

        # Instanciate ideal sequence numpy array
        sequence_list = np.full((number_satellites,number_satellites),-1)

        # Built the ideal sequence array
        for sequence_row in range(0,number_satellites):
            sequence_list[sequence_row,:] = np.mod(np.arange(sequence_row,sequence_row+number_satellites,1),number_satellites)

        # After establishing feasible options, compute criterium to prioritize between them
        criteria_raan_spread = []
        criteria_altitude = []
        for i in range(0, len(ordered_satellites_id)):
            # Get targets id
            satellite_id_list = [ordered_satellites_id[i] for i in sequence_list[i, :]]

            # Instanciate raan spread over current sequence
            sequence_raan_spread = 0 * u.deg

            # Iterate through sequence's satellites
            for j in range(1, len(satellite_id_list)):
                # Extract initial target RAAN
                initial_RAAN = self.constellation.satellites[satellite_id_list[j]].get_default_orbit().raan

                # Extract next target RAAN
                final_RAAN = self.constellation.satellites[satellite_id_list[j-1]].get_default_orbit().raan

                # Check for opposite precession movement (Has a larger cost)
                delta_RAAN = final_RAAN-initial_RAAN
                if np.sign(delta_RAAN) != np.sign(global_precession_direction):
                    # Need to circle around globe to reach final RAAN
                    delta_RAAN = -np.sign(delta_RAAN)*(360*u.deg-abs(delta_RAAN))
                
                # Add RAAN spread to sequence's total RAAN spread
                sequence_raan_spread += delta_RAAN


            # Append sequence_raan_spread to global array
            criteria_raan_spread.append(abs(sequence_raan_spread.value))

            # Compute sum of altitudes of all targets, this is used to prioritize sequences with lower targets
            satellites_altitude = sum([self.constellation.satellites[sat_id].get_default_orbit().a.to(u.km).value for sat_id in satellite_id_list])
            criteria_altitude.append(satellites_altitude)

        # Find ideal sequence by merging RAAN and altitude in a table
        ranking = [list(range(0, len(ordered_satellites_id))), criteria_raan_spread, criteria_altitude]
        ranking = np.array(ranking).T.tolist()

        # Sort by RAAN spread (primary) and alitude (secondary)
        ranking = sorted(ranking, key=lambda element: (element[1], element[2]))

        # Extract best sequence
        best_sequence = int(ranking[0][0])

        # Extract and assign satellite to this launcher
        self.constellation.set_optimized_ordered_satellites([self.constellation.satellites[ordered_satellites_id[int(sat_id_in_list)]] for sat_id_in_list in sequence_list[best_sequence, :]])
    
    def print_results(self):
        """ Print results summary in results medium.
        """
        # Print general KPI
        self.print_KPI()
        print("\n")
        # Print general report
        self.print_report()

    def print_report(self):
        # Print flag
        """ Print report.
        """
        print("="*72)
        print("REPORT")
        print("="*72)

        # Print Fleet related report
        self.fleet.print_report()
    
    def print_KPI(self):
        """ Print mission KPI.
        """
        # Print title
        if self.kickstage_use_database and self.launcher_use_database:
            print("Scenario:", self.scenario, "using", self.launcher_name, "launcher(s) and", self.kickstage_name, "kick stage(s).")
        elif self.launcher_use_database:
            print("Scenario:", self.scenario, "using", self.launcher_name, "launcher(s) and custom kick stage(s).")
        elif self.kickstage_use_database:
            print("Scenario:", self.scenario, "using custom launcher(s) and", self.kickstage_name, "kick stage(s).")
        else:
            print("Scenario:", self.scenario, "using custom launcher(s) and custom kick stage(s).")

        # Print flag
        print("="*72)
        print("KPI")
        print("="*72)

        # Print execution success
        if self.execution_success:
            print("Script successfully executed: Yes")
        else:
            print("Script successfully executed: No")

        # Print Fleet related KPI
        self.fleet.print_KPI()
