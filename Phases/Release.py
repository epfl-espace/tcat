from Modules.CaptureModule import *
from Phases.GenericPhase import GenericPhase
import copy

class Release(GenericPhase):
    """A Phase that represents release and separates the target given in argument from the servicer.
    Needs to be assigned to the capture module that captured the target.
        
    Args:
        phase_id (str): Standard id. Needs to be unique.
        plan (Plan_module.Plan): plan the phase belongs to
        target (poliastro.Client_module.Target): captured target to be releases
        duration (u.second): duration of the phase

    Attributes: (plus attributes from GenericPhase, some might be overridden by new definitions in this module)
        target (Client_module.Target): approached target
        duration (u.second): duration of the phase
    """
    def __init__(self, phase_id, plan, target, duration=3.*u.day):
        super().__init__(phase_id, plan)
        self.target = target
        self.duration = duration

    def assign_module(self, assigned_module):
        """ Assigns a module of a servicer to the phase. Checks for appropriate module type.

        Args:
            assigned_module (Fleet_module.<Module_class>): Added module
        """
        if isinstance(assigned_module, CaptureModule):
            self.assigned_module = assigned_module
        else:
            raise TypeError('Non-capture module assigned to Capture phase.')
    
    def apply(self):
        """ Separate target from the capture module. The target will now be independent of the servicer."""
        # TODO: check if commented code needs to be used

        self.get_assigned_module().release_single_spacecraft(self.target)
        
        # in case the architecture is launcher and sats, separate sats
        if self.target.mothership:
            # the sat is separated and updated
            self.get_assigned_spacecraft().separate_spacecraft(self.target)

        self.update_spacecraft()
        self.spacecraft_snapshot = self.build_spacecraft_snapshot_string()

        # Update target current orbit
        self.target.set_current_orbit(copy.deepcopy(self.get_assigned_spacecraft().get_current_orbit()))
        self.target.modify_insertion_orbit_epoch(self.get_assigned_spacecraft().get_current_orbit().epoch)

    def get_operational_cost(self):
        """ Returns the operational cost of the phase based on assumed FTE and associated costs. 

        Return:
            (float): operational cost in Euros
        """
        fte_operation = 10.  # FTE (1 per key sub-system)
        cost_fte_operation = 100. * 1000. / u.year  # Euros per year
        number_of_additional_gnd_station_passes = round(self.duration.to(u.day).value * 2.)
        passes_cost = number_of_additional_gnd_station_passes * 100.
        return (fte_operation * cost_fte_operation * self.duration + passes_cost).decompose()

    def build_spacecraft_snapshot_string(self):
        """ Save current assigned servicer as a snapshot for future references and post-processing. """
        return ('--- \nRelease: ' + super().build_spacecraft_snapshot_string()
                + '\n\tReleased Object: ' + str(self.target))
