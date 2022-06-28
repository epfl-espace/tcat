"""
Created:        28.06.2022
Last Revision:  28.06.2022
Author:         Malo Goury
Description:    Constellation for deployment class definitions
"""
# Import Classes
from Constellations.Constellation import *

class ConstellationForDeployment(Constellation):
    def __init__(self, constellation_id):
        super().__init__(constellation_id)

    def populate_standard_constellation(self, constellation_name, reference_satellite, number_of_planes=2, sat_per_plane=10, plane_distribution_angle=180, altitude_offset = 10*u.km):
        super().populate_standard_constellation(constellation_name, reference_satellite, number_of_planes, sat_per_plane, plane_distribution_angle, altitude_offset)
        self.init_sats_initial_orbit()

    def init_sats_initial_orbit(self):
        """ Instantiate all satellites' initial orbit to the insertion orbit.
        """
        for _, satellite in self.satellites.items():
            satellite.initial_orbit = satellite.insertion_orbit