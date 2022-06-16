from astropy import units as u

class GenericModule:
    """A Module is an entity belonging to a servicer acting on other objects in the simulation.
    
    Different other module classes inherit from this class. Generic attributes are shared between all phases.
    When a module is initialized, it is added to the plan specified as argument. Inheriting modules may be either:
    - static: the module does not impact other objects in the simulation but is only modelled in terms of mass and power
    - dynamic: the module impacts other objects in the simulation (propulsion system that change orbits, etc)

    Args:
        module_id (str): Standard id. Needs to be unique.
        servicer (Scenario.Fleet_module.Servicer): servicer the module belongs to
        dry_mass_override (u.kg): module dry mass (no contingency), overrides possible underlying models
        reference_power_override (u.W): module mean power over designing phase, overrides possible underlying models
        recurring_cost_override (float): recurring cost of module in Euros, overrides possible underlying models
        non_recurring_cost_override (float): non recurring cost of module in Euros, overrides possible underlying models
        mass_contingency (float): mass_contingency on the module dry mass

    Attributes:
        module_id (str): Standard id. Needs to be unique.
        servicer (Scenario.Fleet_module.Servicer or Fleet_module.UpperStage): servicer the module belongs to
        dry_mass_override (u.kg): module dry mass (no contingency), overrides possible underlying models
        reference_power_override (u.W): module mean power over designing phase, overrides possible underlying models
        recurring_cost_override (float): recurring cost of module in Euros, overrides possible underlying models
        non_recurring_cost_override (float): non recurring cost of module in Euros, overrides possible underlying models
        dry_mass (u.kg): module dry mass (no contingency)
        reference_power (u.W): module mean power over designing phase
        recurring_cost (float): recurring cost of module in Euros
        non_recurring_cost (float): non recurring cost of module in Euros
        mass_contingency (float): mass_contingency on the module dry mass
    """
    def __init__(self, module_id, spacecraft, dry_mass_override=None, reference_power_override=None, mass_contingency=0.0,
                 recurring_cost_override=None, non_recurring_cost_override=None):
        self.id = module_id
        self.spacecraft = spacecraft
        self.dry_mass_override = dry_mass_override
        self.dry_mass = dry_mass_override
        self.initial_mass = dry_mass_override
        self.reference_power_override = reference_power_override
        self.reference_power = reference_power_override
        self.mass_contingency = mass_contingency
        self.recurring_cost_override = recurring_cost_override
        self.recurring_cost = recurring_cost_override
        self.non_recurring_cost_override = non_recurring_cost_override
        self.non_recurring_cost = non_recurring_cost_override
        self.add_module_to_servicer(spacecraft)

    def add_module_to_servicer(self, servicer):
        """ Add the module to the servicer given in argument. """
        servicer.add_module(self)

    def design(self, plan):
        """Method called during convergence to design the module given the current plan.
        This method usually computes the module dry mass and reference power based on the attributed plan.

        Args:
            plan (Plan_module.Plan): plan for which the module is designed
        """
        pass

    def get_phases(self, plan):
        """ Returns all phases from the plan the module is assigned to.
        Args:
            plan (Plan_module.Plan): plan for which the module is designed
        """
        servicer_phases = []
        for phase in plan.phases:
            if phase.get_assigned_module() == self:
                servicer_phases.append(phase)
        return servicer_phases

    def get_initial_mass(self, contingency=False):
        """Returns the initial mass of the module.

        Return:
            (u.kg): dry mass with contingency
        """
        return self.get_dry_mass(contingency=contingency)

    def get_dry_mass(self, contingency=True):
        """Returns the dry mass of the module (including contingencies by default).

        Return:
            (u.kg): dry mass with contingency
        """
        if not self.dry_mass:
            return 0. * u.kg
        if contingency:
            return self.dry_mass * (1 + self.mass_contingency)
        else:
            return self.dry_mass

    def get_wet_mass(self, contingency=True):
        """Returns the initial wet mass of the module at launch (including contingencies by default).

        Return:
            (u.kg): initial wet mass
        """
        return self.get_dry_mass(contingency=contingency)

    def get_reference_power(self):
        """ Returns the reference power of the module.
        The reference power is a parameter used in the design of most modules and usually represents the mean power
        draw of the module.

        Return:
            (u.W): reference power
        """
        if not self.reference_power:
            return 0. * u.W
        else:
            return self.reference_power

    def get_recurring_cost(self):
        """ Returns the recurring cost of the module in Euros.

        Return:
            (float): recurring module cost in Euro
        """
        return self.recurring_cost

    def get_non_recurring_cost(self):
        """ Returns the non recurring cost of the module in Euros.

        Return:
            (float): recurring module cost in Euro
        """
        return self.non_recurring_cost

    def reset(self):
        """ Resets the module to a state equivalent to simulation start. Used in simulation and mass_convergence. """
        pass
    
    def __str__(self):
        return (self.id
                + "\n\t\tDry mass: " + '{:.01f}'.format(self.get_dry_mass())
                + "\n\t\tReference power " + '{:.01f}'.format(self.get_reference_power()))
