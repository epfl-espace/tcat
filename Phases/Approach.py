from Phases.Common_functions import *
from Phases.GenericPhase import GenericPhase
from Modules.PropulsionModule import *


class Approach(GenericPhase):
    """ A Phase that represents maneuvers made by the servicer to reach proximity with a target from far rendezvous.
    Needs to be assigned to a propulsion module.

    The phase consumes a predefined amount of propellant given as attribute.
    # TODO: override get_delta_v method to return an estimate of delta_v based on consumed propellant and servicer mass
        
    Args:
        phase_id (str): Standard id. Needs to be unique.
        plan (Plan_module.Plan): plan the phase belongs to
        target (ADRClient_module.Target): approached target
        propellant (u.<Mass_unit>): consumed propellant for the phase
        duration (u.<Time_unit>): (optional) duration of the phase
        propellant_contingency (float): (optional) mass_contingency to be applied to the delta_v

    Attributes: (plus attributes from GenericPhase, some might be overridden by new definitions in this module)
        target (Client_module.Target): approached target
        propellant (u.<Mass_unit>): consumed propellant for the phase
        duration (u.<Time_unit>>): duration of the phase
        mass_contingency (float): mass_contingency to be applied to the delta_v
    """
    def __init__(self, phase_id, plan, target, propellant, duration=10.*u.day, propellant_contingency=0.1):
        super().__init__(phase_id, plan)
        self.target = target
        self.propellant = propellant
        self.duration = duration
        self.contingency = propellant_contingency

    def assign_module(self, assigned_module):
        """ Assigns a module of a servicer to the phase. Checks for appropriate module type.

        Args:
            assigned_module (Fleet_module.<Module_class>): Added module
        """
        if isinstance(assigned_module, PropulsionModule):
            self.assigned_module = assigned_module
        else:
            raise TypeError('Non-propulsion module assigned to Approach phase.')
    
    def apply(self):
        """ Asks the propulsion module to consume propellant according to predefined value.
        Calls generic methods to update orbit raan and epoch.
        """
        # check which epoch is later (servicer or target) and catch-up both objects to the later date
        if self.get_assigned_servicer().current_orbit.epoch > self.target.current_orbit.epoch:
            reference_time = self.get_assigned_servicer().current_orbit.epoch
            self.target.current_orbit = update_orbit(self.target.current_orbit, reference_time)
        else:
            reference_time = self.target.current_orbit.epoch
            self.get_assigned_servicer().current_orbit = update_orbit(self.get_assigned_servicer().current_orbit,
                                                                      reference_time)

        # check if orbits are close enough, if not throw an exception
        if abs(self.target.current_orbit.a - self.get_assigned_servicer().current_orbit.a) > 50. * u.km:
            raise ValueError('Attempted approach with non matching altitude in ' + self.ID + ' : '
                             + str(self.target.current_orbit.a - self.get_assigned_servicer().current_orbit.a))
        elif abs(self.target.current_orbit.inc - self.get_assigned_servicer().current_orbit.inc) > 5. * u.deg:
            raise ValueError('Attempted approach with non matching inclination in ' + ' : ' + self.ID
                             + str(self.target.current_orbit.inc - self.get_assigned_servicer().current_orbit.inc))
        elif abs(self.target.current_orbit.raan - self.get_assigned_servicer().current_orbit.raan) > 5. * u.deg:
            raise ValueError('Attempted approach with non matching raan in ' + self.ID + ' : '
                             + str(self.target.current_orbit.raan - self.get_assigned_servicer().current_orbit.raan))

        self.get_assigned_module().consume_propellant(self.propellant * (1 + self.contingency), 'rcs_thrusters')
        self.update_servicer()
        self.take_servicer_snapshot()

    def get_operational_cost(self):
        """ Returns the operational cost of the phase based on assumed FTE and associated costs. 

        Return:
            (float): operational cost in Euros
        """
        fte_operation = 10.  # FTE
        cost_fte_operation = 250. * 1000. / u.year    # Euros per year
        number_of_gnd_station_passes = round(self.duration.to(u.day).value * 2.)
        passes_cost = number_of_gnd_station_passes * 100.  # Euros
        return (fte_operation * cost_fte_operation * self.duration + passes_cost).decompose()
    
    def __str__(self):
        return ('--- \nApproach: ' + super().__str__()
                + '\n\tOf ' + str(self.target)
                )
