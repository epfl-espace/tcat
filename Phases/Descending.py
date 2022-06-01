from astropy import units as u
from poliastro.twobody.orbit import Orbit
from Phases.GenericPhase import GenericPhase
from poliastro.bodies import Moon
from astropy.coordinates import solar_system_ephemeris


class Descending(GenericPhase):

    def __init__(self, phase_id, plan, orbit=None, duration=1. * u.day, delta_v=2400. * u.m / u.s, contingency=0.1):
        super().__init__(phase_id, plan)
        self.orbit = orbit
        self.duration = duration
        self.delta_v = delta_v
        self.contingency = contingency

    def apply(self):
        """ Asks the propulsion module to consume propellant according to delta v.
        Calls generic function to update orbit raan and epoch.
        """
        # When the servicer performs landing, its orbit is coincident with the Moon's
        solar_system_ephemeris.set('jpl')
        EPOCH = self.get_assigned_spacecraft().current_orbit.epoch
        orbit = Orbit.from_body_ephem(Moon, EPOCH)

        self.get_assigned_spacecraft().change_orbit(orbit)
        self.get_assigned_module().apply_delta_v(self.delta_v * (1 + self.contingency), 'phasing')
        self.update_spacecraft()

    def __str__(self):
        return ('--- \nDescending: ' + super().__str__()
                + '\n\tDelta V ' + str(self.delta_v))
