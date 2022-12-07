# Created:          27.09.2022
# Last Revision:    07.12.2022
# Authors:          Mathieu Udriot
# Emails:           mathieu.udriot@epfl.ch
# Description:      Script to read input .csv file describing the trajectory and thrust curve needed to compute the atmoshperic impacts of a launch vehicle, to be used in ACT

# import class
from Scenarios.ScenarioParameters import *

# imports
from scipy import interpolate, integrate
import numpy as np
import astropy.units as u
import csv
from astropy.constants import g0
from matplotlib import pyplot 

INTERPOLATION_PLOT_STEP = 0.1

plotting = True

# local inputs to define launcher and engine
launcher = "Vega_C"
engine = "Z40"
number_of_launch_es = 1

# launcher = "Themis_S1_reuse"
# engine = "T3_S1"

number_of_engine_s = 1 # if several engines used in parallel (Prometheus), this scales the emissions too.
prop_type = 'APCP' # prop_type can be LOx/RP1, LOx/LH2, LOx/LCH4, NTO/UDMH, or APCP
Isp = 295 * u.s # 270 for MPS, 431 for Vulcain, 320 for S1, 350 for S2, 278.5 for P120, 295 s for Z40

# ignition and cutoff timestamps (here for Ariane 5 EAP)
ignition_timestamp = 150 *u.s
cutoff_timestamp = 267 *u.s
# ignition and cutoff timestamps (here for Ariane 5 EPC)
# ignition_timestamp = 0 *u.s
# cutoff_timestamp = 531 *u.s

# NOTE assumption: the engine has only 1 ignition and 1 cutoff. Workaround: define a thrust curve that goes to 0 during ballistic time and goes "turns on" again 
# have the boundaries defined for the total duration of the thrust curve

# Trajectory (at least up to atmospheric limit)
raw_trajectory = np.genfromtxt(f'{PATH_CSV_TRAJECTORIES}input_traj_{launcher}.csv', delimiter=",", skip_header=2)

# thrust curve of the engine
raw_thrust_curve = np.genfromtxt(f'{PATH_CSV_THRUST_CURVES}thrust_curve_{engine}.csv', delimiter=",", skip_header=2)

def atm_main(launcher, engine, number_of_engine_s, prop_type, Isp, raw_trajectory, raw_thrust_curve, number_of_launch_es, plotting):
    
    if number_of_engine_s < 0:
        raise ValueError("Number of engine(s) must be a positive integer.")
    if Isp < 0:
        raise ValueError("Specific impulse must be positive [s].")
    if number_of_launch_es < 0:
        raise ValueError("Number of launch(es) must be a positive integer.")

    # trjaectory interpolation
    trajectory = interpolate.interp1d(raw_trajectory[:, 0], raw_trajectory[:, 1])
    x_trajectory = np.arange(min(raw_trajectory[:, 0]), max(raw_trajectory[:, 0]) + INTERPOLATION_PLOT_STEP, INTERPOLATION_PLOT_STEP)
    y_trajectory = trajectory(x_trajectory)
    # plot
    if plotting == True:
        fig, ax = pyplot.subplots(figsize=(5, 2.7), layout='constrained')
        ax.plot(raw_trajectory[:, 0], raw_trajectory[:, 1], 'ro', label = "raw")
        ax.plot(x_trajectory, y_trajectory, 'b', label = "Interpolation")
        ax.set_ylabel("h [km]")
        ax.set_xlabel("t [s]")
        ax.set_title("Launcher trajectory")
        ax.legend()
        fig.savefig(PATH_ATM_RESULTS + 'atm_' + launcher + '_trajectory.png', bbox_inches='tight', dpi=100)

    # from thrust curve to prop mass flow (with Isp and g0)
    raw_m_dot_over_time = find_propellant_mass_flow(raw_thrust_curve, Isp)

    # prop mass flow interpolation
    m_dot_over_time = interpolate.interp1d(raw_thrust_curve[:, 0], raw_m_dot_over_time)
    x_mass_flow = np.arange(min(raw_thrust_curve[:, 0]), max(raw_thrust_curve[:, 0]) + INTERPOLATION_PLOT_STEP, INTERPOLATION_PLOT_STEP)
    y_mass_flow = m_dot_over_time(x_mass_flow)
    # plot
    if plotting == True:
        fig, ax = pyplot.subplots(figsize=(5, 2.7), layout='constrained')
        ax.plot(raw_thrust_curve[:, 0], raw_m_dot_over_time, 'ro', label = "raw")
        ax.plot(x_mass_flow, y_mass_flow, 'b--', label = "Interpolation")
        ax.set_ylabel("propellant mass flow [tons / s]")
        ax.set_xlabel("t [s]")
        ax.set_title("Propellant mass flow from thrust curve")
        ax.legend()
        fig.savefig(PATH_ATM_RESULTS + 'atm_' + engine + '_mass_flow.png', bbox_inches='tight', dpi=100)

    if x_mass_flow[-1] - x_mass_flow[0] != (cutoff_timestamp - ignition_timestamp).value:
        raise ValueError("Burn duration inconsistant between ignition and cutoff timestamps, and thrust curve duration (thrust curve not long enough).")

    # table of emissions per type of propellant [kg per kg of prop combusted]
    emissions_table = np.genfromtxt(f'atm_emissions_per_propellant.csv', delimiter=",", skip_header=2)[:,1:]
    
    propulsion_type_entries = np.genfromtxt(f'atm_emissions_per_propellant.csv', delimiter=",", skip_header=2, usecols=0, dtype=str)

    # creating list of layer classes for the atmosphere
    low_troposphere = layer("Low_troposphere", ATM_EARTH_SURFACE, ATM_LIM_LOW_TROPOSPHERE)
    high_troposphere = layer("High_troposphere", ATM_LIM_LOW_TROPOSPHERE, ATM_LIM_OZONE_LOW)
    ozone_layer = layer("Ozone_layer", ATM_LIM_OZONE_LOW, ATM_LIM_OZONE_HIGH)
    stratosphere = layer("Stratosphere", ATM_LIM_OZONE_HIGH, ATM_LIM_STRATOSPHERE)
    mesosphere = layer("Mesosphere", ATM_LIM_STRATOSPHERE, ATM_LIM_MESOSPHERE)
    thermosphere = layer("Thermosphere", ATM_LIM_MESOSPHERE, ALTITUDE_ATMOSPHERE_LIMIT)
    outer_space = layer("Outer_space", ALTITUDE_ATMOSPHERE_LIMIT, np.inf * u.km)

    atmosphere = [low_troposphere, high_troposphere, ozone_layer, stratosphere, mesosphere, thermosphere, outer_space]

    # from trajectory to time spent in layers (with limits)
    current_layer_index = 0
    ascending = True
    altitude_temp = ATM_EARTH_SURFACE
    time_temp = 0 * u.s
    i = 0
    current_layer = atmosphere[current_layer_index]
    print("Take-off !")

    while i < len(x_trajectory) - 2:
        if ascending:
            while y_trajectory[i] < current_layer.get_upper_bound().value and i < len(x_trajectory) - 2:
                i += 1
                if y_trajectory[i] > y_trajectory[i+1]:
                    ascending = False
                    altitude_temp = y_trajectory[i] * u.km
                    # print(i, "Altitude", altitude_temp, ", ascending", ascending)
                    break
            if i == len(x_trajectory) - 2:
                time_final = x_trajectory[i] * u.s
                integrate_mass_flow(m_dot_over_time, ignition_timestamp, cutoff_timestamp, time_temp, time_final, current_layer, propulsion_type_entries, emissions_table, prop_type, number_of_engine_s)
                pass
            elif ascending: # meaning we are moving one layer above
                altitude_temp = y_trajectory[i] * u.km
                # print(i, "Altitude", altitude_temp, ", ascending", ascending)
                time_final = x_trajectory[i] * u.s
                integrate_mass_flow(m_dot_over_time, ignition_timestamp, cutoff_timestamp, time_temp, time_final, current_layer, propulsion_type_entries, emissions_table, prop_type, number_of_engine_s)
                time_temp = time_final
                current_layer_index += 1
                current_layer = atmosphere[current_layer_index]
                if current_layer_index == len(atmosphere) - 1:
                    print("Going out of atmosphere")
        else:
            while y_trajectory[i] > current_layer.get_lower_bound().value and i < len(x_trajectory) - 2:
                i += 1
                if y_trajectory[i] < y_trajectory[i+1]:
                    ascending = True
                    altitude_temp = y_trajectory[i] * u.km
                    # print(i, "Altitude", altitude_temp, ", ascending", ascending)
                    break
            if i == len(x_trajectory) - 2:
                time_final = x_trajectory[i] * u.s
                integrate_mass_flow(m_dot_over_time, ignition_timestamp, cutoff_timestamp, time_temp, time_final, current_layer, propulsion_type_entries, emissions_table, prop_type, number_of_engine_s)
                if y_trajectory[-1] == 0:
                    print("Landed back.")
                pass
            elif not ascending: # meaning we are moving one layer below
                altitude_temp = y_trajectory[i] * u.km
                # print(i, "Altitude", altitude_temp, ", ascending", ascending)
                time_final = x_trajectory[i] * u.s
                integrate_mass_flow(m_dot_over_time, ignition_timestamp, cutoff_timestamp, time_temp, time_final, current_layer, propulsion_type_entries, emissions_table, prop_type, number_of_engine_s)
                time_temp = time_final
                current_layer_index -= 1
                current_layer = atmosphere[current_layer_index]

    # Prepare printing results in a csv output file
    results_file_path = PATH_ATM_RESULTS + "atm_" + launcher + "_" + engine + "_emissions.csv"

    with open(results_file_path, 'w') as w_file:
        writer = csv.writer(w_file)
        header = ["Layer", "CO", "CO2", "H2O", "H", "O", "OH", "N2", "NO", "Al", "HCl", "Cl", "soot (BC)"]
        writer.writerow(header)
    
    for atm_layer in atmosphere:
        atm_layer.scale_by_launch_es(number_of_launch_es)
        atm_layer.write_results(results_file_path)
      
def find_propellant_mass_flow(thrust_curve, Isp):
    """
    Translate thust datapoints into propellant mass flow using the specific impulse [s] and the g0 constant

    output: list of propellant mass flow datapoints
    """
    m_dot_over_time = list()
    for i in range(len(thrust_curve[:, 0])):
        m_dot_over_time.append(thrust_curve[i, 1] / Isp.value / g0.value)
    return m_dot_over_time

def integrate_mass_flow(m_dot_over_time, ignition_timestamp, cutoff_timestamp,  t_0, t_f, current_layer, propulsion_type_entries, emissions_table, prop_type, number_of_engine_s):
    """
    Integrate mass flow interpolation function between two timestamps

    Call layer class method to add the emissions associated with the burnt propellant
    """
    # test if engine is ignited between integral boundaries
    if ignition_timestamp > t_f or cutoff_timestamp < t_0:
        print(f"Engine not ignited in this layer ({current_layer.name}).")
        pass
    else:
        # find applicable integral boundaries
        if ignition_timestamp > t_0:
            t_0 = ignition_timestamp
        if cutoff_timestamp < t_f:
            t_f = cutoff_timestamp
        
        mass_propellant_burnt = integrate.quad(m_dot_over_time, (t_0 - ignition_timestamp).value, (t_f - ignition_timestamp).value)

        current_layer.add_emissions(prop_type, propulsion_type_entries, emissions_table, mass_propellant_burnt, number_of_engine_s)


class layer:
    def __init__(self, name = "default", lower_bound = 0 * u.km, upper_bound = 10 * u.km):
        self.name = name
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.duration = 0 * u.s
        
        # stored emissions, updated everytime the engine spends time in the layer
        # "CO", "CO2", "H2O", "H", "O", "OH", "N2", "NO", "Al", "HCl", "Cl", "soot (BC)"
        self.stored_emissions = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 , 0]
  
    def get_lower_bound(self):
        return self.lower_bound
    
    def get_upper_bound(self):
        return self.upper_bound
            
    def add_to_duration(self, additional_time):
        self.duration += additional_time

    def get_duration(self):
        return self.duration 

    def add_emissions(self, prop_type, propulsion_type_entries, emissions_table, mass_propellant_burnt, number_of_engine_s):
        if not prop_type in propulsion_type_entries:
            raise ValueError("Emissions from this propulsion type are not known.")
        else:
            i = 0
            while propulsion_type_entries[i] != prop_type:
                i += 1
            for j in range(len(emissions_table[i, :])):
                self.stored_emissions[j] = self.stored_emissions[j] + number_of_engine_s*mass_propellant_burnt[0]*emissions_table[i, j]
            
    def scale_by_launch_es(self, number_of_launch_es):
        for i in range(len(self.stored_emissions)):
            self.stored_emissions[i] = self.stored_emissions[i]*number_of_launch_es
        print(f"Layer {self.name}", " cumulatively suffers ", f"{self.stored_emissions[1]:.3f} of CO2,", f"{self.stored_emissions[2]:.3f} of H2O", f"{self.stored_emissions[8]:.3f} of Al", 
                    f"{self.stored_emissions[11]:.3f} of soot.")

    # to write results of emissions per layer in export table (.csv)
    def write_results(self, results_path):
        with open(results_path, 'a') as w_file:
            writer = csv.writer(w_file)
            data = [self.name] + self.stored_emissions
            writer.writerow(data)

atm_main(launcher, engine, number_of_engine_s, prop_type, Isp, raw_trajectory, raw_thrust_curve, number_of_launch_es, plotting)