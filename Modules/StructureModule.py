import numpy as np
from astropy import units as u

from Modules.GenericModule import GenericModule


class StructureModule(GenericModule):
    """Structure module is a static module.

    Args:
        c.f. GenericModule

    Attributes:
        c.f. GenericModule
    """
    def __init__(self, module_id, servicer, dry_mass_override=None, reference_power_override=0.*u.W,
                 mass_contingency=0.1, recurring_cost_override=None, non_recurring_cost_override=None):
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
        self.compute_dry_mass(plan)

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
            structure_default_mass = 60. * u.kg
            servicer_default_mass = 225. * u.kg
            self.dry_mass = (structure_default_mass * self.spacecraft.get_dry_mass(contingency=False)
                             / servicer_default_mass)
        elif self.spacecraft.group in ['ADR_servicers', 'tankers']:
            structure_default_mass = 50.8 * u.kg
            servicer_default_mass = 225. * u.kg
            self.dry_mass = (structure_default_mass * self.spacecraft.get_dry_mass(contingency=False)
                             / servicer_default_mass)
        else:
            raise TypeError('Missing Structure mass model for group ' + self.spacecraft.group + ' .')

    def get_recurring_cost(self):
        """ Returns the recurring cost of the module in Euros.

        Return:
            (float): recurring module cost in Euro
        """
        if self.recurring_cost_override is not None:
            self.recurring_cost = self.recurring_cost_override
        elif self.spacecraft.group in ['LEO', 'high_Earth', 'planetary']:
            structure_default_recurring_cost = 200. * 1000  # EUR
            structure_default_mass = 50.8 * u.kg
            structure_mass = self.get_dry_mass(contingency=False)
            self.recurring_cost = (structure_default_recurring_cost
                                   * structure_mass.to(u.kg).value / np.log(structure_mass.to(u.kg).value)
                                   / structure_default_mass.to(u.kg).value
                                   / np.log(structure_default_mass.to(u.kg).value))
        elif self.spacecraft.group in ['ADR_servicers', 'tankers']:
            structure_default_recurring_cost = 200. * 1000  # EUR
            structure_default_mass = 50.8 * u.kg
            structure_mass = self.get_dry_mass(contingency=False)
            self.recurring_cost = (structure_default_recurring_cost
                                   * structure_mass.to(u.kg).value / np.log(structure_mass.to(u.kg).value)
                                   / structure_default_mass.to(u.kg).value
                                   / np.log(structure_default_mass.to(u.kg).value))
        else:
            raise TypeError('Missing Structure recurring cost model for group ' + self.spacecraft.group + ' .')
        return self.recurring_cost

    def get_non_recurring_cost(self):
        """ Returns the non recurring cost of the module in Euros.

        Return:
            (float): non recurring module cost in Euro
        """
        if self.non_recurring_cost_override is not None:
            self.non_recurring_cost = self.non_recurring_cost_override
        elif self.spacecraft.group in ['LEO', 'high_Earth', 'planetary']:
            structure_engineering_non_recurring_cost = 1202. * 1000  # EUR
            structure_default_non_recurring_cost = 601. * 1000  # EUR
            structure_default_mass = 50.8 * u.kg
            structure_mass = self.get_dry_mass(contingency=False)
            self.non_recurring_cost = (structure_engineering_non_recurring_cost
                                       + structure_default_non_recurring_cost
                                       * structure_mass.to(u.kg).value / np.log(structure_mass.to(u.kg).value)
                                       / structure_default_mass.to(u.kg).value
                                       / np.log(structure_default_mass.to(u.kg).value))
        elif self.spacecraft.group in ['ADR_servicers', 'tankers']:
            structure_engineering_non_recurring_cost = 1202. * 1000  # EUR
            structure_default_non_recurring_cost = 601. * 1000  # EUR
            structure_default_mass = 50.8 * u.kg
            structure_mass = self.get_dry_mass(contingency=False)
            self.non_recurring_cost = (structure_engineering_non_recurring_cost
                                       + structure_default_non_recurring_cost
                                       * structure_mass.to(u.kg).value / np.log(structure_mass.to(u.kg).value)
                                       / structure_default_mass.to(u.kg).value
                                       / np.log(structure_default_mass.to(u.kg).value))
        else:
            raise TypeError('Missing Structure non recurring cost model for group ' + self.spacecraft.group + ' .')
        return self.non_recurring_cost
