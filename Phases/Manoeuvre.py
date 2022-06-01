class Manoeuvre:
    """ Class representing a manoeuvre. This is used to simplify computations of thrust, mass and durations.

    Args:
        delta_v (u.<speed unit>): delta v for the manoeuvre

    Attributes:
        delta_v (u.<speed unit>): delta v for the manoeuvre
        burn_duration (u.<time unit>): duration of the burn for the manoeuvre
    """
    def __init__(self, delta_v):
        self.delta_v = delta_v
        self.burn_duration = 0. * u.minute

    def get_delta_v(self):
        return self.delta_v

    def compute_burn_duration(self, initial_mass, mean_thrust, isp):
        final_mass = initial_mass / np.exp((self.delta_v.to(u.meter / u.second) / const.g0 / isp.to(u.second)).value)
        mean_mass = (final_mass + initial_mass) / 2
        self.burn_duration = mean_mass / mean_thrust * self.delta_v
        self.burn_duration = self.burn_duration.to(u.s)
        pass

    def get_burn_duration(self, duty_cycle=1.):
        return self.burn_duration / duty_cycle

    def __str__(self):
        return (f"\u0394V: {self.delta_v.to(u.m/u.s):.1f}, \u0394t {self.get_burn_duration().to(u.minute):.1f}")

