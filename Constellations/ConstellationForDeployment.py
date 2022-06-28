"""
Created:        ?
Last Revision:  23.05.2022
Author:         Malo Goury
Description:    Constellation class definitions
"""
# Import Classes
from Constellations.Constellation import *

class ConstellationForDeployment(Constellation):
    def __init__(self, constellation_id):
        super().__init__(constellation_id)

    def populate_standard_constellation(self, constellation_name, reference_satellite, number_of_planes=2, sat_per_plane=10, plane_distribution_angle=180, altitude_offset = 10*u.km):
        """ Adds satellites to form a complete constellation with equi-phased planes based on inputs.
            The reference satellite is duplicated to fill the planes.

        Args:
            plane_distribution_angle (int): Angle over which to distribute the RAAN of the orbital planes. Generally
                                            180° for constellations composed of polar orbits and 360° for the others.
            constellation_name (str): constellation name as provided by input json
            reference_satellite (ConstellationSatellites.Satellite): target that is duplicated to create constellation members
            number_of_planes (int): number of planes for the constellation, equiphased along 180° of raan
            altitude_offset (u.km): ?
            sat_per_plane (int): number of satellites on each plane, equiphased along 360° of anomaly
        """
        super().populate_standard_constellation(constellation_name, reference_satellite, number_of_planes, sat_per_plane, plane_distribution_angle, altitude_offset)
        self.init_sats_initial_orbit()

    def init_sats_initial_orbit(self):
        """ Instantiate all satellites' initial orbit to the insertion orbit.
        """
        for _, satellite in self.satellites.items():
            satellite.initial_orbit = satellite.insertion_orbit