from Spacecrafts.Spacecraft import Spacecraft
from Phases.Common_functions import nodal_precession


class Satellite(Spacecraft):
    """ Satellite acts as a child Class to describe passive satellite such as constellation satellites.

    :param satellite_id: Satellite identification name
    :type satellite_id: str
    :param initial_mass: Satellite initial mass
    :type initial_mass: u*kg
    :param volume: Satellite volume
    :type volume: u*m**3
    :param insertion_orbit: Insertion orbit
    :type insertion_orbit: poliastro.twobody.Orbit
    :param operational_orbit: Operational orbit
    :type operational_orbit: poliastro.twobody.Orbit
    :param disposal_orbit: Disposal orbit
    :type disposal_orbit: poliastro.twobody.Orbit
    :param state: Spacecraft actual state
    :type state: str
    :param default_orbit: Initial orbit
    :type default_orbit: poliastro.twobody.Orbit
    """
    def __init__(self, satellite_id, initial_mass, volume, insertion_orbit=None, operational_orbit=None, disposal_orbit=None, state="standby", default_orbit=None):
        super().__init__(satellite_id,initial_mass, volume,insertion_orbit=insertion_orbit,operational_orbit=operational_orbit, disposal_orbit=disposal_orbit,state=state)
        self.default_orbit = default_orbit

    def get_default_orbit(self):
        """ Get the satellite default orbit

        :return: default orbit
        :rtype: poliastro.twobody.Orbit
        """
        return self.default_orbit

    def set_default_orbit(self,orbit):
        """ Set the default orbit

        :param orbit: new default orbit
        :type orbit: poliastro.twobody.Orbit
        """
        self.default_orbit = orbit