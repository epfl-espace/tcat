from astropy import units as u

from Modules.GenericModule import GenericModule


class CommunicationModule(GenericModule):
    """Communication module is a static module.

    Args:
        c.f. GenericModule

    Attributes:
        c.f. GenericModule
    """
    def __init__(self, module_id, servicer, dry_mass_override=None, reference_power_override=None,
                 mass_contingency=0.2, recurring_cost_override=None, non_recurring_cost_override=None):
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
        elif self.spacecraft.group in ['LEO', 'high_Earth', 'planetary']:
            self.reference_power = 100 * u.W
        elif self.spacecraft.group in ['ADR_servicers', 'tankers']:
            self.reference_power = 20 * u.W
        else:
            raise TypeError('Missing Communication power model for group '+self.spacecraft.group+' .')

    def compute_dry_mass(self, plan):
        """Compute the dry mass of the module depending gon the servicer group.
        Args:
            plan (Plan_module.Plan): plan for which the module is designed
        """
        # if dry mass is given, override models
        if self.dry_mass_override is not None:
            self.dry_mass = self.dry_mass_override
        # otherwise apply adequate model if available
        elif self.spacecraft.group in ['LEO', 'high_Earth', 'planetary']:
            self.dry_mass = 70. * u.kg
        elif self.spacecraft.group in ['ADR_servicers', 'tankers']:
            self.dry_mass = 12.6 * u.kg
        else:
            raise TypeError('Missing Communication mass model for group '+self.spacecraft.group+' .')

    def get_recurring_cost(self):
        """ Returns the recurring cost of the module in Euros.

        Return:
            (float): recurring module cost in Euro
        """
        if self.recurring_cost_override is not None:
            self.recurring_cost = self.recurring_cost_override
        elif self.spacecraft.group in ['LEO', 'high_Earth', 'planetary']:
            self.recurring_cost = 645000.
        elif self.spacecraft.group in ['ADR_servicers', 'tankers']:
            self.recurring_cost = 250000.
        else:
            raise TypeError('Missing Communication recurring cost model for group ' + self.spacecraft.group + ' .')
        return self.recurring_cost

    def get_non_recurring_cost(self):
        """ Returns the non recurring cost of the module in Euros.

        Return:
            (float): non recurring module cost in Euro
        """
        if self.non_recurring_cost_override is not None:
            self.non_recurring_cost = self.non_recurring_cost_override
        elif self.spacecraft.group in ['LEO', 'high_Earth', 'planetary']:
            self.non_recurring_cost = 8000000.
        elif self.spacecraft.group in ['ADR_servicers', 'tankers']:
            self.non_recurring_cost = 8000000.
        else:
            raise TypeError('Missing Communication non recurring cost model for group ' + self.spacecraft.group + ' .')
        return self.non_recurring_cost
