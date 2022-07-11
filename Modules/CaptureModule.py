from typing import List
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

        # Capture spacecrafts
        self.captured_spacecrafts = dict()

    def add_captured_spacecrafts(self,spacecrafts):
        """ Populate all spacecraft with

        Args:
            spacecrafts (List[Spacecraft] or Spacecraft): captured spacecrafts
        """
        if isinstance(spacecrafts, list):
            for spacecraft in spacecrafts:
                self.captured_spacecrafts[spacecraft.get_id()] = spacecraft
        else:
            self.captured_spacecrafts[spacecrafts.get_id()] = spacecrafts

    def release_single_spacecraft(self,spacecraft):
        """ Release a single spacecraft at a time

        Args:
            spacecraft (Spacecraft): captured spacecraft to be released
        """
        if spacecraft.get_id() in self.captured_spacecrafts.keys():
            del self.captured_spacecrafts[spacecraft.get_id()]
    
    def release_all_spacecrafts(self):
        """ Release all spacecraft at a time
        """
        self.reset()

    def get_captured_spacecrafts(self):
        """ Set the capture object to a specified spacecraft

        Return:
            self.captured_spacecrafts (Spacecraft): captured spacecraft
        """
        return self.captured_spacecrafts

    def get_dry_mass(self):
        """Returns the dry mass of the module

        Return:
            (u.kg): dry mass
        """
        return self.dry_mass

    def get_captured_mass(self):
        """Returns the captured mass of the modules

        Return:
            (u.kg): dry mass
        """
        return sum([self.captured_spacecrafts[key].get_current_mass() for key in self.captured_spacecrafts.keys()])

    def get_current_mass(self):
        """Returns the total mass of the modules

        Return:
            (u.kg): dry mass
        """
        return self.get_dry_mass() + self.get_captured_mass()

    def is_capture_default(self):
        """ Check if module is default capture module for its servicer."""
        return self.spacecraft.capture_module_ID == self.id

    def reset(self):
        """ Resets the module to a state equivalent to servicer_group start. Used in simulation and convergence."""
        self.captured_spacecrafts = dict()
        self.history_captured_spacecrafts = dict()
