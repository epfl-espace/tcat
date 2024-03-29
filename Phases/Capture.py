from astropy import units as u

from Phases.GenericPhase import GenericPhase
from Modules.CaptureModule import *

class Capture(GenericPhase):
    """A Phase that represents capture and links an object given in argument to the servicer for subsequent phases.
    Needs to be assigned to a capture module.
        
    Args:
        phase_id (str): Standard id. Needs to be unique.
        plan (Plan_module.Plan): plan the phase belongs to
        captured_object (ADRClient_module.Target or Scenario.Fleet_module.Servicer): captured object
        duration (u.<Time_unit>): duration of the phase

    Attributes: (plus attributes from GenericPhase, some might be overridden by new definitions in this module)
        captured_object (Client_module.Target): captured object
        duration (u.<Time_unit>): duration of the phase
    """
    def __init__(self, phase_id, plan, captured_object, duration=2.*u.week):
        super().__init__(phase_id, plan)
        self.captured_object = captured_object
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
        """Assigns target to the capture module. The target and servicer or kit will now share orbit changes.
         Calls generic function to update orbit raan and epoch.
         """
        # assign capture object to the appropriate module
        self.get_assigned_module().add_captured_spacecrafts(self.captured_object)

        # in case the architecture is mothership and current_kits, separate kit
        if self.captured_object.mothership:
            # the sat is separated and updated
            self.get_assigned_spacecraft().add_spacecraft(self.captured_object)

        # if not, then simply update the servicer
        self.update_spacecraft()
        self.spacecraft_snapshot = self.build_spacecraft_snapshot_string()

    def get_operational_cost(self):
        """ Returns the operational cost of the phase based on assumed FTE and associated costs. 

        Return:
            (float): operational cost in Euros
        """
        fte_operation = 10.  # FTE
        cost_fte_operation = 250. * 1000. / u.year  # Euros per year
        number_of_additional_gnd_station_passes = round(self.duration.to(u.day).value * 2.)
        passes_cost = number_of_additional_gnd_station_passes * 100.  # Euros
        return (fte_operation * cost_fte_operation * self.duration + passes_cost).decompose()

    def build_spacecraft_snapshot_string(self):
        """ Save current assigned servicer as a snapshot for future references and post-processing. """
        return ('--- \nCapture: ' + super().build_spacecraft_snapshot_string()
                + '\n\tCaptured Object: ' + str(self.captured_object))
