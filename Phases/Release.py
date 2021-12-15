import Fleet_module
from Modules.CaptureModule import *
from Phases.GenericPhase import GenericPhase
import logging

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
        self.get_assigned_module().captured_object = None
        if isinstance(self.assigned_module.servicer, Fleet_module.Servicer):
            self.update_servicer()
            self.take_servicer_snapshot()
        else:
            self.update_launcher()
            self.take_launcher_snapshot()

        # in case the architecture is launcher and sats, separate sats
        logging.log(21, f"Sat deployed is {self.target}, sats in the dispenser are {self.target.mothership.current_sats}")
        if self.target.mothership:
            logging.log(21, f"Using Launcher mothership architecture")
            # the launcher's orbit is updated (not just the sat's)
            self.update_launcher(launcher=self.target.mothership)
            # the sat is separated and updated
            self.get_assigned_launcher().separate_sat(self.target)
            self.update_launcher()
            self.take_launcher_snapshot()

        # if not, then simply update the launcher
        elif isinstance(self.assigned_module.servicer, Fleet_module.LaunchVehicle):
            logging.log(21, f"NOT using Launcher mothership architecture")
            self.update_launcher()
            self.take_launcher_snapshot()

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

    def __str__(self):
        return ('--- \nRelease: ' + super().__str__()
                + '\n\tOf ' + str(self.target))
