"""
Created:        ?
Last Revision:  01.06.2022
Author:         ?,Emilien Mingard
Description:    Regroups all user parameter for the senario (margins, contingencies, etc...).
                Such parameters were previously defined loacally in the Senario's methods.
"""

from astropy import units as u

# The launcher reaches its orbit with a certain precision that can be defined here:
INSERTION_RAAN_MARGIN = 0 * u.deg # Defines the raan error.
INSERTION_A_MARGIN = 0 * u.km # Defines the semi-major axis error

# The servicer releases the satelilite when the target orbit is reached with a certain precision that can be defined here:
INSERTION_RAAN_WINDOW = 1 * u.deg # Defines the admissible range of RAAN around target orbit

# The models include contingencies to account for model errors:
CONTINGENCY_DELTA_V = 0.1 # dV added to computed dV for each manoeuvres

# Different models exist for a same type of manoeuvre, selection is based on certain criteria:
MODEL_RAAN_DIRECT_LIMIT = 8 * u.deg # criteria to select between direct RAAN change (small angles only) or use J2 model

# Define the input json name and path here (can also use argv[1])
SCENARIO_INPUT_JSON = "Constellation_new_v1.json"