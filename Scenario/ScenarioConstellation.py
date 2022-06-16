"""
Created:        17.05.2022
Last Revision:  23.05.2022
Author:         Emilien Mingard
Description:    Constellation dedicated Scenario Class definition
"""

# Import Class
from Scenario.ConstellationSatellites import Constellation,Satellite
from Scenario.Fleet_module import *
from Scenario.Plan_module import *

# Import Libraries
from json import load as load_json

# Set logging
logging.getLogger('numba').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.addLevelName(21, "DEBUGGING")

# Class definition
class ScenarioConstellation:
    """
    General Attributs
    """
    general_fields = ['architecture',
                      'propulsion_type',
                      'deployment_strategy',
                      'verbose',
                      'constellation_name',
                      'n_planes',
                      'n_sats_per_plane',
                      'plane_distribution_angle',
                      'n_sats_simultaneously_deployed',
                      'launcher',
                      'launch_site',
                      'orbit_type',
                      'dispenser_tech_level',
                      'custom_launcher_name',
                      'interpolation_method',
                      'starting_epoch',
                      'data_path']

    scalable_field = [('sat_mass', u.kg),
                      ('sat_volume', u.m ** 3),
                      ('custom_launcher_performance', u.kg),
                      ('fairing_diameter', u.m),
                      ('fairing_cylinder_height', u.m),
                      ('fairing_total_height', u.m),
                      ('apogee_sats_insertion', u.km),
                      ('perigee_sats_insertion', u.km), 
                      ('inc_sats_insertion', u.deg),
                      ('apogee_sats_operational', u.km),
                      ('perigee_sats_operational', u.km),
                      ('inc_sats_operational', u.deg),
                      ('apogee_launcher_insertion', u.km),
                      ('perigee_launcher_insertion', u.km),
                      ('inc_launcher_insertion', u.deg),
                      ('apogee_launcher_disposal', u.km),
                      ('perigee_launcher_disposal', u.km),
                      ('inc_launcher_disposal', u.deg)]

    """
    Init
    """
    def __init__(self,scenario_id,config_file):
        # Set identification
        self.id = scenario_id

        # Instanciante Clients, Fleet and Plan
        self.clients = None
        self.fleet = None
        self.plan = None

        # Flag
        self.execution_success = False

        # Load json configuration file
        with open(config_file) as file:
            json = load_json(file)

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

        # Instanciate epoch
        self.starting_epoch = Time(self.starting_epoch, scale="tdb")

        # Enabling logging. Set level >21 to display INFO only
        logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    """
    Methods
    """
    def setup(self,existing_constellation=None):
        """ Create the clients, fleet and plan based on json inputs files (Provided through Class attributs).
            Off the capability of re-using pre-set constellation in case multiple scenario are used. The existing client can be
            provided by another scenario

        Args:
            existing_constellation (Constellation_Client_Module.ConstellationClients): (optional) clients that serve as input; re-generated if not given
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

        # Define fleet based on attributes
        logging.info("Start defining Fleet...")
        self.define_fleet()
        logging.info("Finish defining Fleet...")

        # Define plan based on attributes
        logging.info("Start defining Plan...")
        self.define_plan()
        logging.info("Finish defining Plan...")

    def execute(self):
        """ Execute the scenario until the fleet converges using a method from the fleet class.
        """
        logging.info("Start executing...")
        try:
            self.fleet.design_constellation(self.plan, verbose=False)
            logging.info("Finish executing...")
            self.execution_success = True
            return True
        except RuntimeWarning as warning:
            logging.info("Executing failed...")
            self.execution_success = False
            return warning

    def define_constellation(self):
        """ Define constellation object.
        """
        # Define relevant orbits
        logging.info("Gathering satellite orbits...")
        self.define_constellation_orbits()

        # Check if satellites volume is known, otherwise an estimate is provided
        if float(self.sat_volume.value) == 0:
            logging.info("Estimating satellite volume...")
            self.estimate_satellite_volume()

        # Define a reference satellite
        logging.info("Generating the reference satellite...")
        self.reference_satellite = Satellite('Reference_' + self.constellation_name + '_satellite',
                                             self.sat_mass,
                                             self.sat_volume,
                                             self.sat_insertion_orbit,
                                             self.sat_operational_orbit,
                                             state='standby',
                                             is_stackable=False)

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
            logging.info(f"Sat {satellite.ID} has {satellite.insertion_orbit}, {satellite.insertion_orbit.raan} RAAN, {satellite.insertion_orbit.nu} nu orbit")

        # Plot if verbose
        if self.verbose:
            logging.info("Start plotting Clients...")
            self.constellation.plot_3D_distribution(save="3D_plot", save_folder=self.data_path)
            self.constellation.plot_distribution(save="2D_plot", save_folder=self.data_path)
            logging.info("Finish plotting Clients...")

    def define_fleet(self):
        """ Define fleet object.
        """
        # Compute total number of satellites
        satellites_left = self.constellation.get_number_satellites()

        # Define launcher relevant orbit
        logging.info("Gathering launchers orbits...")
        self.define_upperstages_orbits()

        # Define launch vehicle based on specified launcher
        if self.custom_launcher_name is None:
            self.launcher_name = self.launcher
        else:
            self.launcher_name = self.custom_launcher_name

        # Define fleet
        self.fleet = Fleet('UpperStages', self.architecture)

        # Assign satellite to launcher as long as satellite are left without launch vehicle
        index = 0
        while satellites_left > 0:
            # Check for architecture compatibility
            if self.architecture == 'upperstage':
                # Create launcher id based on index
                upperstage_id = 'UpperStage_' + '{:04d}'.format(index)
                logging.info(f"Instanciating {upperstage_id}...")

                # Create a new launch vehicle
                temp_upperstage, serviced_sats = self.create_upperstage_spacecraft(upperstage_id,satellites_left)

                # Update number of left satellite
                satellites_left -= serviced_sats

                # Add latest UpperStage to the fleet
                self.fleet.add_upperstage(temp_upperstage)
                index += 1

                # Update the number of servicers during convergence
                self.number_of_servicers = self.fleet.get_number_upperstages()

            else:
                raise Exception('Unknown architecture {}'.format(self.architecture))

    def define_plan(self):
        """ Define plan according to constellation and fleet.
        """
        # Instanciate Plan object
        self.plan = Plan('Plan', self.starting_epoch)

        # Assign targets to UpperStage
        self.assign_satellites()

        # Check for available satellite to deploy
        self.fleet.define_fleet_mission_profile(self)

    def create_upperstage_spacecraft(self,upperstage_id,serviceable_sats_left):
        """ Create an upperstage.

        Args:
            upperstage_id (str): id of the launcher to be created
            serviceable_sats_left (int): remaining satellites to be serviced

        Return:
            (Fleet_module.UpperStage): created launcher
        """

        # Instanciate a reference launch vehicle and set it up
        reference_launch_vehicle = UpperStage(upperstage_id,self,mass_contingency=0.0)
        reference_launch_vehicle.setup(self)

        logging.info(f"Converging the number of satellites manifested in the Launch Vehicle...")
        serviced_sats, _, self.ref_disp_mass, self.ref_disp_volume = reference_launch_vehicle.converge_launch_vehicle(self.reference_satellite,serviceable_sats_left,tech_level=self.dispenser_tech_level)

        # Instanciate Capture and Propulsion modules
        reference_dispenser = CaptureModule(upperstage_id + '_dispenser',
                                            reference_launch_vehicle,
                                            mass_contingency=0.0,
                                            dry_mass_override=self.ref_disp_mass)

        # TOFIX: the initial mass of propellant in Propulsion Module is set to 0 kg. 
        # It is further used to compute the wet mass of launcher.
        # Therefore, the mission the launcher's mass becomes negative while it burns propellant.
        # Remark: in execute() method, it seems like the converge() method should take care of estimating 
        # required prop. mass. Looks like it doesn't do the job....
        reference_phasing_propulsion = PropulsionModule(upperstage_id + '_phasing_propulsion',
                                                        reference_launch_vehicle, 'bi-propellant', 294000 * u.N, ### FLAG ATTENTION ###
                                                        294000 * u.N, 330 * u.s, 0. * u.kg,
                                                        5000 * u.kg, reference_power_override=0 * u.W,
                                                        propellant_contingency=0.05, dry_mass_override=0 * u.kg,
                                                        mass_contingency=0.2)

        # Define modules
        reference_dispenser.define_as_capture_default()
        reference_phasing_propulsion.define_as_main_propulsion()

        # Return UpperStage and number of serviced sats
        return reference_launch_vehicle, serviced_sats

    def estimate_satellite_volume(self):
        """ Estimate the reference satellite volume based on mass
        """
        # Estimate volume based on satellite mass
        self.sat_volume = 9 * 10 ** -9 * self.sat_mass ** 3 - 10 ** -6 * self.sat_mass ** 2 + 0.0028 * self.sat_mass

    def define_constellation_orbits(self):
        """ Define orbits needed for constellation and satellites definition.
        """
        # Satellites insertion orbit
        a_sats_insertion_orbit = (self.apogee_sats_insertion + self.perigee_sats_insertion)/2 + Earth.R
        e_sats_insertion_orbit = ((self.apogee_sats_insertion + Earth.R)/a_sats_insertion_orbit - 1)*u.one
        self.sat_insertion_orbit = Orbit.from_classical(Earth,
                                                        a_sats_insertion_orbit,
                                                        e_sats_insertion_orbit,
                                                        self.inc_sats_insertion,
                                                        0. * u.deg,
                                                        90. * u.deg,
                                                        0. * u.deg,
                                                        self.starting_epoch)

        # Satellites operational orbit
        a_sats_operational_orbit = (self.apogee_sats_operational + self.perigee_sats_operational)/2 + Earth.R
        e_sats_operational_orbit = ((self.apogee_sats_operational + Earth.R)/a_sats_operational_orbit - 1)*u.one
        self.sat_operational_orbit = Orbit.from_classical(Earth, 
                                                          a_sats_operational_orbit,
                                                          e_sats_operational_orbit,
                                                          self.inc_sats_operational,
                                                          0. * u.deg,
                                                          90. * u.deg,
                                                          0. * u.deg,
                                                          self.starting_epoch)

    def define_upperstages_orbits(self):
        """ Define orbits needed for upperstages definition.
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

        # launcher disposal orbit
        a_launcher_disposal_orbit = (self.apogee_launcher_disposal + self.perigee_launcher_disposal)/2 + Earth.R
        e_launcher_disposal_orbit = ((self.apogee_launcher_disposal + Earth.R)/a_launcher_disposal_orbit - 1)*u.one
        self.launcher_disposal_orbit = Orbit.from_classical(Earth,
                                                            a_launcher_disposal_orbit,
                                                            e_launcher_disposal_orbit,
                                                            self.inc_launcher_disposal,
                                                            0. * u.deg,
                                                            90. * u.deg,
                                                            0. * u.deg,
                                                            self.starting_epoch)

    def assign_satellites(self):
        """Function that creates a plan based on an architecture, clients and fleet.
        """
        # Determine if precession is turning counter-clockwise (1) or clockwise (-1)
        global_precession_direction = self.constellation.get_global_precession_rotation()

        # Extract launcher and satellite precession speeds
        targets_J2_speed = nodal_precession(self.launcher_insertion_orbit)[1]
        launchers_J2_speed = nodal_precession(self.sat_insertion_orbit)[1]

        # Compute precession direction based on knowledge from Launcher and Servicers
        relative_precession_direction = np.sign(launchers_J2_speed-targets_J2_speed)

        # Order targets by their current raan following precession direction, then by true anomaly
        ordered_satellites_id = sorted(self.constellation.get_standby_satellites(), key=lambda satellite_id: (relative_precession_direction *
                                    self.constellation.get_standby_satellites()[satellite_id].operational_orbit.raan.value,
                                    self.constellation.get_standby_satellites()[satellite_id].operational_orbit.nu.value))

        logging.info("Finding 'optimal' sequence of target deployment...")
        # For each launcher, find optimal sequence of targets' deployment
        for _, launcher in self.fleet.get_launchers_from_group('launcher').items():
            # Extract number of satellites
            number_satellites = self.constellation.get_number_satellites()

            # Instanciate ideal sequence numpy array
            sequence_list = np.full((number_satellites,min(launcher.sats_number,number_satellites)),-1)

            # Built the ideal sequence array
            for sequence_row in range(0,number_satellites):
                sequence_list[sequence_row,:] = np.mod(np.arange(sequence_row,sequence_row+launcher.sats_number,1),launcher.sats_number)

            # After establishing feasible options, compute criterium to prioritize between them
            criteria_raan_spread = []
            criteria_altitude = []
            for i in range(0, len(ordered_satellites_id)):
                # Get targets id
                satellite_id_list = [ordered_satellites_id[i] for i in sequence_list[i, :]]
                logging.log(21,f"List of targets' ID: {satellite_id_list}")

                # Instanciate raan spread over current sequence
                sequence_raan_spread = 0 * u.deg

                # Iterate through sequence's satellites
                for j in range(1, len(satellite_id_list)):
                    # Extract initial target RAAN
                    initial_RAAN = self.constellation.satellites[satellite_id_list[j]].insertion_orbit.raan
                    logging.log(21,f"1: RAAN {initial_RAAN}°")

                    # Extract next target RAAN
                    final_RAAN = self.constellation.satellites[satellite_id_list[j-1]].insertion_orbit.raan
                    logging.log(21,f"2: RAAN {final_RAAN}°")

                    # Check for opposite precession movement (Has a larger cost)
                    delta_RAAN = final_RAAN-initial_RAAN
                    if np.sign(delta_RAAN) != np.sign(global_precession_direction):
                        # Need to circle around globe to reach final RAAN
                        delta_RAAN = -np.sign(delta_RAAN)*(360*u.deg-abs(delta_RAAN))
                    
                    # Add RAAN spread to sequence's total RAAN spread
                    sequence_raan_spread += delta_RAAN

                logging.log(21,f"Total RAAN spread over sequence {i}: {sequence_raan_spread}°")

                # Append sequence_raan_spread to global array
                criteria_raan_spread.append(abs(sequence_raan_spread.value))

                # Compute sum of altitudes of all targets, this is used to prioritize sequences with lower targets
                satellites_altitude = sum([self.constellation.satellites[sat_id].operational_orbit.a.to(u.km).value for sat_id in satellite_id_list])
                criteria_altitude.append(satellites_altitude)
                logging.log(21,f"Total altitude over sequence {i}: {satellites_altitude}")

            # Find ideal sequence by merging RAAN and altitude in a table
            ranking = [list(range(0, len(ordered_satellites_id))), criteria_raan_spread, criteria_altitude]
            ranking = np.array(ranking).T.tolist()

            # Sort by RAAN spread (primary) and alitude (secondary)
            ranking = sorted(ranking, key=lambda element: (element[1], element[2]))

            # Extract best sequence
            best_sequence = int(ranking[0][0])

            # Extract and assign satellite to this launcher
            satellites_assigned_to_launcher = [self.constellation.satellites[ordered_satellites_id[int(sat_id_in_list)]] for sat_id_in_list in sequence_list[best_sequence, :]]
            launcher.assign_sats(satellites_assigned_to_launcher)

            # Remove from ordered targets
            for satellite in satellites_assigned_to_launcher: ### FLAG USELESS? ###
                ordered_satellites_id.remove(satellite.ID)

            satellites_assigned_to_launcher.clear() ### FLAG USELESS? ###
    
    def print_results(self):
        """ Print results summary in results medium"""
        # Print general report
        self.print_report()

        # Print general KPI
        self.print_KPI()

    def print_report(self):
        # Print flag
        """ Print report """
        print("="*72)
        print("REPORT")
        print("="*72)

        # Print Plan related report
        self.plan.print_report()

        # Print Fleet related report
        self.fleet.print_report()
    
    def print_KPI(self):
        """ Print mission KPI"""
        # Print flag
        print("\n"*3+"="*72)
        print("KPI")
        print("="*72)

        # Print execution success
        if self.execution_success:
            print("Script succesfully executed: Yes")
        else:
            print("Script succesfully executed: No")
        
        # Print Plan related KPI
        self.plan.print_KPI()

        # Print Fleet related KPI
        self.fleet.print_KPI()

        # Print Constellation related KPI
        self.constellation.print_KPI()
