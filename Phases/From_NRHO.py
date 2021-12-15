from astropy import units as u

from Phases.GenericPhase import GenericPhase

from poliastro.twobody import Orbit
class From_NRHO(GenericPhase):
    """
    Maneuver accomplished to go from a Lunar Transfer Orbit to a Near Rectilinear Halo Orbit and vice versa.
    - NRHO:
        Periapsis  : 3000km  , Apoapsis :  80000km

    - LLO:
        200km or 300km ( polar orbit , ex :88° )

    - Delta-v: 850 m/s
    - Duration: 0.5 day
    [Orbit and delta-vdData provided by ESA's Space Transportation Directorate; duration time provided by NASA]
    """

    def __init__(self, phase_id, plan, orbit, duration=1 * u.h, delta_v=850. * u.m / u.s, contingency=0.1):
        super().__init__(phase_id, plan)
        self.duration = duration
        self.delta_v = delta_v
        self.contingency = contingency
        self.orbit = orbit
        self.epoch_fix = None

    def apply(self):
        """ Asks the propulsion module to consume propellant according to delta v.
        Calls generic function to update orbit raan and epoch.
        """
        # this workaround to avoid issues when a wrong epoch is given as input
        if self.get_assigned_servicer().current_orbit.epoch and self.epoch_fix is None:
            self.epoch_fix = (self.get_assigned_servicer().current_orbit.epoch - self.orbit.epoch).to(u.h)
            self.duration += self.epoch_fix

        self.get_assigned_servicer().change_orbit(self.orbit)
        self.get_assigned_module().apply_delta_v(self.delta_v * (1 + self.contingency), 'From NRHO')
        self.update_servicer()
        # return self.get_assigned_servicer()

    def __str__(self):
        return ('--- \nFrom NRHO: ' + super().__str__()
                + '\n\tDelta V ' + str(self.delta_v))
