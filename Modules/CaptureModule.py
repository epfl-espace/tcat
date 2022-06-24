from astropy import units as u
from Modules.GenericModule import GenericModule


class CaptureModule(GenericModule):
    """Capture module is a dynamic module that can link or unlink targets to the servicer.
    
    The captured target will be linked to the module's servicer and orbit changes will apply to the target as well.
    While the target is captured, it's mass is accounted for when computing servicer manoeuvres.

    Args:
        c.f. GenericModule

    Attributes:
        c.f. GenericModule
        captured_object(<>): object linked to the module after capture
    """
    def __init__(self, module_id, servicer, dry_mass_override=43.1*u.kg, reference_power_override=0.*u.W,
                 mass_contingency=0.25, recurring_cost_override=250000., non_recurring_cost_override=3825000):
        super().__init__(module_id, servicer, dry_mass_override=dry_mass_override,
                         reference_power_override=reference_power_override,
                         mass_contingency=mass_contingency,
                         recurring_cost_override=recurring_cost_override,
                         non_recurring_cost_override=non_recurring_cost_override)
        self.captured_object = None

    def set_captured_object(self,spacecraft):
        """ Set the capture object to a specified spacecraft

        Args:
            spacecraft (Spacecraft): captured spacecraft
        """
        self.captured_object = spacecraft

    def get_captured_object(self):
        """ Set the capture object to a specified spacecraft

        Return:
            self.captured_object (Spacecraft): captured spacecraft
        """
        return self.captured_object

    def is_capture_default(self):
        """ Check if module is default capture module for its servicer."""
        return self.spacecraft.capture_module_ID == self.id

    def reset(self):
        """ Resets the module to a state equivalent to servicer_group start. Used in simulation and convergence."""
        self.captured_object = None
