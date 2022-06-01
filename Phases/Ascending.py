from astropy import units as u

from Phases.GenericPhase import GenericPhase


class Ascending(GenericPhase):


    def __init__(self, phase_id, plan, orbit, duration=1. * u.day, delta_v=2000. * u.m / u.s, contingency=0.1):
        super().__init__(phase_id, plan)
        self.orbit = orbit
        self.duration = duration
        self.delta_v = delta_v
        self.contingency = contingency

    def apply(self):
        """ Asks the propulsion module to consume propellant according to delta v.
        Calls generic function to update orbit raan and epoch.
        """
        # self.get_assigned_spacecraft().change_orbit(self.orbit)
        self.get_assigned_module().apply_delta_v(self.delta_v * (1 + self.contingency), 'phasing')
        self.update_spacecraft()


    def __str__(self):
        return ('--- \nAscending: ' + super().__str__()
                + '\n\tDelta V ' + str(self.delta_v))
