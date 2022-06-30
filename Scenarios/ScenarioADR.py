"""
Created:        28.06.2022
Last Revision:  28.06.2022
Author:         Malo Goury
Description:    Scenario for constellation deployment
"""

# Import Class
from Scenarios.Scenario import *
from Fleets.FleetADR import FleetADR

# Class definition
class ScenarioADR(Scenario):
    def __init__(self, scenario_id, json):
        self.general_fields.extend(['sats_reliability',
                                    'seed_random_sats_failure',
                                    'architecture'])
        self.scalable_field.extend([('apogee_sats_operational', u.km),
                                    ('perigee_sats_operational', u.km), 
                                    ('inc_sats_operational', u.deg),
                                    ('apogee_sats_disposal', u.km),
                                    ('perigee_sats_disposal', u.km), 
                                    ('inc_sats_disposal', u.deg),
                                    ('apogee_servicer_insertion',u.km),
                                    ('perigee_servicer_insertion',u.km),
                                    ('inc_servicer_insertion', u.deg),
                                    ('raan_servicer_insertion', u.deg),
                                    ('arg_periapsis_servicer_insertion', u.deg),
                                    ('true_anomaly_servicer_insertion', u.deg),
                                    ('apogee_servicer_disposal',u.km),
                                    ('perigee_servicer_disposal',u.km),
                                    ('inc_servicer_disposal', u.deg)])
        super().__init__(scenario_id, json)
        self.servicer_insertion_orbit = None
        self.servicer_disposal_orbit = None

    def define_constellation_orbits(self):
        """ Define orbits needed for constellation and satellites definition.
        """
        self.sat_insertion_orbit = None

        a_sats_operational_orbit = (self.apogee_sats_operational + self.perigee_sats_operational)/2 + Earth.R
        e_sats_operational_orbit = ((self.apogee_sats_operational + Earth.R)/a_sats_operational_orbit - 1)*u.one
        self.sat_operational_orbit = Orbit.from_classical(Earth,
                                                        a_sats_operational_orbit,
                                                        e_sats_operational_orbit,
                                                        self.inc_sats_operational,
                                                        self.raan_servicer_insertion,
                                                        self.arg_periapsis_servicer_insertion,
                                                        self.true_anomaly_servicer_insertion,
                                                        self.starting_epoch)
        
        a_sats_disposal_orbit = (self.apogee_sats_disposal + self.perigee_sats_disposal)/2 + Earth.R
        e_sats_disposal_orbit = ((self.apogee_sats_disposal + Earth.R)/a_sats_disposal_orbit - 1)*u.one
        self.sat_disposal_orbit = Orbit.from_classical(Earth,
                                                        a_sats_disposal_orbit,
                                                        e_sats_disposal_orbit,
                                                        self.inc_sats_disposal,
                                                        0. * u.deg,
                                                        90. * u.deg,
                                                        0. * u.deg,
                                                        self.starting_epoch)
        self.sat_default_orbit = self.sat_operational_orbit

    def define_fleet_orbits(self):
        super().define_fleet_orbits()
        self.define_servicer_orbits()

    def define_servicer_orbits(self):
        a_servicer_insertion_orbit = (self.apogee_servicer_insertion + self.perigee_servicer_insertion)/2 + Earth.R
        e_servicer_insertion_orbit = ((self.apogee_servicer_insertion + Earth.R)/a_servicer_insertion_orbit - 1)*u.one
        self.servicer_insertion_orbit = Orbit.from_classical(Earth,
                                                             a_servicer_insertion_orbit,
                                                             e_servicer_insertion_orbit,
                                                             self.inc_servicer_insertion,
                                                             0. * u.deg,
                                                             90. * u.deg,
                                                             0. * u.deg,
                                                             self.starting_epoch)

        # launcher disposal orbit
        a_servicer_disposal_orbit = (self.apogee_servicer_disposal + self.perigee_servicer_disposal)/2 + Earth.R
        e_servicer_disposal_orbit = ((self.apogee_servicer_disposal + Earth.R)/a_servicer_disposal_orbit - 1)*u.one
        self.servicer_disposal_orbit = Orbit.from_classical(Earth,
                                                            a_servicer_disposal_orbit,
                                                            e_servicer_disposal_orbit,
                                                            self.inc_servicer_disposal,
                                                            0. * u.deg,
                                                            90. * u.deg,
                                                            0. * u.deg,
                                                            self.starting_epoch)
    
    def create_fleet(self):
        self.fleet = FleetADR('UpperStages',self)

