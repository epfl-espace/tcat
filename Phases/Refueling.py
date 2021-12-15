from Modules.PropulsionModule import *
from Phases.GenericPhase import GenericPhase


class Refueling(GenericPhase):
    """A Phase that exchanges fuel between two servicers. One servicer needs to capture the other.
    Needs to be assigned to a propulsion module.

    Args:
        phase_id (str): Standard id. Needs to be unique.
        plan (Plan_module.Plan): plan the phase belongs to
        duration (u.second): duration of the phase
        refuel_mass (u.kg): (optional) desired amount to be refueled, if not specified, fill recipient until full
                            or assigned_tanker is empty

    Attributes: (plus attributes from GenericPhase, some might be overridden by new definitions in this module)
        duration (u.second): duration of the phase
        refuel_mass (u.kg): (optional) desired amount to be refueled, if not specified, fill recipient or empty tanker
        last_refuel_for_recipient (bool): if True, this is the last refuel for the recipient, only fill what is required
    """

    def __init__(self, phase_id, plan, duration=3. * u.day, refuel_mass=None):
        super().__init__(phase_id, plan)
        self.duration = duration
        self.refuel_mass = refuel_mass
        self.last_refuel_for_recipient = False

    def assign_module(self, assigned_module):
        """ Assigns a module of a servicer to the phase. Checks for appropriate module type.

        Args:
            assigned_module (Fleet_module.<Module_class>): Added module
        """
        if isinstance(assigned_module, PropulsionModule):
            self.assigned_module = assigned_module
        else:
            raise TypeError('Non-propulsion module assigned to Refueling phase.')

    def apply(self):
        """ Performs refueling and update servicer. """
        if self.refuel_mass != 0. * u.kg:
            self.refuel(self.find_tank())
        self.update_servicer()
        self.take_servicer_snapshot()

    def find_tank(self):
        """ Find a tank within the captured targets to get the propellant from.

        Return:
             (Modules.PropulsionModule): Propulsion module used for refueling
        """
        # find all possible captured objects that have propulsion modules
        propulsion_modules = dict()
        for _, module in self.get_assigned_servicer().get_capture_modules().items():
            propulsion_modules = {**propulsion_modules, **module.captured_object.get_refueling_modules()}
        if not propulsion_modules:
            raise Exception('Found no assigned_tanker for '+str(self.ID)+'.')

        # from these, find which propulsion modules are flagged as capable of refueling
        tanks = dict()
        for _, module in propulsion_modules.items():
            if module.is_refueler:
                tanks[module.ID] = module
        if not tanks:
            raise Exception('Found no assigned_tanker for ' + str(self.ID) + '.')

        # choose option with most fuel if multiple choices
        max_propellant = None
        selected_tank = None
        for _, tank in tanks.items():
            if not max_propellant:
                max_propellant = tank.get_current_prop_mass()
                selected_tank = tank
            if tank.get_current_prop_mass() > max_propellant:
                max_propellant = tank.get_current_prop_mass()
                selected_tank = tank
        return selected_tank

    def refuel(self, tank):
        """ Update propellant masses of appropriate modules to represent refueling.

        Arg:
            tank (Modules.PropulsionModule): Propulsion module used for refueling
        """
        # find desired amount of fuel
        module = self.get_assigned_module()
        # if the amount is specified, use it
        if self.refuel_mass:
            transferred_fuel = self.refuel_mass
        # if the refueling is the last one for a recipient, only fill up to what is needed
        elif self.last_refuel_for_recipient and module.last_refuel_amount is not None:
            transferred_fuel = module.last_refuel_amount
        # otherwise fill the whole tank
        else:
            transferred_fuel = module.get_initial_prop_mass() - module.get_current_prop_mass()
        # do the exchange
        tank.consume_propellant(transferred_fuel, 'refueling')
        module.add_propellant(transferred_fuel)

    def get_operational_cost(self):
        """ Returns the operational cost of the phase based on assumed FTE and associated costs.

        Return:
            (float): operational cost in Euros
        """
        fte_operation = 10.  # FTE
        cost_fte_operation = 100. * 1000. / u.year  # Euros per year
        return (fte_operation * cost_fte_operation * self.duration).decompose()

    def __str__(self):
        return '--- \nRefueling: ' + super().__str__()
