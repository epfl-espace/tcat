from Spacecrafts.Spacecraft import Spacecraft
from Phases.Common_functions import nodal_precession


class Satellite(Spacecraft):
    """ Satellite consist of an object in an initial orbit that can be moved by servicers.
    The class is initialized by giving the current object mass and orbit at time 0.
    It is added to the Clients class taken as argument during initialization.

    Args:
        satellite_id (str): Standard id. Needs to be unique.
        initial_mass (u.kg): Object mass at time 0.
        insertion_orbit (poliastro.twobody.Orbit): Object orbit after insertion
        operational_orbit (poliastro.twobody.Orbit): Object orbit after orbit raising
        state (str): descriptor of the satellite state, used to identify different possible failures and states

    Attributes:
        ID (str): Standard id. Needs to be unique.
        initial_mass (u.kg): Object mass at time 0.
        volume (u.m^3): Volume of the satellite
        initial_orbit (poliastro.twobody.Orbit): Initial orbit of the satellite
        insertion_orbit (poliastro.twobody.Orbit): Object orbit after insertion
        operational_orbit (poliastro.twobody.Orbit): Object orbit after orbit raising
        current_orbit (poliastro.twobody.Orbit): Object orbit at current time.
        current_mass (u.kg): Object mass at current time.
        state (str): descriptor of the satellite state, used to identify different possible failures and states
    """
    def __init__(self, satellite_id, initial_mass, volume, insertion_orbit, operational_orbit, state, is_stackable=False):
        super().__init__(satellite_id, initial_mass, volume, insertion_orbit, operational_orbit)
        self.state = state

    def reset(self):
        """ Reset the current satellite orbit and mass to the parameters given during initialization.
            This function is used to reset the state and orbits of the target after a simulation.
        """
        super().reset()
        self.state = "standby"

    def __str__(self):
        return self.ID