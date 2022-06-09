from astropy import units as u

from Modules.GenericModule import GenericModule


class ThermalModule(GenericModule):
    """Thermal module is a static module.
    Args:
        module_id (str): Standard id. Needs to be unique.
        servicer (Scenario.Fleet_module.Servicer): servicer the module belongs to
        mass_contingency (float): mass_contingency on the module dry mass

    Attributes:
        module_id (str): Standard id. Needs to be unique.
        servicer (Scenario.Fleet_module.Servicer): servicer the module belongs to
        dry_mass (u.kg): module dry mass (no mass_contingency)
        mass_contingency (float): mass_contingency on the module dry mass
        reference_power (u.W): module mean power over designing phase (used as reference for power module phasing)
        recurring_cost (float): recurring cost of module in Euros
        non_recurring_cost (float): non recurring cost of module in Euros
    """
    def __init__(self, module_id, servicer, dry_mass_override=None, reference_power_override=None,
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
            self.reference_power = 0.25 * u.W
        elif self.spacecraft.group in ['ADR_servicers', 'tankers']:
            thermal_default_power = 60. * u.W
            servicer_default_power = 610. * u.W
            self.reference_power = thermal_default_power * self.spacecraft.get_reference_power() / servicer_default_power
        else:
            raise TypeError('Missing Thermal power model for group ' + self.spacecraft.group + ' .')

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
            thermal_default_mass = 300. * u.kg
            # TODO: consolidate ref mass and ref power
            ref_mass = 100. * u.kg
            ref_power = 100. * u.W
            servicer_default_mass = ref_mass
            thermal_default_power = ref_power
            self.dry_mass = (thermal_default_mass * self.spacecraft.get_reference_power() / thermal_default_power
                             * (self.spacecraft.get_dry_mass(contingency=False) / servicer_default_mass) ** (1 / 3))
        elif self.spacecraft.group in ['ADR_servicers', 'tankers']:
            thermal_default_mass = 21.7 * u.kg
            servicer_default_mass = 225. * u.kg
            thermal_default_power = 610. * u.W
            self.dry_mass = (thermal_default_mass * self.spacecraft.get_reference_power() / thermal_default_power
                             * (self.spacecraft.get_dry_mass(contingency=False) / servicer_default_mass) ** (1 / 3))
        else:
            raise TypeError('Missing Thermal mass model for group ' + self.spacecraft.group + ' .')

    def get_recurring_cost(self):
        """ Returns the recurring cost of the module in Euros.

        Return:
            (float): recurring module cost in Euro
        """
        if self.recurring_cost_override is not None:
            self.recurring_cost = self.recurring_cost_override
        elif self.spacecraft.group in ['LEO', 'high_Earth', 'planetary']:
            thermal_default_recurring_cost = 100. * 1000  # EUR
            thermal_default_mass = 21.7 * u.kg
            self.recurring_cost = thermal_default_recurring_cost * (self.get_dry_mass(contingency=False)
                                                                    / thermal_default_mass)
        elif self.spacecraft.group in ['ADR_servicers', 'tankers']:
            thermal_default_recurring_cost = 100. * 1000  # EUR
            thermal_default_mass = 21.7 * u.kg
            self.recurring_cost = thermal_default_recurring_cost * (self.get_dry_mass(contingency=False)
                                                                    / thermal_default_mass)
        else:
            raise TypeError('Missing Thermal recurring cost model for group ' + self.spacecraft.group + ' .')
        return self.recurring_cost

    def get_non_recurring_cost(self):
        """ Returns the non recurring cost of the module in Euros.

        Return:
            (float): non recurring module cost in Euro
        """
        if self.non_recurring_cost_override is not None:
            self.non_recurring_cost = self.non_recurring_cost_override
        elif self.spacecraft.group in ['LEO', 'high_Earth', 'planetary']:
            engineering_non_recurring_cost = 239. * 1000  # EUR
            thermal_default_non_recurring_cost = 91. * 1000  # EUR
            thermal_default_mass = 21.7 * u.kg
            self.non_recurring_cost = (engineering_non_recurring_cost + thermal_default_non_recurring_cost
                                       * (self.get_dry_mass(contingency=False) / thermal_default_mass) ** 2)
        elif self.spacecraft.group in ['ADR_servicers', 'tankers']:
            engineering_non_recurring_cost = 239. * 1000  # EUR
            thermal_default_non_recurring_cost = 91. * 1000  # EUR
            thermal_default_mass = 21.7 * u.kg
            self.non_recurring_cost = (engineering_non_recurring_cost + thermal_default_non_recurring_cost
                                       * (self.get_dry_mass(contingency=False) / thermal_default_mass) ** 2)
        else:
            raise TypeError('Missing Thermal non recurring cost model for group ' + self.spacecraft.group + ' .')
        return self.non_recurring_cost
