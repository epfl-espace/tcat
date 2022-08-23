import numpy as np
from astropy import constants as const
from astropy import units as u
from Modules.GenericModule import GenericModule


class PropulsionModule(GenericModule):
    """Propulsion module is a module that can change the orbit of its servicer and/or transfer duel to other modules.

    Args:
        c.f. GenericModule
        prop_type (str): Either "mono-propellant", "solid", "electrical", "water"
        max_thrust (u.N): maximum thrust of thruster
        min_thrust (u.N): minimal thrust of thruster
        isp (u.s): thruster specific impulse
        initial_propellant_mass (u.kg): initial guess for propellant mass required for the module
        max_tank_capacity (u.kg): maximum capacity of a single tank, tanks will be duplicated if too much propellant
        is_refueler (boolean): True if the module has a refueling valve and can transfer fuel to
        propellant_contingency (u.kg): ratio of fuel mass left at the end of the servicer_group to the initial mass
        assumed_duty_cycle (float): amount of time over one period where electrical thrust is assumed to be possible

    Attributes:
        c.f. GenericModule
        prop_type (str): Either "mono-propellant", "solid", "electrical", "water"
        max_thrust (u.N): maximum thrust of thruster
        min_thrust (u.N): minimal thrust of thruster
        isp (u.s): thruster specific impulse
        initial_propellant_mass (u.kg): initial guess for propellant mass required for the module
        max_tank_capacity (u.kg): maximum capacity of a single tank, tanks will be duplicated if too much propellant
        is_refueler (boolean): True if the module has a refueling valve and can transfer fuel to
        propellant_contingency (u.kg): ratio of fuel mass left at the end of the servicer_group to the initial mass
        assumed_duty_cycle (float): amount of time over one period where electrical thrust is assumed to be possible
        reference_thrust (u.N): reference thrust used for dimensioning purposes
        current_propellant_mass (u.kg): current propellant mass remaining in the module
        previous_initial_propellant_mass (u.kg): initial prop. mass from the previous convergence_margin iteration
        previous_minimal_propellant_mass (u.kg): min remaining prop. mass in the previous convergence_margin iteration
        previous_final_propellant_mass (u.kg); final prop. mass from the previous convergence_margin iteration
        rendezvous_throughput (u.kg): total amount of propellant used through rcs thrusters
        phasing_throughput (u.kg): total amount of propellant used through main thrusters
        previous_rendezvous_throughput (u.kg): phasing throughput from previous convergence_margin iteration
        previous_phasing_throughput (u.kg): rendezvous throughput from previous convergence_margin iteration
        last_refuel_amount (u.kg): amount of fuel taken by the module on the last refuel, implemented to avoid taking
                                   unnecessary fuel and used during convergence_margin
    """
    def __init__(self, module_id, servicer, prop_type, max_thrust, min_thrust, isp, initial_propellant_mass,
                 max_tank_capacity, dry_mass_override=None, reference_power_override=None,
                 mass_contingency=0.25, recurring_cost_override=None, non_recurring_cost_override=None,
                 is_refueler=False, propellant_contingency=0.15, assumed_duty_cycle=0.25):
        super().__init__(module_id, servicer, dry_mass_override=dry_mass_override,
                         reference_power_override=reference_power_override,
                         mass_contingency=mass_contingency,
                         recurring_cost_override=recurring_cost_override,
                         non_recurring_cost_override=non_recurring_cost_override)
        self.prop_type = prop_type
        self.max_thrust = max_thrust
        self.min_thrust = min_thrust
        self.isp = isp
        self.initial_propellant_mass = initial_propellant_mass
        self.max_tank_capacity = max_tank_capacity
        self.propellant_contingency = propellant_contingency
        self.is_refueler = is_refueler
        self.assumed_duty_cycle = assumed_duty_cycle
        self.reference_thrust = max_thrust
        self.current_propellant_mass = initial_propellant_mass
        self.previous_initial_propellant_mass = None
        self.previous_minimal_propellant_mass = None
        self.previous_final_propellant_mass = None
        self.rendezvous_throughput = 0. * u.kg
        self.phasing_throughput = 0. * u.kg
        self.previous_rendezvous_throughput = 0. * u.kg
        self.previous_phasing_throughput = 0. * u.kg
        self.last_refuel_amount = None
        self.nb_burn = 0

    def design(self, plan):
        """Method called during convergence_margin to design the module given the current plan.
        This method usually computes the module dry mass and reference power based on the attributed plan.

        Args:
            plan (Plan_module.Plan): plan for which the module is designed
        """
        rcs_thrust, main_thrust, rcs_prop_mass, ref_delta_v = self.compute_reference_manoeuvers(plan)

        # Here WTF?
        if self.prop_type in ['mono-propellant', 'water']:
            max_phasing_throughput = 150. * u.kg
        else:
            max_phasing_throughput = 1000. * u.kg

        max_rendezvous_throughput = 24. * u.kg
        reference_power = 0. * u.W

        # Attitude change
        if rcs_thrust > 0. * u.N:
            n_of_rdv_thrusters, n_of_rdv_sets = self.compute_thrusters_number(rcs_thrust,
                                                                              self.previous_rendezvous_throughput,
                                                                              max_rendezvous_throughput,
                                                                              override_number=8)
            rendezvous_power = self.compute_reference_power(plan, rcs_thrust, n_of_rdv_thrusters)
            reference_power = max(rendezvous_power, reference_power)
        else:
            n_of_rdv_thrusters = 0
            n_of_rdv_sets = 0

        # Orbital change
        if main_thrust > 0. * u.N:
            n_of_ph_thrusters, n_of_ph_sets = self.compute_thrusters_number(main_thrust,
                                                                            self.previous_phasing_throughput,
                                                                            max_phasing_throughput)
            phasing_power = self.compute_reference_power(plan, main_thrust, n_of_ph_thrusters)
            reference_power = max(reference_power, phasing_power)
            self.reference_thrust = main_thrust
        else:
            n_of_ph_thrusters = 0
            n_of_ph_sets = 0

        
        self.reference_power = reference_power

        # Compute number of tanks
        n_of_tanks = self.compute_tanks_number()

        # Compute dry mass based on estimated design stage
        self.dry_mass = self.compute_dry_mass(plan, n_of_rdv_thrusters, n_of_rdv_sets, n_of_ph_thrusters, n_of_ph_sets,n_of_tanks, ref_delta_v)

    def compute_reference_manoeuvers(self, plan):
        """ Return the reference thrust and delta v for phasing and rendezvous maneuvers.
        For phasing thrust, based on desired delta v and burn durations.
        For rendezvous thrust, based on servicer inertia.

        Args:
            plan (Plan_module.Plan): plan for which the thruster is designed, used to retrieve reference delta v

        Return:
            (u.N): reference thrust, phasing_thrust
        """
        # setup and get representative delta v
        ref_delta_v, rcs_prop_mass = self.spacecraft.get_reference_manoeuvres(plan, self)
        # for phasing
        if ref_delta_v > 0. * u.m / u.s:
            reference_servicer_mass = self.spacecraft.get_initial_wet_mass()
            if self.prop_type in ['mono-propellant', 'water', 'solid', "bi-propellant"]:
                reference_time = 20. * u.minute
                main_thrust = (reference_servicer_mass * ref_delta_v / reference_time).to(u.N)
                # check feasibility, limiting max number of thrusters to 4
                number_of_manoeuvres = np.ceil(main_thrust.to(u.N).value / self.max_thrust.to(u.N).value)
                main_thrust = main_thrust / number_of_manoeuvres
                ref_delta_v = ref_delta_v / number_of_manoeuvres
            elif self.prop_type in ['electrical']:
                reference_time = 6. * u.week
                # assumed duty cycle of 25%, no possibility to duplicate maneuver
                main_thrust = reference_servicer_mass * ref_delta_v / reference_time / self.assumed_duty_cycle
            else:
                raise Exception
        else:
            main_thrust = 0. * u.N
            ref_delta_v = 0. * u.m / u.s
        # for rendezvous
        if rcs_prop_mass > 0. * u.kg:
            rcs_thrust = 1. * u.N * self.spacecraft.get_reference_inertia() / (167. * u.kg * u.m * u.m)
            rcs_prop_mass = rcs_prop_mass / 3
        else:
            rcs_thrust = 0. * u.N
            rcs_prop_mass = 0. * u.kg
        return rcs_thrust.to(u.N), main_thrust.to(u.N), rcs_prop_mass.to(u.kg), ref_delta_v.to(u.m / u.s)

    def compute_thrusters_number(self, desired_thrust, propellant_throughput, max_thrusters_throughput,
                                 override_number=None):
        """ Returns the number of thrusters in the design based on desired thrust and total propellant throughput.
        If the throughput exceeds the thruster capabilities, the thruster set is duplicated.

        Args:
            desired_thrust (u.N): desired overall thrust output of the thrusters
            propellant_throughput (u.kg): actual throughput experienced by the thrusters during servicer_group
            max_thrusters_throughput (u.kg): total_throughput the thrusters are designed to withstand
            override_number (int): if given, overrides the computation based on desired thrust, only checks throughput

        Returns:
            (int): number of thrusters
        """
        if override_number:
            thrusters_number = override_number
        else:
            thrusters_number = max(1, np.ceil(desired_thrust / self.max_thrust).decompose())
        max_throughput = max_thrusters_throughput * thrusters_number
        duplicate_factor = max(1, np.ceil(propellant_throughput / max_throughput))
        return thrusters_number, duplicate_factor

    def compute_reference_power(self, plan, reference_thrust, number_of_thrusters):
        """ Return the reference or "as designed" power for the module.
        Used in different models (mass, cost, etc.)

        Return:
            (u.W): reference power
        """
        if self.reference_power_override is not None:
            self.reference_power = self.reference_power_override
        elif self.prop_type in ['mono-propellant']:
            valve_power = number_of_thrusters * (7.76 + 0.106 * reference_thrust.to(u.N).value
                                                 / number_of_thrusters) * u.W / 4
            heater_power = number_of_thrusters * (3.76 + 0.868 * reference_thrust.to(u.N).value
                                                  - 0.00193 * 0.868 * reference_thrust.to(u.N).value ** 2
                                                  / number_of_thrusters) * u.W
            self.reference_power = (valve_power + heater_power)
        elif self.prop_type in ['water', 'bi-propellant']:
            valve_power = number_of_thrusters * (7.76 + 0.106 * reference_thrust.to(u.N).value
                                                 / number_of_thrusters) * u.W / 4
            heater_power = 0. * u.W
            self.reference_power = (valve_power + heater_power)
        elif self.prop_type in ['solid']:
            self.reference_power = 1. * u.W
        elif self.prop_type in ['electrical']:
            self.reference_power = (reference_thrust.to(u.N).value + 3.8612) / 0.0633 * u.W
            self.isp = (504.06 + 2.6445 * self.reference_power.to(u.W).value
                        - 0.0023 * self.reference_power.to(u.W).value ** 2) * u.s
        return self.reference_power

    def compute_tanks_number(self):
        """ Returns the number of tanks needed for the initial propellant mass given a single tank maximum capacity."""
        return max(1, np.ceil(self.initial_propellant_mass / self.max_tank_capacity).decompose().value)

    def compute_dry_mass(self, plan, n_of_rdv_thrusters, n_of_rdv_sets, n_of_ph_thrusters, n_of_ph_sets, n_of_tanks,
                         phasing_delta_v):
        """ Compute module dry mass based on number of elements and other parameters."""
        if self.dry_mass_override is not None:
            self.dry_mass = self.dry_mass_override
        elif self.spacecraft.group in ['LEO', 'high_Earth', 'planetary']:
            # engine_mass = ((1.104 ** -3) * self.max_thrust.to(u.N).value + 27.702) * u.kg
            engine_mass = (9.81 * 10 ** -4 * self.max_thrust.to(u.N).value + 5.37 * 10 ** -4
                           * self.max_thrust.to(u.N).value * 90 ** 0.5 + 25) * u.kg
            tank_mass = 0.1 * self.initial_propellant_mass
            self.dry_mass = engine_mass + tank_mass
        elif self.prop_type == "mono-propellant":
            # setup and tubing mass
            thruster_mass = 0. * u.kg
            tubing_mass = 2. * u.kg
            # rendezvous_thrusters mass
            thruster_mass += 3.2 * u.kg / 8 * n_of_rdv_thrusters * n_of_rdv_sets
            # phasing thrusters mass
            thruster_mass += 1.1 * u.kg * n_of_ph_thrusters * n_of_ph_sets
            # tanks mass
            propellant_mass_per_tank = self.initial_propellant_mass / n_of_tanks
            tank_mass = (1.4015 + 0.1269 * propellant_mass_per_tank.to(u.kg).value
                         - 0.00007 * propellant_mass_per_tank.to(u.kg).value ** 2) * u.kg
            tank_mass *= n_of_tanks
            self.dry_mass = thruster_mass + tank_mass + tubing_mass
        elif self.prop_type == "electrical":
            # tubing mass
            tubing_mass = 2. * u.kg
            # phasing thrusters mass
            thruster_mass = 5.7 * u.kg * n_of_ph_thrusters * n_of_ph_sets
            # tanks mass
            propellant_mass_per_tank = self.initial_propellant_mass / n_of_tanks
            tank_mass = (5.0163 + 0.07161 * propellant_mass_per_tank.to(u.kg).value) * u.kg
            tank_mass *= n_of_tanks
            self.dry_mass = thruster_mass + tank_mass + tubing_mass
        elif self.prop_type == "water":
            # setup and tubing mass
            tubing_mass = 2. * u.kg
            thruster_mass = 3.5 * u.kg
            # rendezvous thrusters mass
            thruster_mass += 1. * u.kg * n_of_ph_thrusters * n_of_ph_sets
            # phasing thrusters mass
            thruster_mass += 3.2 * u.kg / 8 * n_of_rdv_thrusters * n_of_rdv_sets
            max_continuous_delta_v = max(0. * u.m / u.s, phasing_delta_v)
            # compute tanks for hydrolyzed H2 and O2
            hydrolyzed_mass = (self.spacecraft.get_initial_wet_mass()
                               * (1 - 1 / np.exp((max_continuous_delta_v / self.isp / const.g0).decompose().value)))
            n_h2 = hydrolyzed_mass / (18. * u.g / u.mol)
            n_o2 = hydrolyzed_mass / (36. * u.g / u.mol)
            h2_volume = n_h2 * const.R * (291 * u.K) / (24 * u.bar)
            o2_volume = n_o2 * const.R * (291 * u.K) / (24 * u.bar)
            h2_tank_mass = (5.0163 + 0.12836 * h2_volume.to(u.m ** 3).value) * u.kg
            o2_tank_mass = (5.0163 + 0.12836 * o2_volume.to(u.m ** 3).value) * u.kg
            if hydrolyzed_mass == 0. * u.kg:
                h2_tank_mass = 0. * u.kg
                o2_tank_mass = 0. * u.kg
            # compute tanks for water
            propellant_mass_per_tank = self.initial_propellant_mass / n_of_tanks
            h2o_tank_mass = (1.4015 + 0.1269 * propellant_mass_per_tank.to(u.kg).value
                             - 0.00007 * propellant_mass_per_tank.to(u.kg).value ** 2) * u.kg
            h2o_tank_mass *= n_of_tanks
            self.dry_mass = thruster_mass + h2o_tank_mass + h2_tank_mass + o2_tank_mass + tubing_mass
        elif self.prop_type == "bi-propellant":
            self.dry_mass = 40. * u.kg + 11. * u.kg + (0.096 * (1 + 0.278) + 0.08) * self.initial_propellant_mass
        elif self.prop_type == "solid":
            self.dry_mass = 0.1 * self.initial_propellant_mass
        else:
            raise TypeError('Missing Propulsion mass model for group ' + self.spacecraft.group + ' .')
        if self.is_refueler:
            conditioning_mass = 10. * u.kg
            self.dry_mass += conditioning_mass
        return self.dry_mass

    def get_recurring_cost(self):
        """ Returns the recurring cost of the module in Euros.

        Return:
            (float): recurring module cost in Euro
        """
        if self.recurring_cost_override is not None:
            self.recurring_cost = self.recurring_cost_override
        elif self.prop_type in ['mono-propellant']:
            self.recurring_cost = 1000. * 1000 + 200. * self.initial_propellant_mass.to(u.kg).value
        elif self.prop_type in ['electrical']:
            self.recurring_cost = 2500. * 1000 + 1500. * self.initial_propellant_mass.to(u.kg).value
        elif self.prop_type in ['water']:
            self.recurring_cost = 1500. * 1000 + 6000. * self.get_reference_power().to(u.W).value
        return self.recurring_cost

    def get_non_recurring_cost(self):
        """ Returns the recurring cost of the module in Euros.

        Return:
            (float): non recurring module cost in Euro
        """
        if self.non_recurring_cost_override is not None:
            self.non_recurring_cost = self.non_recurring_cost_override
        else:
            self.non_recurring_cost = 1700 * 1000
        return self.non_recurring_cost

    def get_nb_burn(self):
        """ Returns the number of time a delta_v is executed

        :return: number of executed dVs
        :rtype: float
        """
        return self.nb_burn

    def is_main_propulsion(self):
        """ Check if module is default phasing for its servicer."""
        return self.spacecraft.main_propulsion_module_ID == self.id
    
    def define_as_rcs_propulsion(self):
        """ Make module rendezvous capture module for its servicer.
        Used in automatic generation of planning and servicers.
        """
        self.spacecraft.rcs_propulsion_module_ID = self.id

    def is_rcs_propulsion(self):
        """ Check if module is default phasing for its servicer."""
        return self.spacecraft.rcs_propulsion_module_ID == self.id
    
    def apply_delta_v(self, delta_v, phase):
        """Compute and consume the appropriate propellant to perform delta_v.

        Args:
            delta_v (u.m/u.s): delta v to be performed
            phase (str): used to track throughput of thruster ("main_thrusters" or "rcs_thrusters" respectively)
        """
        self.delta_mass = self.compute_propellant_mass(delta_v)
        self.consume_propellant(self.delta_mass, phase=phase)
        self.nb_burn += 1

    def compute_propellant_mass(self, delta_v):
        """ Compute amount of propellant to produce delta v.

        Return:
            (u.kg): propellant mass
        """
        # TODO add propellant mass computation for non impulsive maneuvers
        initial_mass = self.spacecraft.get_current_mass()
        temp = np.exp((delta_v.to(u.meter / u.second)/const.g0/self.isp.to(u.second)).value)
        consumed_propellant_mass = initial_mass * (temp-1) / temp
        return consumed_propellant_mass
    
    def consume_propellant(self, propellant_mass, phase):
        """ Reduce the current propellant mass of the module by the argument.

        Args:
            propellant_mass (u.kg): consumed propellant
            phase (str): used to track throughput of thruster ("main_thrusters" or "rcs_thrusters" respectively)
        """
        self.log_propellant_consumption(propellant_mass, phase)
        self.current_propellant_mass = self.current_propellant_mass - propellant_mass

    def add_propellant(self, propellant_mass, phase):
        """ Add a propellant to the module (usually through refueling).

        Args:
            propellant_mass (u.kg): propellant mass to be added from the current propellant
            phase (str): used to track throughput of thruster ("refueling" most likely)
        """
        self.log_propellant_consumption(propellant_mass, phase)
        self.current_propellant_mass = self.current_propellant_mass + propellant_mass

    def log_propellant_consumption(self, delta_mass, phase):
        """ Log propellant mass consumed by the module. This is done independently for rendezvous and phasing thrusters.
        Used to check if thrusters max throughput are not exceeded.

        Args:
            delta_mass (u.kg): propellant mass to log
            phase (str): used to track throughput of thruster ("main_thrusters", "rcs_thrusters", etc)
        """
        if phase == "main_thrusters":
            self.rendezvous_throughput += delta_mass
        elif phase == 'rcs_thrusters':
            self.phasing_throughput += delta_mass
        elif phase == 'refueling':
            pass
        else:
            raise TypeError('Missing propellant consumption/refueling phase: ' + phase + ' .')

    def get_initial_prop_mass(self):
        """ Returns the initial mass of propellant at launch in the module.

        Return:
            (u.kg): mass of the initial propellant
        """
        return self.initial_propellant_mass

    def get_current_prop_mass(self):
        """ Returns the current mass of propellant at launch in the module.

        Return:
            (u.kg): mass of the current propellant in the module
        """
        return self.current_propellant_mass

    def get_initial_wet_mass(self):
        """Returns the initial wet mass of the module at launch (including contingencies by default).

        Return:
            (u.kg): initial wet mass
        """
        return super().get_initial_wet_mass() + self.get_initial_prop_mass()

    def get_current_mass(self):
        """Returns the current wet mass of the module (including contingencies by default).

        Return:
            (u.kg): current wet mass
        """ 
        return  super().get_current_mass() + self.get_current_prop_mass()

    def get_minimal_propellant_mass(self, plan):
        """ Returns the lowest fuel state of the module over a plan. Used for convergence of fleet.

        Args:
            plan (Plan_module.Plan): plan in which the module is used

        Return:
            (u.kg): lowest fuel state of the module over the plan
        """
        minimal_propellant_mass = self.initial_propellant_mass
        for i, phase in enumerate(self.get_phases(plan)):
            phase_propellant_mass = phase.spacecraft_snapshot.modules[self.id].current_propellant_mass
            if phase_propellant_mass < minimal_propellant_mass:
                minimal_propellant_mass = phase_propellant_mass
        return minimal_propellant_mass

    def update_initial_propellant_mass(self, new_propellant_mass, plan):
        """ Update the module after a change of initial propellant mass during convergence_margin.

        Args:
            new_propellant_mass (u.kg): new best guess for propellant mass needed for module
            plan (Plan_module.Plan): plan in which the module is used
        """
        self.previous_initial_propellant_mass = self.initial_propellant_mass
        self.previous_minimal_propellant_mass = self.get_minimal_propellant_mass(plan)
        self.initial_propellant_mass = new_propellant_mass

    def reset(self):
        """" Resets the module to a state equivalent to servicer_group start. Used in simulation and convergence_margin.
        """
        if self.last_refuel_amount is not None:
            self.last_refuel_amount = (self.last_refuel_amount - self.current_propellant_mass
                                       + self.initial_propellant_mass * self.propellant_contingency)
        else:
            self.last_refuel_amount = (self.initial_propellant_mass - self.current_propellant_mass)
        self.previous_final_propellant_mass = self.current_propellant_mass
        self.current_propellant_mass = self.initial_propellant_mass
        self.previous_rendezvous_throughput = self.rendezvous_throughput
        self.rendezvous_throughput = 0. * u.kg
        self.previous_phasing_throughput = self.phasing_throughput
        self.phasing_throughput = 0. * u.kg
        self.nb_burn = 0

    def __str__(self):
        return (super(PropulsionModule, self).__str__()
                + "\n\t\tPropellant mass: " + '{:01.1f}'.format(self.initial_propellant_mass))
