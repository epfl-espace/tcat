import copy
from Commons.common import convert_time_for_print

from Phases.Common_functions import *
from astropy.time import Time
from Phases.Common_functions import *


class GenericPhase:
    """A Phase is performed by an assigned module and changes the state of the fleet and clients it applies to.

    When the class is initialized, it is added to the plan specified as argument.
    Phases in a plan will be executed in the order of their initialization.

    Multiple classes inherit from this class. Generic attributes are shared between all phases:

    Args:
        phase_id (str): Standard id. Needs to be unique.
        plan (Plan_module.Plan): plan the phase is added to (the phase is automatically added to the plan)

    Attributes:
        phase_id (str): Standard id. Needs to be unique.
        assigned_module (Fleet_module.PropulsionModule or CaptureModule): module responsible for phase
        duration (u.second): duration of the phase
        spacecraft_snapshot (Scenario.Fleet_module.Servicer): copy of the servicer, in its state at the completion of the phase
                                                 (for reference and post-processing purposes)
        starting_date (astropy.time.Time): beginning date of the phase (computed during simulation)
        end_date (astropy.time.Time): finish date of the phase (computed during simulation)
    """

    def __init__(self, phase_id, plan):
        self.ID = phase_id
        self.assigned_module = None
        plan.add_phase(self)
        self.duration = 0. * u.second
        self.spacecraft_snapshot = None
        self.starting_date = Time("2000-01-01 12:00:00")
        self.end_date = Time("2000-01-01 12:00:00")

    def apply(self):
        """ Change the servicer and clients impacted by the phase when called during simulation. """
        # In inheriting phases, this method holds the method to perform the phase, then calls the update_servicer method
        self.update_spacecraft()
        self.spacecraft_snapshot = self.build_spacecraft_snapshot_string()

    def assign_module(self, assigned_module):
        """ Assigns a module of a servicer to the phase.
        Args:
            assigned_module (Fleet_module.<Module_class>): Added module
        """
        self.assigned_module = assigned_module

    def get_assigned_module(self):
        """ Returns the module assigned to the phase.

        Return:
            (Fleet_module.<Module_class>): assigned module
        """
        return self.assigned_module

    def get_assigned_spacecraft(self):
        """ Returns the servicer that hosts the module assigned to the phase.
        Return:
            (Scenario.Fleet_module.Servicer): assigned servicer
        """
        return self.assigned_module.spacecraft

    def update_spacecraft(self, spacecraft=None):
        """ Perform changes on a servicer to represent its state at the end of the phase.

        If no specific servicer is given as attribute, the servicer assigned to the phase is taken.
        Changes are the orbit raan and epoch according to the specified duration and the servicer orbit at time of
        execution. This function may be redefined within inheriting phases.

        Args:
            servicer (Servicer):  (optional) servicer to be updated
                                This optional attributes is used to update servicers connected to the servicer assigned
                                to the phase, for instance to update the whole mothership if a module of a kit is
                                assigned to the phase.
        """
        # if no servicer is given, take the servicer assigned to the phase
        if spacecraft is None:
            spacecraft = self.get_assigned_spacecraft()

        # update epoch information based on currently computed starting date and phase duration
        self.starting_date = spacecraft.current_orbit.epoch
        self.end_date = self.starting_date + self.duration

        # update orbit
        new_orbit = update_orbit(spacecraft.current_orbit, self.end_date)
        spacecraft.change_orbit(new_orbit)

    def build_spacecraft_snapshot_string(self):
        """ Save current assigned servicer as a snapshot for future references and post-processing. """
        # format duration
        duration_print = convert_time_for_print(self.duration)

        # Build snapshot string
        return (str(self.ID)
        + "\n\tAssociated Module: " + str(self.get_assigned_module().id)
        + "\n\tTotal Duration: " + "{0:.1f}".format(duration_print)
        + self.get_assigned_spacecraft().generate_snapshot_string())

    def get_operational_cost(self):
        """ Returns the operational cost of the phase based on operation labour.

        This function is usually redefined within specific phases.
        """
        return 0.

    def get_delta_v(self):
        """ Returns delta v for the phase. Returns 0 m/s if delta v does not apply to the phase. """
        if hasattr(self, 'delta_v'):
            return self.delta_v
        else:
            return 0. * u.m / u.s

    def get_duration(self):
        """ Returns duration for the phase, as currently computed. """
        return self.duration

    def reset(self):
        """ Resets the phase to its pre-simulation state. This function may be redefined within inheriting phases. """
        self.spacecraft_snapshot = None
        self.starting_date = Time("2000-01-01 12:00:00")
        self.end_date = Time("2000-01-01 12:00:00")

    def __str__(self):
        # print built spacecraft_snapshot
        return (self.spacecraft_snapshot)
