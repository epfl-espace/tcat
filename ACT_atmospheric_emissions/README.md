# TCAT - ACT compatibility
## Atmospheric emissions of launchers
All files and folders starting with atm_ are for the calculation of the atmospheric emissions during a launch.

Run the atmospheric emissions (ATM) code by using the command: _python atm_run_code.py_

For now the inputs have to be changed in atm_run_code.py. The script will be accessed with an API, from ACT, entering method atm_main() which verifies the inputs and perform the calculations.

The _atm_main()_ method starts by interpolating the provided trajectory and the mass flow curve (extracted from the input thrust curve). They can be plotted if the Boolean "PLOTTING" is True.

The table atm_emissions_per_propellant.csv is imported, it holds values of emissions (in kg for 12 species: "CO", "CO2", "H2O", "H", "O", "OH", "N2", "NO", "Al", "HCl", "Cl", "soot (BC)") per kig of burnt propellant. Propellants in the table are:
1. LOx/RP1
2. LOx/LH2
3. LOx/LCH4
4. NTO/UDMH
5. APCP
A list of layer classes to define the atmosphere made of several layers, is created, based on gloabl parameters defining the limits.

From the interpolated trajectory, timestamps at which the engine crosses the limit between two layers are found. The code accepts trajectories going down again (for propulsive reusable LVs or for ascent that have a coast phase like Ariane 5). Between these timestamps, the mass flow curvbe is integrated to find the mass of propellant burnt in each layer. This value is used with the atm_emissions_per_propellant table to find the mass of emissions.

The output is scaled by the number of engines and launches.