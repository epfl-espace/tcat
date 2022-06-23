import Spacecrafts.Servicer
from Modules.PropulsionModule import *
from Phases.GenericPhase import GenericPhase
from Spacecrafts.Spacecraft import Spacecraft


class Insertion(GenericPhase):
    """A Phase that places a servicer in its initial orbit as well as represents commissioning duration.
    Needs to be assigned to a propulsion module.
    
    There is a possibility to assign some delta v to this phase to represent initial propulsion commissioning.
    
    Args:
        phase_id (str): Standard id. Needs to be unique.
        plan (Plan_module.Plan): plan the phase belongs to
        orbit (poliastro.twobody.Orbit): insertion orbit
        propellant (u.<Mass_unit>): consumed propellant for the phase
        duration (u.<Time_unit>): duration of the phase
        propellant_contingency (float): mass_contingency to be applied to the delta_v

    Attributes: (plus attributes from GenericPhase, some might be overridden by new definitions in this module)
        orbit (poliastro.twobody.Orbit): insertion orbit
        propellant (u.<Mass_unit>): consumed propellant for the phase
        duration (u.<Time_unit>): duration of the phase
        mass_contingency (float): mass_contingency to be applied to the delta_v
    """
    def __init__(self, phase_id, plan, orbit, propellant=0. * u.kg, duration=30.*u.day, propellant_contingency=0.1):
        super().__init__(phase_id, plan)
        self.orbit = orbit
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
            raise TypeError('Non-propulsion module assigned to Insertion phase.')
    
    def apply(self):
        """ Moves the servicer to the insertion orbit.
        Asks the propulsion module to consume propellant according to predefined value.
        Calls generic function to update orbit raan and epoch.
        """

        if isinstance(self.assigned_module.spacecraft, Spacecrafts.Servicer.Servicer):
            self.get_assigned_spacecraft().change_orbit(self.orbit)
            self.get_assigned_module().consume_propellant(self.propellant * (1 + self.contingency), 'rcs_thrusters')
            self.update_spacecraft()
            self.take_spacecraft_snapshot()

        else:
            # isinstance(self.assigned_module.spacecraft, Fleet_module.UpperStage)
            self.get_assigned_spacecraft().change_orbit(self.orbit)
            # These two lines avoid propellant consumption for propulsion modules not yet modeled (e.g. launchers ones)
            if isinstance(self.assigned_module, PropulsionModule):
                self.get_assigned_module().consume_propellant(0 * u.kg, 'rcs_thrusters')
            self.update_spacecraft()
            self.take_spacecraft_snapshot()




    def get_operational_cost(self):
        """ Returns the operational cost of the phase based on assumed FTE and associated costs. 

        Return:
            (float): operational cost in Euros
        """
        fte_operation = 10  # FTE
        cost_fte_operation = 100 * 1000 / u.year  # Euros per year
        return (fte_operation * cost_fte_operation * self.duration).decompose()
        
    def __str__(self):
        return '--- \nInsertion: ' + super().__str__()
