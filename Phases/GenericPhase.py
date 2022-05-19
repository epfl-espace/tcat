import copy

import Scenario.Fleet_module
from Phases.Common_functions import *
from astropy.time import Time


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
        servicer_snapshot (Scenario.Fleet_module.Servicer): copy of the servicer, in its state at the completion of the phase
                                                 (for reference and post-processing purposes)
        starting_date (astropy.time.Time): beginning date of the phase (computed during simulation)
        end_date (astropy.time.Time): finish date of the phase (computed during simulation)
    """

    def __init__(self, phase_id, plan):
        self.ID = phase_id
        self.assigned_module = None
        plan.add_phase(self)
        self.duration = 0. * u.second
        self.servicer_snapshot = None
        self.launcher_snapshot = None
        self.starting_date = Time("2000-01-01 12:00:00")
        self.end_date = Time("2000-01-01 12:00:00")

    def apply(self):
        """ Change the servicer and clients impacted by the phase when called during simulation. """
        # In inheriting phases, this method holds the method to perform the phase, then calls the update_servicer method
        if isinstance(self.assigned_module.spacecraft, Scenario.Fleet_module.Servicer):
            self.update_servicer()
            self.take_servicer_snapshot()
        else:
            self.update_launcher()
            self.take_launcher_snapshot()


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

    def get_assigned_servicer(self):
        """ Returns the servicer that hosts the module assigned to the phase.
        Return:
            (Scenario.Fleet_module.Servicer): assigned servicer
        """
        return self.assigned_module.spacecraft

    def get_assigned_launcher(self):
        """ Returns the launcher that hosts the module assigned to the phase.
        Return:
            (Fleet_module.LaunchVehicle): assigned launcher
        """
        return self.assigned_module.spacecraft

    def update_servicer(self, servicer=None):
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
        if servicer is None:
            if isinstance(self.assigned_module.spacecraft, Scenario.Fleet_module.Servicer):
                servicer = self.get_assigned_servicer()
            else:
                servicer = self.get_assigned_launcher()

        # update epoch information based on currently computed starting date and phase duration
        self.starting_date = servicer.current_orbit.epoch
        self.end_date = self.starting_date + self.duration

        # update orbit
        new_orbit = update_orbit(servicer.current_orbit, self.end_date)
        servicer.change_orbit(new_orbit)

    def update_launcher(self, launcher=None):
        """ Perform changes on a launcher to represent its state at the end of the phase.

        If no specific launcher is given as attribute, the launcher assigned to the phase is taken.
        Changes are the orbit raan and epoch according to the specified duration and the launcher orbit at time of
        execution. This function may be redefined within inheriting phases.

        Args:
            launcher (LaunchVehicle):  (optional) launcher to be updated
                                This optional attributes is used to update launcher connected to the launcher assigned
                                to the phase
        """
        # if no servicer is given, take the servicer assigned to the phase
        if launcher is None:
            launcher = self.get_assigned_launcher()

        # update epoch information based on currently computed starting date and phase duration
        self.starting_date = launcher.current_orbit.epoch
        self.end_date = self.starting_date + self.duration

        # update orbit
        new_orbit = update_orbit(launcher.current_orbit, self.end_date)
        launcher.change_orbit(new_orbit)

    def take_servicer_snapshot(self):
        """ Save current assigned servicer as a snapshot for future references and post-processing. """
        self.servicer_snapshot = copy.deepcopy(self.get_assigned_servicer())

    def take_launcher_snapshot(self):
        """ Save current assigned launcher as a snapshot for future references and post-processing. """

        self.launcher_snapshot = copy.deepcopy(self.get_assigned_launcher())
        print(self.launcher_snapshot.current_orbit.a -self.launcher_snapshot.current_orbit.attractor.R)

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
        self.servicer_snapshot = None
        self.launcher_snapshot = None
        self.starting_date = Time("2000-01-01 12:00:00")
        self.end_date = Time("2000-01-01 12:00:00")

    def __str__(self):
        # format duration
        if self.duration > 30. * u.day:
            duration_print = self.duration.to(u.year)
        elif self.duration > 1. * u.day:
            duration_print = self.duration.to(u.day)
        else:
            duration_print = self.duration.to(u.minute)
        # build string
        if self.servicer_snapshot:
            return (str(self.ID)
                    + "\n\tEpoch: " + str(self.servicer_snapshot.current_orbit.epoch)
                    + "\n\tServicer: " + str(self.get_assigned_servicer().ID)
                    + "\n\tModule: " + str(self.get_assigned_module().id)
                    + "\n\tDuration : " + "{0:.1f}".format(duration_print)
                    + "\n\tServicer Orbit : " + orbit_string(self.servicer_snapshot.current_orbit)
                    + "\n\tServicer Current Mass : {0:.1f}".format(self.servicer_snapshot.get_current_mass())
                    + "\n\tServicer Wet Mass     : {0:.1f}".format(self.servicer_snapshot.get_wet_mass())
                    )
        elif self.launcher_snapshot:
            return (str(self.ID)
                    + "\n\tEpoch: " + str(self.launcher_snapshot.current_orbit.epoch)
                    + "\n\tLauncher: " + str(self.get_assigned_launcher().id)
                    + "\n\tModule: " + str(self.get_assigned_module().id)
                    + "\n\tDuration: " + "{0:.1f}".format(duration_print)
                    + "\n\tLauncher Orbit: " + orbit_string(self.launcher_snapshot.current_orbit)
                    + "\n\tLauncher Current Mass: {0:.1f}".format(self.launcher_snapshot.get_current_mass())
                    + "\n\tLauncher Wet Mass: {0:.1f}".format(self.launcher_snapshot.get_wet_mass()))
        else:
            if isinstance(self.assigned_module.spacecraft, Scenario.Fleet_module.Servicer):
                return (str(self.ID)
                        + "\n\tServicer: " + str(self.get_assigned_servicer().ID)
                        + "\n\tModule: " + str(self.get_assigned_module().ID)
                        + "\n\tDuration : " + "{0:.1f}".format(duration_print)
                        )
            else:
                return (str(self.ID)
                        + "\n\tLaunch Vehicle: " + str(self.get_assigned_launcher().id)
                        + "\n\tModule: " + str(self.get_assigned_module().id)
                        + "\n\tDuration : " + "{0:.1f}".format(duration_print)
                        )
