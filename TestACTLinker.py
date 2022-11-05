from ScenarioDatabase.ACTConfigLinker.ACTConfigLinker import ACTConfigLinker
from ScenarioDatabase.ACTConfigLinker.ACTConfigIDs import *

from ScenarioDatabase.ScenarioInput.ScenarioInputBase import ScenarioInputBase

config_name = "test_tcat_1"
act = ACTConfigLinker("ScenarioDatabase/Configurations.json")

bb = act.get_buildingblock(config_name,BB_ID_KICKSTAGE)
bb_params = act.get_buildingblock_parameters(config_name,BB_ID_KICKSTAGE)
bb_param = act.get_buildingblock_parameter(config_name,BB_ID_KICKSTAGE,PARAM_ID_KICKSTAGE_DIAMETER)
bb_param_val = act.get_buildingblock_parameter_value(config_name,BB_ID_KICKSTAGE,PARAM_ID_KICKSTAGE_DIAMETER)
bb_param_u = act.get_buildingblock_parameter_unit(config_name,BB_ID_KICKSTAGE,PARAM_ID_KICKSTAGE_DIAMETER)

configs = act.get_configs_name()
# kick_bb = act.get_buildingblock_kickstage(config_name)
# kick_diameter = act.get_kickstage_diameter(config_name)

si = ScenarioInputBase()
si.to_json_file("./my_new_json.json")

pass