# Created:          27.09.2022
# Last Revision:    07.12.2022
# Authors:          Mathieu Udriot
# Emails:           mathieu.udriot@epfl.ch
# Description:      Script to read input .csv file describing the trajectory and thrust curve needed to compute the atmoshperic impacts of a launch vehicle, to be used in ACT
import os

# imports
from scipy import interpolate, integrate
import numpy as np
import astropy.units as u
import csv
import json
from astropy.constants import g0
from matplotlib import pyplot

# global parameters
# atmospheric layers are defined below (https://www.noaa.gov/jetstream/atmosphere/layers-of-atmosphere):
# NOTE NB: the altitude of the layers depends on the latitude. The latitude of the launch site will thus have an impact on the decomposition of the atmosphere, but for now we assume Kourou for each.
ATM_EARTH_SURFACE = 0 * u.km
ATM_LIM_LOW_TROPOSPHERE = 10 * u.km
ATM_LIM_OZONE_LOW = 20 * u.km
ATM_LIM_OZONE_HIGH = 30 * u.km
ATM_LIM_STRATOSPHERE = 50 * u.km
ATM_LIM_MESOSPHERE = 85 * u.km
ALTITUDE_ATMOSPHERE_LIMIT = 200 * u.km

ATM_INCREMENT = 5 * u.km

PATH_CSV_THRUST_CURVES = "ACT_atmospheric_emissions/atm_thrust_curves/"
PATH_CSV_TRAJECTORIES = "ACT_atmospheric_emissions/atm_trajectories/"
PATH_ATM_RESULTS = "ACT_atmospheric_emissions/atm_results/"

INTERPOLATION_PLOT_STEP = 0.1

plotting = False

# local inputs to define launcher and engine
number_of_launch_es = 1

# launcher = "Vega_C"
# engine = "P120" # "Z40", "Z9"
# launcher = "Ariane_5"
# engine = "Vulcain" # "MPS", "HM7B"
launcher = "Themis_S1_reuse" # "Themis_T3"
engine = "T3_S1" # "T3_S2"

# For Vega C
# number_of_engine_s = 1 # [1, 1, 1] # this scales the emissions too.
# prop_type = 'APCP' # ['APCP', 'APCP', 'APCP']  # prop_type can be LOx/RP1, LOx/LH2, LOx/LCH4, NTO/UDMH, or APCP
# Isp = 278.5 * u.s # [278.5 * u.s, 295 * u.s, 296 * u.s]
# For Ariane 5
# number_of_engine_s = 1 # [1, 2, 1] # this scales the emissions too.
# prop_type = 'LOx/LH2' # ['LOx/LH2', 'APCP', 'LOx/LH2']  # prop_type can be LOx/RP1, LOx/LH2, LOx/LCH4, NTO/UDMH, or APCP
# Isp = 431 * u.s # [431 * u.s, 270 * u.s, 446 * u.s] 
# For Themis T3
number_of_engine_s = 3 # [3, 1] # this scales the emissions too.
prop_type = 'LOx/LCH4'  # prop_type can be LOx/RP1, LOx/LH2, LOx/LCH4, NTO/UDMH, or APCP
Isp = 320 * u.s # [320 * u.s, 350 * u.s]

# ignition and cutoff timestamps (here for Vega C)
# ignition_timestamp = 0 *u.s # [0 *u.s, 150 *u.s, 282 * u.s]
# cutoff_timestamp = 133 *u.s # [133 *u.s, 267 *u.s, 442 *u.s]
# ignition and cutoff timestamps (here for Ariane 5)
# ignition_timestamp = 0 *u.s # [0 *u.s, 7 *u.s, 580 * u.s]
# cutoff_timestamp = 531 *u.s # [531 *u.s, 142 *u.s, 1525 *u.s]
# ignition and cutoff timestamps (here for Themis T3 reusable)
ignition_timestamp = 0 *u.s # [0 *u.s, 200 *u.s]
cutoff_timestamp = 325 *u.s # [325 *u.s, 372.8 *u.s]

# NOTE assumption: the engine has only 1 ignition and 1 cutoff. Workaround: define a thrust curve that goes to 0 during ballistic time and goes "turns on" again 
# have the boundaries defined for the total duration of the thrust curve

# NOTE raw_trajectory and raw_thrust_curve corresponding to launcher trajectoy(ies) and engine(s) shall be given as input
# Trajectory (at least up to atmospheric limit)
# raw_trajectory = np.genfromtxt(f'{PATH_CSV_TRAJECTORIES}input_traj_{launcher}.csv', delimiter=",", skip_header=2)

# thrust curve of the engine
#raw_thrust_curve = np.genfromtxt(f'{PATH_CSV_THRUST_CURVES}thrust_curve_{engine}.csv', delimiter=",", skip_header=2)

def atm_main(TCAT_DIR, launcher, engine, number_of_engine_s, prop_type, Isp, ignition_timestamp, cutoff_timestamp, number_of_launch_es, raw_trajectory = None, raw_thrust_curve = None, plotting = False):

    if raw_trajectory is None:
        raw_trajectory = np.genfromtxt(f'{os.path.join(TCAT_DIR, PATH_CSV_TRAJECTORIES)}input_traj_{launcher}.csv', delimiter=",", skip_header=2)

    if raw_thrust_curve is None:
        raw_thrust_curve = np.genfromtxt(f'{os.path.join(TCAT_DIR, PATH_CSV_THRUST_CURVES)}thrust_curve_{engine}.csv', delimiter=",",
                                         skip_header=2)

    # creating a list of layer classes for the global atmosphere (cumulating the emissions of every engine)
    global_low_troposphere = layer("Low_troposphere", ATM_EARTH_SURFACE, ATM_LIM_LOW_TROPOSPHERE)
    global_high_troposphere = layer("High_troposphere", ATM_LIM_LOW_TROPOSPHERE, ATM_LIM_OZONE_LOW)
    global_ozone_layer = layer("Ozone_layer", ATM_LIM_OZONE_LOW, ATM_LIM_OZONE_HIGH)
    global_stratosphere = layer("Stratosphere", ATM_LIM_OZONE_HIGH, ATM_LIM_STRATOSPHERE)
    global_mesosphere = layer("Mesosphere", ATM_LIM_STRATOSPHERE, ATM_LIM_MESOSPHERE)
    global_thermosphere = layer("Thermosphere", ATM_LIM_MESOSPHERE, ALTITUDE_ATMOSPHERE_LIMIT)
    global_outer_space = layer("Outer_space", ALTITUDE_ATMOSPHERE_LIMIT, np.inf * u.km)
    global_atmosphere = [global_low_troposphere, global_high_troposphere, global_ozone_layer, global_stratosphere, global_mesosphere, global_thermosphere, global_outer_space]

    ### To use for finer atmospheric decomposition (also below for "atmosphere")
    # global_atmosphere = list()
    # for i in range(int(ALTITUDE_ATMOSPHERE_LIMIT.value/ATM_INCREMENT.value)):
    #     global_atmosphere.append(layer(f"Layer {i}", i*ATM_INCREMENT, (i+1)*ATM_INCREMENT))
    # global_atmosphere.append(layer("Outer_space", ALTITUDE_ATMOSPHERE_LIMIT, np.inf * u.km))

    max_kg_emission = 0

    # trajectory interpolation
    trajectory = interpolate.interp1d(raw_trajectory[:, 0], raw_trajectory[:, 1])
    x_trajectory = np.arange(min(raw_trajectory[:, 0]), max(raw_trajectory[:, 0]) + INTERPOLATION_PLOT_STEP, INTERPOLATION_PLOT_STEP)
    y_trajectory = trajectory(x_trajectory)
    # plot
    if plotting:
        fig, ax = pyplot.subplots(figsize=(5, 2.7), layout='constrained')
        ax.plot(raw_trajectory[:, 0], raw_trajectory[:, 1], 'ro', label = "raw")
        ax.plot(x_trajectory, y_trajectory, 'b', label = "Interpolation")
        ax.set_ylabel("h [km]")
        ax.set_xlabel("t [s]")
        ax.set_title("Launcher trajectory")
        ax.legend()
        fig.savefig(PATH_ATM_RESULTS + 'atm_' + launcher+ '_trajectory.png', bbox_inches='tight', dpi=100)

    # from thrust curve to prop mass flow (with Isp and g0)
    raw_m_dot_over_time = find_propellant_mass_flow(raw_thrust_curve, Isp)

    # prop mass flow interpolation
    m_dot_over_time = interpolate.interp1d(raw_thrust_curve[:, 0], raw_m_dot_over_time)
    x_mass_flow = np.arange(min(raw_thrust_curve[:, 0]), max(raw_thrust_curve[:, 0]) + INTERPOLATION_PLOT_STEP, INTERPOLATION_PLOT_STEP)
    y_mass_flow = m_dot_over_time(x_mass_flow)
    # plot
    if plotting:
        fig, ax = pyplot.subplots(figsize=(5, 2.7), layout='constrained')
        ax.plot(raw_thrust_curve[:, 0], raw_m_dot_over_time, 'ro', label = "raw")
        ax.plot(x_mass_flow, y_mass_flow, 'b--', label = "Interpolation")
        ax.set_ylabel("propellant mass flow [kg / s]")
        ax.set_xlabel("t [s]")
        ax.set_title("Propellant mass flow from thrust curve")
        ax.legend()
        fig.savefig(PATH_ATM_RESULTS + 'atm_' + engine + '_mass_flow.png', bbox_inches='tight', dpi=100)

    if x_mass_flow[-1] - x_mass_flow[0] != (cutoff_timestamp - ignition_timestamp).value:
        raise ValueError("Burn duration inconsistant between ignition and cutoff timestamps, and thrust curve duration (thrust curve not long enough).")

    # table of emissions per type of propellant [kg per kg of prop combusted]
    emissions_table = np.genfromtxt(os.path.join(TCAT_DIR, 'ACT_atmospheric_emissions/atm_emissions_per_propellant.csv'), delimiter=",", skip_header=2)[:,1:]
    
    propulsion_type_entries = np.genfromtxt(os.path.join(TCAT_DIR, 'ACT_atmospheric_emissions/atm_emissions_per_propellant.csv'), delimiter=",", skip_header=2, usecols=0, dtype=str)

    # creating list of layer classes for the atmosphere (reset to 0  for each engine)
    low_troposphere = layer("Low_troposphere", ATM_EARTH_SURFACE, ATM_LIM_LOW_TROPOSPHERE)
    high_troposphere = layer("High_troposphere", ATM_LIM_LOW_TROPOSPHERE, ATM_LIM_OZONE_LOW)
    ozone_layer = layer("Ozone_layer", ATM_LIM_OZONE_LOW, ATM_LIM_OZONE_HIGH)
    stratosphere = layer("Stratosphere", ATM_LIM_OZONE_HIGH, ATM_LIM_STRATOSPHERE)
    mesosphere = layer("Mesosphere", ATM_LIM_STRATOSPHERE, ATM_LIM_MESOSPHERE)
    thermosphere = layer("Thermosphere", ATM_LIM_MESOSPHERE, ALTITUDE_ATMOSPHERE_LIMIT)
    outer_space = layer("Outer_space", ALTITUDE_ATMOSPHERE_LIMIT, np.inf * u.km)
    atmosphere = [low_troposphere, high_troposphere, ozone_layer, stratosphere, mesosphere, thermosphere, outer_space]

    ### To use for finer atmospheric decomposition (also above for "global_atmosphere")
    # atmosphere = list()
    # for i in range(int(ALTITUDE_ATMOSPHERE_LIMIT.value/ATM_INCREMENT.value)):
    #     atmosphere.append(layer(f"{i}", i*ATM_INCREMENT, (i+1)*ATM_INCREMENT))
    # atmosphere.append(layer("Outer_space", ALTITUDE_ATMOSPHERE_LIMIT, np.inf * u.km))

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

    # Prepare printing results in a csv output file and results in a dictionary
    results_file_path = os.path.join(TCAT_DIR, PATH_ATM_RESULTS + "atm_" + launcher + "_" + engine + "_emissions.csv")
    header = ["Layer", "CO", "CO2", "H2O", "H", "O", "OH", "N2", "NO", "Al", "HCl", "Cl", "soot (BC)"]

    #with open(results_file_path, 'w') as w_file:
    #    writer = csv.writer(w_file)
    #    writer.writerow(header)
    
    atm_results_dict = {}

    for i in range(len(atmosphere)):
        atm_layer = atmosphere[i]
        atm_results_dict[atm_layer.name] = atm_layer.stored_emissions
        atm_layer.scale_by_launch_es(number_of_launch_es)
        # add total emissions in global layer to sum the contribution of different engines
        for j in range(len(atm_layer.stored_emissions)):
            global_atmosphere[i].stored_emissions[j] = global_atmosphere[i].stored_emissions[j] + atm_layer.stored_emissions[j]
        if max(global_atmosphere[i].stored_emissions) > max_kg_emission:
            max_kg_emission = max(global_atmosphere[i].stored_emissions)

        #atm_layer.write_results(results_file_path)
        #if plotting:
        #    atm_layer.plot_emissions_bar_chart(header, engine, launcher, number_of_launch_es)

    # Global plot of all contributions when there is a loop inside the function (input several engines of the same launcher)
    # y_pos = list(np.arange(len(header)-1))
    # fig, ax = pyplot.subplots(ncols=1, nrows=len(global_atmosphere)-1, figsize=(5, 1.75*len(atmosphere)))
    # for i in range(len(global_atmosphere)-1):
    #     ax[i].barh(y_pos, global_atmosphere[-2-i].stored_emissions)
    #     pyplot.setp(ax, yticks = y_pos, yticklabels = header[1:], xticks = [0, max_kg_emission])
    #     ax[i].set_title(f"{global_atmosphere[-2-i].name}" + " < " + f"{global_atmosphere[-2-i].upper_bound}.")
    # ax[-1].set_xlabel("Emissions [kg]")
    # # fig.suptitle("Emissions in atmosphere by " f"{launcher[run]} launcher, for " f"{number_of_launch_es} launch(es).")
    # fig.savefig(PATH_ATM_RESULTS + 'atm_' + launcher[run] + '.png', bbox_inches='tight', dpi=100) 

    # return json from dict() with key = name of the layer, and value is a list of the stored emissions (following the order "CO", "CO2", "H2O", "H", "O", "OH", "N2", "NO", "Al", "HCl", "Cl", "soot (BC)")
    return atm_results_dict
      
def find_propellant_mass_flow(thrust_curve, Isp):
    """
    Translate thust datapoints into propellant mass flow using the specific impulse [s] and the g0 constant

    output: list of propellant mass flow datapoints
    """
    m_dot_over_time = list()
    for i in range(len(thrust_curve[:, 0])):
        m_dot_over_time.append(thrust_curve[i, 1] * 1000 / Isp.value / g0.value) # convert to N from kN
    return m_dot_over_time

def integrate_mass_flow(m_dot_over_time, ignition_timestamp, cutoff_timestamp,  t_0, t_f, current_layer, propulsion_type_entries, emissions_table, prop_type, number_of_engine_s):
    """
    Integrate mass flow interpolation function between two timestamps

    Call layer class method to add the emissions associated with the burnt propellant
    """
    current_layer.add_to_duration(t_f-t_0)
    # test if engine is ignited between integral boundaries
    if ignition_timestamp > t_f or cutoff_timestamp < t_0:
        print(f"Engine not ignited in this layer ({current_layer.name}).")
        pass
    else:
        current_layer.change_affected_state()
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
        self.affected = False
        
        # stored emissions, updated everytime the engine spends time in the layer
        # "CO", "CO2", "H2O", "H", "O", "OH", "N2", "NO", "Al", "HCl", "Cl", "soot (BC)"
        self.stored_emissions = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 , 0]
  
    def get_lower_bound(self):
        return self.lower_bound
    
    def get_upper_bound(self):
        return self.upper_bound

    def change_affected_state(self):
        self.affected = True
            
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

    def plot_emissions_bar_chart(self, header, engine, launcher, number_of_launch_es):
        if self.affected == True:
            y_pos = list(np.arange(len(header)-1))
            fig, ax = pyplot.subplots(figsize=(5, 2.7))
            ax.barh(y_pos, self.stored_emissions)
            ax.set_xlabel("Emissions [kg]")
            pyplot.setp(ax, yticks = y_pos, yticklabels = header[1:])
            ax.set_title("Emissions in " f"{self.name} by {engine} engine, on {launcher} launcher, for " f"{number_of_launch_es} launch(es).")
            fig.savefig(PATH_ATM_RESULTS + 'atm_' + launcher + '_' + engine + '_' + self.name + '_.png', bbox_inches='tight', dpi=100)

