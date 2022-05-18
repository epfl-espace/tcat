"""
Created:        17.05.2022
Last Revision:  -
Author:         Emilien Mingard
Description:    Constellation dedicated Scenario Class
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
class ScenarioConstellation():
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
                      ('a_sats_insertion', u.km),
                      ('ecc_sats_insertion', u.one), 
                      ('inc_sats_insertion', u.deg),
                      ('a_sats_operational', u.km),
                      ('ecc_sats_operational', u.one),
                      ('inc_sats_operational', u.deg),
                      ('a_launcher_insertion', u.km),
                      ('ecc_launcher_insertion', u.one),
                      ('inc_launcher_insertion', u.deg)]

    """
    Init
    """
    def __init__(self,scenario_id,config_file):
        # Set identification
        self.ID = scenario_id

        # Instanciante Clients, Fleet and Plan
        self.clients = None
        self.fleet = None
        self.plan = None

        # TO BE REMOVED
        # Instanciate reference values
        #self.ref_disp_volume = 0. * u.m ** 3
        #self.ref_disp_mass = 0. * u.kg
        #self.number_of_servicers = 0
        # TO BE REMOVED

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

        # TO BE REMOVED
        # Compute launcher orbits
        #self.define_servicers_orbits()
        #semimajor_axis = self.define_servicers_orbits().a.value
        #self.apogee_h = (1 + self.define_servicers_orbits().ecc.value) * semimajor_axis - Earth.R.to(u.km).value
        #self.perigee_h = 2 * semimajor_axis - self.apogee_h - 2 * Earth.R.to(u.km).value
        #self.inclination = self.define_servicers_orbits().inc.value
        # TO BE REMOVED

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
        #self.define_fleet()
        logging.info("Finish defining Fleet...")

        # Define plan based on attributes
        logging.info("Start defining Plan...")
        #self.define_plan()
        logging.info("Finish defining Plan...")

    def execute(self):
        print("TODO")

    def define_constellation(self):
        """ Define clients object.
        Given arguments can specify the reliability to use as input for reliability model.

        Args:
            reliability (float): (optional) satellite reliability at end of life

        Return:
            (ADRClient_module.ADRClients): created clients
        """

        # Define relevant orbits
        logging.info("Gathering satellite orbits...")
        self.define_constellation_orbits()

        # Check if satellites volume is known, otherwise an estimate is provided
        if int(self.sat_volume.value) == 0:
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
            self.satellites.plot_3D_distribution(save="3D_plot", save_folder=self.data_path)
            self.satellites.plot_distribution(save="2D_plot", save_folder=self.data_path)
            logging.info("Finish plotting Clients...")
        
    def estimate_satellite_volume(self):
        """ Estimate the satellite volume based on mass

        Return:
            (u.m3): Satellite volume
        """
        # Estimate volume based on satellite mass
        self.sat_volume = 9 * 10 ** -9 * self.sat_mass ** 3 - 10 ** -6 * self.sat_mass ** 2 + 0.0028 * self.sat_mass

    def define_constellation_orbits(self):
        """ Define orbits needed for satellites definition.

        Return:
            (poliastro.twobody.Orbit): target operational orbit
        """
        # Satellites insertion orbit
        self.sat_insertion_orbit = Orbit.from_classical(Earth, self.a_sats_insertion + Earth.R,
                                                        self.ecc_sats_insertion,
                                                        self.inc_sats_insertion,
                                                        0. * u.deg,
                                                        90. * u.deg,
                                                        0. * u.deg,
                                                        self.starting_epoch)
        # Satellites operational orbit
        self.sat_operational_orbit = Orbit.from_classical(Earth, self.a_sats_operational + Earth.R,
                                                          self.ecc_sats_operational,
                                                          self.inc_sats_operational,
                                                          0. * u.deg,
                                                          90. * u.deg,
                                                          0. * u.deg,
                                                          self.starting_epoch)

    def define_launchers_orbits(self):
        """ Define orbits needed for launchers definition.

        Return:
            (poliastro.twobody.Orbit): launchers insertion orbit
        """
        # launcher insertion orbit
        launcher_insertion_orbit = Orbit.from_classical(Earth, self.a_launcher_insertion + Earth.R, self.ecc_launcher_insertion,
                                                        self.inc_launcher_insertion, 0. * u.deg, 90. * u.deg,
                                                        0. * u.deg,
                                                        self.starting_epoch)
        return launcher_insertion_orbit