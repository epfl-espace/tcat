"""
Created:        ?
Last Revision:  01.06.2022
Author:         ?,Emilien Mingard
Description:    Regroups all user parameter for the senario (margins, contingencies, etc...).
                Such parameters were previously defined loacally in the Senario's methods.
"""

from astropy import units as u

# Atmosphere limit
ALTITUDE_ATMOSPHERE_LIMIT = 80 * u.km

# The launcher reaches its orbit with a certain precision that can be defined here:
INSERTION_RAAN_MARGIN = 0 * u.deg # Defines the raan error.
INSERTION_A_MARGIN = 0 * u.km # Defines the semi-major axis error

# The servicer releases the satelilite when the target orbit is reached with a certain precision that can be defined here:
INSERTION_RAAN_WINDOW = 1 * u.deg # Defines the admissible range of RAAN around target orbit

# The models include contingencies to account for model errors:
CONTINGENCY_DELTA_V = 0.1 # dV added to computed dV for each manoeuvres

# Different models exist for a same type of manoeuvre, selection is based on certain criteria:
MODEL_RAAN_DIRECT_LIMIT = 8 * u.deg # criteria to select between direct RAAN change (small angles only) or use J2 model
MODEL_RAAN_DELTA_INCLINATION_HIGH = 10 *u.deg # higer bound of inclination change for RAAN phasing
MODEL_RAAN_DELTA_INCLINATION_LOW = 1e-3 * u.deg # lower bound of inclination change for RAAN phasing

# KickStage initial fuel mass
# KICKSTAGE_INITIAL_FUEL_MASS = 89.8 * u.kg
KICKSTAGE_REMAINING_FUEL_TOLERANCE = 1e-3 * u.kg
# KICKSTAGE_REMAINING_FUEL_MARGIN = 0. * u.kg
# KICKSTAGE_MAX_THRUST = 294000 * u.N
# KICKSTAGE_MIN_THRUST = 294000 * u.N
# KICKSTAGE_ISP_THRUST = 330 * u.s
KICKSTAGE_MAXTANK_CAPACITY = 5000 * u.kg
KICKSTAGE_FUEL_CONTINGENCY = 0.05
KICKSTAGE_PROP_MODULE_MASS_CONTINGENCY = 0.0

# KickStage initial dry mass
# KICKSTAGE_PROPULSION_DRY_MASS = 5 * u.kg
# KICKSTAGE_DISPENSER_DRY_MASS = 93.3 *  u.kg
# KICKSTAGE_STRUCT_MASS = 10 * u.kg

# Servicer masses
# SERVICER_INITIAL_FUEL_MASS = 100 * u.kg
# SERVICER_CAPTURE_DRY_MASS = 10 * u.kg
# SERVICER_MAX_THRUST = 294000 * u.N
# SERVICER_MIN_THRUST = 294000 * u.N
# SERVICER_ISP_THRUST = 330 * u.s
SERVICER_MAXTANK_CAPACITY = 5000 * u.kg
SERVICER_FUEL_CONTINGENCY = 0.05
SERVICER_PROP_MODULE_MASS_CONTINGENCY = 0.2
# SERVICER_PROPULSION_DRY_MASS = 20 * u.kg
# SERVICER_STRUCT_MASS = 5 * u.kg
# SERVICER_DEFAULT_VOLUME = 2.0 * u.m**3