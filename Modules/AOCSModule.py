from astropy import units as u
from Modules.GenericModule import GenericModule


class AOCSModule(GenericModule):
    """AOCS (Attitude and orbit Control) module is a static module.

    Args:
        c.f. GenericModule

    Attributes:
        c.f. GenericModule
    """
    def __init__(self, module_id, servicer, dry_mass_override=None, reference_power_override=None, mass_contingency=0.1,
                 recurring_cost_override=None, non_recurring_cost_override=None):
        super().__init__(module_id, servicer, dry_mass_override=dry_mass_override,
                         reference_power_override=reference_power_override,
                         mass_contingency=mass_contingency,
                         recurring_cost_override=recurring_cost_override,
                         non_recurring_cost_override=non_recurring_cost_override)

    def design(self, plan):
        """ Method called during convergence to design the module given the current plan.

        Args:
            plan (Plan_module.Plan): plan for which the module is designed
        """
        self.compute_reference_power(plan)
        self.compute_dry_mass(plan)

    def compute_reference_power(self, plan):
        """ Compute the reference or "as designed" power for the module depending on the servicer group.
        Used in different models (mass, cost, etc.)

        Args:
            plan (Plan_module.Plan): plan for which the module is designed
        """
        # if reference power is given, override models
        if self.reference_power_override is not None:
            self.reference_power = self.reference_power_override
        # otherwise apply adequate model if available
        elif self.spacecraft.group in ['LEO']:
            reference_inertia = self.spacecraft.get_reference_inertia()
            self.reference_power = 89 * u.W * reference_inertia / (167 * u.kg * u.m * u.m)
        elif self.spacecraft.group in ['high_Earth']:
            reference_inertia = self.spacecraft.get_reference_inertia()
            self.reference_power = 50 * u.W * reference_inertia / (167 * u.kg * u.m * u.m)
        elif self.spacecraft.group in ['planetary']:
            reference_inertia = self.spacecraft.get_reference_inertia()
            # TODO: check ref_inertia
            ref_inertia = 1000.*u.kg*u.m*u.m
            self.reference_power = 1000. * u.W * reference_inertia / (ref_inertia * u.kg * u.m * u.m)
        elif self.spacecraft.group in ['ADR_servicers', 'tankers']:
            reference_inertia = self.spacecraft.get_reference_inertia()
            self.reference_power = 89 * u.W * reference_inertia / (167 * u.kg * u.m * u.m)
        else:
            raise TypeError('Missing AOCS power model for group '+self.spacecraft.group+' .')

    def compute_dry_mass(self, plan):
        """Compute the dry mass of the module depending gon the servicer group.
        Args:
            plan (Plan_module.Plan): plan for which the module is designed
        """
        # if dry mass is given, override models
        if self.dry_mass_override is not None:
            self.dry_mass = self.dry_mass_override
        # otherwise apply adequate model if available
        elif self.spacecraft.group in ['LEO']:
            sensors_mass = 5.9 * u.kg
            actuator_default_mass = 6.3 * u.kg
            reference_inertia = self.spacecraft.get_reference_inertia()
            self.dry_mass = sensors_mass + actuator_default_mass * reference_inertia / (167. * u.kg * u.m * u.m)
        elif self.spacecraft.group in ['high_Earth']:
            sensors_mass = 10. * u.kg
            actuator_default_mass = 5. * u.kg
            reference_inertia = self.spacecraft.get_reference_inertia()
            self.dry_mass = sensors_mass + actuator_default_mass * reference_inertia / (167. * u.kg * u.m * u.m)
        elif self.spacecraft.group in ['planetary']:
            sensors_mass = 50. * u.kg
            actuator_default_mass = 200. * u.kg
            reference_inertia = self.spacecraft.get_reference_inertia()
            # TODO: check ref_inertia
            ref_inertia = 1000.*u.kg*u.m*u.m
            self.dry_mass = sensors_mass + actuator_default_mass * reference_inertia / (ref_inertia * u.kg * u.m * u.m)
        elif self.spacecraft.group in ['ADR_servicers', 'tankers']:
            sensors_mass = 5.9 * u.kg
            actuator_default_mass = 6.3 * u.kg
            reference_inertia = self.spacecraft.get_reference_inertia()
            self.dry_mass = sensors_mass + actuator_default_mass * reference_inertia / (167. * u.kg * u.m * u.m)
        else:
            raise TypeError('Missing AOCS mass model for group '+self.spacecraft.group+' .')

    def get_recurring_cost(self):
        """ Returns the recurring cost of the module in Euros.

        Return:
            (float): recurring module cost in Euro
        """
        if self.recurring_cost_override is not None:
            self.recurring_cost = self.recurring_cost_override
        else:
            sensor_recurring_cost = 500. * 1000  # EUR
            actuators_default_recurring_cost = 740. * 1000  # EUR
            self.recurring_cost = sensor_recurring_cost + actuators_default_recurring_cost
        return self.recurring_cost

    def get_non_recurring_cost(self):
        """ Returns the non recurring cost of the module in Euros.

        Return:
            (float): non recurring module cost in Euro
        """
        if self.non_recurring_cost_override is not None:
            self.non_recurring_cost = self.non_recurring_cost_override
        else:
            reference_inertia = self.spacecraft.get_reference_inertia()
            engineering_non_recurring_cost = 2784. * 1000  # EUR
            sensor_non_recurring_cost = 698. * 1000  # EUR
            actuators_default_non_recurring_cost = 492. * 1000  # EUR
            self.non_recurring_cost = (engineering_non_recurring_cost + sensor_non_recurring_cost
                                       + actuators_default_non_recurring_cost
                                       * reference_inertia / (167. * u.kg * u.m * u.m))
        return self.non_recurring_cost
