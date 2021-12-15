from astropy import units as u
from Modules.GenericModule import GenericModule


class ApproachSuiteModule(GenericModule):
    """Approach suite module is a static module.

    Args:
        c.f. GenericModule

    Attributes:
        c.f. GenericModule
    """
    def __init__(self, module_id, servicer, dry_mass_override=13.9*u.kg, reference_power_override=45*u.W,
                 mass_contingency=0.25, recurring_cost_override=100000., non_recurring_cost_override=4500000):
        super().__init__(module_id, servicer, dry_mass_override=dry_mass_override,
                         reference_power_override=reference_power_override,
                         mass_contingency=mass_contingency,
                         recurring_cost_override=recurring_cost_override,
                         non_recurring_cost_override=non_recurring_cost_override)
