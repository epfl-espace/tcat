from Phases.Common_functions import *
from Phases.GenericPhase import GenericPhase
from Modules.PropulsionModule import *


class OrbitMaintenance(GenericPhase):
    """A Phase that represents all manoeuvres made by the servicer to maintain its orbit in time.
    Needs to be assigned to a propulsion module.
        
    Args:
        phase_id (str): Standard id. Needs to be unique.
        plan (Plan_module.Plan): plan the phase belongs to
        orbit (poliastro.twobody.Orbit): orbit of the servicer
        duration (u.second): duration of the phase
        delta_v_contingency (float): mass_contingency to be applied to the delta_v

    Attributes: (plus attributes from GenericPhase, some might be overridden by new definitions in this module)
        orbit (poliastro.twobody.Orbit): orbit of the servicer
        duration (u.second): duration of the phase
        delta_v (u.meter / u.second): total delta v associated with the phase
        delta_v_contingency (float): mass_contingency to be applied to the delta_v
    """
    def __init__(self, phase_id, plan, orbit, duration, delta_v_contingency=0.1):
        super().__init__(phase_id, plan)
        self.orbit = orbit
        self.duration = duration
        self.delta_v = 0. * u.m / u.s
        self.delta_v_contingency = delta_v_contingency

    def assign_module(self, assigned_module):
        """ Assigns a module of a servicer to the phase. Checks for appropriate module type.

        Args:
            assigned_module (Fleet_module.<Module_class>): Added module
        """
        if isinstance(assigned_module, PropulsionModule):
            self.assigned_module = assigned_module
        else:
            raise TypeError('Non-propulsion module assigned to Orbit Maintenance phase.')
    
    def apply(self):
        """Asks the propulsion module to consume propellant according to delta v.
        Calls generic function to update orbit raan and epoch.
        """
        manoeuvre = compute_altitude_maintenance_delta_v(self.duration, self.orbit)
        self.delta_v = manoeuvre.get_delta_v()
        self.get_assigned_module().apply_delta_v(self.delta_v * (1 + self.delta_v_contingency), 'main_thrusters')
        self.update_spacecraft()
        self.take_spacecraft_snapshot()
        
    def get_operational_cost(self):
        """ Returns the operational cost of the phase based on assumed FTE and associated costs. 

        Return:
            (float): operational cost in Euros
        """
        fte_operation = 0.  # FTE
        cost_fte_operation = 100 * 1000 / u.year    # Euros per year
        return (fte_operation * cost_fte_operation * self.duration).decompose()
    
    def __str__(self):
        return '--- \nOrbit Maintenance: ' + super().__str__()
