"""
Created:        ?
Last Revision:  23.05.2022
Author:         ?,Emilien Mingard
Description:    Plan Class definition
"""

# Import Classes
from Phases.Common_functions import *

# Import libraries
import logging

class Plan:
    """A Plan consists of a list of phases. The list is ordered in terms of the chronology of the phases.
        The class is initialized with an emtpy list of phases.
        It contains methods used during simulation to apply changes to the fleet according to the phases.
        It contains methods to optimize the assignment of phases based on various assumptions.

    Args:
        plan_id (str): Standard id. Needs to be unique.
        starting_epoch (astropy.Time): reference epoch corresponding to first launch

    Attributes:
        id (str): Standard id. Needs to be unique.
        starting_epoch (astropy.Time): reference epoch corresponding to first launch
        phases (list): List of phases (Ordered)
    """

    """
    Init
    """
    def __init__(self, plan_id, starting_epoch):
        self.id = plan_id
        self.starting_epoch = starting_epoch
        self.phases = []
    
    """
    Methods
    """
    def add_phase(self, phase):
        """Adds a phase to the Plan class.

        Args:
            phase (Phase): phase to add to the plan (sequential)
        """
        self.phases.append(phase)
        
    def apply(self, verbose=False):
        """Calls the apply function of each phase of the plan in their respective order.
            This function is used to execute the plan. The phases are reset at the start.

        Args:
            verbose (boolean): if True, print message during phase execution
        """       
        self.reset()
        for phase in self.phases:
            phase.apply()
            logging.info(phase.__str__())
            if verbose:
                print(phase)

    def get_phases_from_type(self, phase_type):
        """ Returns all phases of a certain type as a list.

        Arg:
            phase_type (Class): class of phases for which to return instances found in the plan
        """
        phases_list = []
        for phase in self.phases:
            if isinstance(phase, phase_type):
                phases_list.append(phase)
        return phases_list

    def get_program_duration(self, additional_schedule_margin=1. * u.year):
        """ Return total duration of program based on operations duration and a margin (1 year by default).
            The simulation must have run to compute this.

        Arg:
            additional_schedule_margin (u.<time unit>): time to add to the duration computation for margin
        Return:
            (u.<time unit>): total duration of the program
        """
        start_date = self.starting_epoch
        end_date = start_date
        for phase in self.phases:
            if phase.end_date > end_date:
                end_date = phase.end_date
        end_date += additional_schedule_margin
        duration = end_date - start_date
        return duration.to(u.day)

    def get_total_cost(self, fleet):
        """ Returns total operation costs. The simulation must have run to compute this.

        Arg:
            fleet (Fleet): fleet of servicers that performed the plan

        Return:
            (float): cost in Euros
        """
        return (self.get_labour_operations_cost(fleet) + self.get_baseline_operations_cost(fleet)
                + self.get_moc_location_cost(fleet) + self.get_gnd_stations_cost(fleet))

    def get_baseline_operations_cost(self, fleet):
        """ Returns baseline of operators labour costs. The simulation must have run to compute this. This cost is
            linked to the duration of the program, not particular operations.

        Arg:
            fleet (Fleet): fleet of servicers, introduced to homogenize "get_" methods implementation

        Return:
            (float): cost in Euros
        """
        # directors cost
        directors_fte = 2
        directors_cost = 280. * 1000. / u.year
        directors_labour = directors_fte * directors_cost
        # experts cost (about one per sub-systems)
        experts_fte = 5 * 0.2  # at 20%
        experts_cost = 250. * 1000. / u.year
        experts_labour = experts_fte * experts_cost
        # engineers cost (about one per sub-systems)
        engineers_fte = 5
        engineers_cost = 250. * 1000. / u.year
        engineers_labour = engineers_fte * engineers_cost
        # operators cost (about one per sub-systems)
        constellation_ctrl_operators_fte = 2
        fds_operators_fte = 4
        operators_cost = 250. * 1000. / u.year
        operators_labour = (fds_operators_fte + constellation_ctrl_operators_fte) * operators_cost
        # IT cost (about one per sub-systems)
        it_fte = 2
        it_cost = 200. * 1000. / u.year
        it_labour = it_fte * it_cost
        # gather costs
        baseline_labour = directors_labour + experts_labour + engineers_labour + operators_labour + it_labour
        baseline_cost = baseline_labour * self.get_program_duration()
        return baseline_cost.decompose()

    def get_labour_operations_cost(self, fleet):
        """ Returns direct labour cost for operation. This cost is linked to particular operations that require
            exceptional labour.

        Arg:
            fleet (Fleet): fleet of servicers, introduced to homogenize "get_" methods implementation

        Return:
            (float): cost in Euros
        """
        # add up labour cost for each phase of the plan
        temp_cost = 0.
        for phase in self.phases:
            temp_cost = temp_cost + phase.get_operational_cost()
        return temp_cost.decompose()
    
    def get_moc_location_cost(self, fleet):
        """ Returns moc location cost.

        Arg:
            fleet (Fleet): fleet of servicers, introduced to homogenize "get_" methods implementation

        Return:
            (float): cost in Euros
        """
        labour_operations_fte = 10
        directors_fte = 2
        experts_fte = 5 * 0.2  # at 20%
        engineers_fte = 5
        constellation_ctrl_operators_fte = 2
        fds_operators_fte = 4
        it_fte = 2
        max_fte_operation = (labour_operations_fte + directors_fte + experts_fte + engineers_fte
                             + constellation_ctrl_operators_fte + fds_operators_fte + it_fte)
        # compute location cost
        fte_density = 1 / (10 * u.m * u.m)
        surface_cost = 350 / (u.m * u.m) / u.year
        surface = max_fte_operation / fte_density
        location_cost = surface * surface_cost * self.get_program_duration()
        return location_cost.decompose()

    def get_gnd_stations_cost(self, fleet):
        """ Returns ground stations location cost.

        Arg:
            fleet (Fleet): fleet of servicers that performed the plan

        Return:
            (float): cost in Euros
        """
        gnd_station_number = 5
        gnd_station_initial_investment = 20. * 1000. * gnd_station_number
        pass_per_day = 2. / (1. * u.day)
        pass_cost_per_day = 100. * pass_per_day
        total_passes_cost = pass_cost_per_day * self.get_program_duration()
        gnd_stations_cost = gnd_station_initial_investment + total_passes_cost
        return gnd_stations_cost.decompose()
        
    def reset(self):
        """ Reset the plan (mainly clear the orbits logged during the plan)."""
        for phase in self.phases:
            phase.reset()
                  
    def print_report(self):
        """ Print quick summary for debugging purposes."""
        print(self.id)
        print('Start : ' + str(self.starting_epoch))
        for phase in self.phases:
            print(phase)
                
    def __str__(self):
        temp = self.id
        for phase in self.phases:
            temp = temp + '\n\t' + phase.__str__()
        return temp
