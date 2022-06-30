"""
Created:        28.06.2022
Last Revision:  28.06.2022
Author:         Malo Goury
Description:    Scenario for constellation deployment
"""

# Import Class
from Scenarios.Scenario import *
from Fleets.FleetConstellation import FleetConstellation

# Class definition
class ScenarioConstellation(Scenario):
    def __init__(self, scenario_id, json):
        self.general_fields.extend([])
        self.scalable_field.extend([('apogee_sats_insertion', u.km),
                                    ('perigee_sats_insertion', u.km), 
                                    ('inc_sats_insertion', u.deg)])
        super().__init__(scenario_id, json)

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

        self.sat_operational_orbit = None
        self.sat_disposal_orbit = None
        self.sat_default_orbit = self.sat_insertion_orbit
    
    def create_fleet(self):
        self.fleet = FleetConstellation('UpperStages',self)

    def log_constellation_data(self):
        # Log satellites distribution
        for _, satellite in self.constellation.satellites.items():
            logging.info(f"Sat {satellite.get_id()} has {satellite.inse_orbit}, {satellite.inse_orbit.raan} RAAN, {satellite.inse_orbit.nu} nu orbit")