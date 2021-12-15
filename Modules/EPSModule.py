from astropy import units as u

from Modules.GenericModule import GenericModule


class EPSModule(GenericModule):
    """EPS module is a static module.

    Args:
        c.f. GenericModule

    Attributes:
        c.f. GenericModule
    """
    def __init__(self, module_id, servicer, dry_mass_override=None, reference_power_override=None,
                 mass_contingency=0.25, recurring_cost_override=None, non_recurring_cost_override=None):
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
        elif self.servicer.group in ['LEO', 'high_Earth', 'planetary']:
            self.reference_power = 0.12 * u.W
        elif self.servicer.group in ['ADR_servicers', 'tankers']:
            self.reference_power = 40. * u.W
        else:
            raise TypeError('Missing EPS power model for group ' + self.servicer.group + ' .')

    def compute_dry_mass(self, plan):
        """Compute the dry mass of the module depending gon the servicer group.

        Args:
            plan (Plan_module.Plan): plan for which the module is designed
        """
        # if dry mass is given, override models
        if self.dry_mass_override is not None:
            self.dry_mass = self.dry_mass_override
        # otherwise apply adequate model if available
        elif self.servicer.group in ['LEO', 'high_Earth', 'planetary']:
            # TODO: consolidate inputs to model
            ref_mass = 100. * u.kg
            ref_eps = 100. * u.kg
            ref_power = 100. * u.W
            harness_default_mass = 40. * u.kg
            servicer_default_mass = ref_mass
            eps_default_mass = ref_eps
            servicer_default_power = ref_power
            self.dry_mass = (harness_default_mass * (self.servicer.get_dry_mass(contingency=False)
                                                     / servicer_default_mass) ** (1/3)
                             + eps_default_mass * self.get_reference_power() / servicer_default_power)
        elif self.servicer.group in ['ADR_servicers', 'tankers']:
            harness_default_mass = 8. * u.kg
            servicer_default_mass = 225. * u.kg
            eps_default_mass = 44. * u.kg
            servicer_default_power = 610. * u.W
            self.dry_mass = (harness_default_mass * (self.servicer.get_dry_mass(contingency=False)
                                                     / servicer_default_mass) ** (1/3)
                             + eps_default_mass * self.get_reference_power() / servicer_default_power)
        else:
            raise TypeError('Missing EPS mass model for group ' + self.servicer.group + ' .')

    def get_recurring_cost(self):
        """ Returns the recurring cost of the module in Euros.

        Return:
            (float): recurring module cost in Euro
        """
        if self.recurring_cost_override is not None:
            self.recurring_cost = self.recurring_cost_override
        elif self.servicer.group in ['LEO', 'high_Earth', 'planetary']:
            eps_default_recurring_cost = 500. * 1000  # EUR
            eps_default_mass = 52. * u.kg
            self.recurring_cost = eps_default_recurring_cost * (
                        self.get_dry_mass(contingency=False) / eps_default_mass) ** 0.72
        elif self.servicer.group in ['ADR_servicers', 'tankers']:
            eps_default_recurring_cost = 500. * 1000  # EUR
            eps_default_mass = 52. * u.kg
            self.recurring_cost = eps_default_recurring_cost * (
                        self.get_dry_mass(contingency=False) / eps_default_mass) ** 0.72
        else:
            raise TypeError('Missing EPS recurring cost model for group ' + self.servicer.group + ' .')
        return self.recurring_cost

    def get_non_recurring_cost(self):
        """ Returns the non recurring cost of the module in Euros.

        Return:
            (float): non recurring module cost in Euro
        """
        if self.non_recurring_cost_override is not None:
            self.non_recurring_cost = self.non_recurring_cost_override
        elif self.servicer.group in ['LEO', 'high_Earth', 'planetary']:
            engineering_non_recurring_cost = 1135. * 1000  # EUR
            eps_default_non_recurring_cost = 487. * 1000  # EUR
            eps_default_mass = 52. * u.kg
            self.non_recurring_cost = (engineering_non_recurring_cost + eps_default_non_recurring_cost
                                       * (self.get_dry_mass(contingency=False) / eps_default_mass) ** 0.72)
        elif self.servicer.group in ['ADR_servicers', 'tankers']:
            engineering_non_recurring_cost = 1135. * 1000  # EUR
            eps_default_non_recurring_cost = 487. * 1000  # EUR
            eps_default_mass = 52. * u.kg
            self.non_recurring_cost = (engineering_non_recurring_cost + eps_default_non_recurring_cost
                                       * (self.get_dry_mass(contingency=False) / eps_default_mass) ** 0.72)
        else:
            raise TypeError('Missing EPS non recurring cost model for group ' + self.servicer.group + ' .')
        return self.non_recurring_cost
