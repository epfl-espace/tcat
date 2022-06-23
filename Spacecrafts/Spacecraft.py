"""
Created:        23.06.2022
Last Revision:  23.06.2022
Author:         Emilien Mingard
Description:    Base class of the Spacecrafts modules
"""

# Import methods
from Phases.Common_functions import nodal_precession

# Class definition
class Spacecraft:
    """
    Parent class of all Spacecrafts modules.
    """

    """
    Init
    """
    def __init__(self, spacecraft_id, dry_mass, volume=0.):
        self.id = spacecraft_id

        self.dry_mass = dry_mass
        self.initial_volume = volume

        self.current_mass = dry_mass
        self.current_volume = volume

        self.insertion_orbit = None
        self.initial_orbit = None
        self.operational_orbit = None
        self.current_orbit = None
        self.previous_orbit = None

        self.mothership = None

    def get_id(self):
        """ Get the spacecraft's id
        
        Returns:
            (str): id of the spacecraft
        """
        return self.id

    def get_current_mass(self):
        """ Get the current satellite mass.

        Returns:
            (u.kg): current mass
        """
        return self.current_mass

    def get_initial_volume(self):
        """ Get the satellite initial volume.

        Returns:
                (u.m**3): volume
        """
        return self.initial_volume

    def get_current_volume(self):
        """ Get the satellite current volume.

        Returns:
                (u.m**3): volume
        """
        return self.current_volume

    def get_volume(self):
        """ Alias for get_current_volume()

        Returns:
                (u.m**3): volume
        """
        return self.get_current_volume()

    def get_initial_mass(self):
        """ Get the initial satellite mass.

        Returns:
            (u.kg): initial mass
        """
        return self.initial_mass

    def get_current_orbit(self):
        """ Get the current orbit

        Returns:
            (poliastro.twobody.Orbit): current orbit
        """
        return self.current_orbit

    def get_initial_orbit(self):
        """ Get the initial orbit

        Returns:
            (poliastro.twobody.Orbit): current orbit
        """
        return self.initial_orbit

    def get_insertion_orbit(self):
        """ Get the insertion orbit

        Returns:
            (poliastro.twobody.Orbit): current orbit
        """
        return self.insertion_orbit

    def get_relative_raan_drift(self, duration, own_orbit=None, other_object_orbit=None):
        """ Returns the relative raan drift between the target and an hypothetical servicer.
            Used for planning purposes, to make sure phasing is feasible with current raan.

        Args:
            duration (u.<time unit>): duration after which to compute relative raan drift
            own_orbit (poliastro.twobody.Orbit): orbit of the target,
                                                    by default the target operational orbit
            other_object_orbit (poliastro.twobody.Orbit): orbit of the other object,
                                                            by default the target insertion orbit
        Return:
            (u.deg): relative raan drift after duration from current orbits
        """
        if not own_orbit:
            own_orbit = self.operational_orbit
        _, own_nodal_precession_speed = nodal_precession(own_orbit)
        _, other_nodal_precession_speed = nodal_precession(other_object_orbit)
        delta_nodal_precession_speed = own_nodal_precession_speed - other_nodal_precession_speed
        return (delta_nodal_precession_speed * duration).decompose()

    def reset(self):
        """ Reset the current satellite orbit and mass to the parameters given during initialization.
            This function is used to reset the state and orbits of the target after a simulation.
        """
        self.current_mass = self.initial_mass
        self.current_orbit = self.initial_orbit
        self.state = "standby"

    def __str__(self):
        return self.get_id()