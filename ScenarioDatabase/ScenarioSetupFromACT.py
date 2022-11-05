from dataclasses import dataclass

from ScenarioDatabase.ACTConfigLinker.ACTConfigLinker import ACTConfigLinker
from ScenarioDatabase.ACTConfigLinker.ACTConfigIDs import *
from ScenarioDatabase.ScenarioInput.ScenarioInput import ScenarioInput

@dataclass
class ScenarioSetupFromACT(ScenarioInput,ACTConfigLinker):
    pass

# class ACTConfigLinker(ACTConfigLinkerBase):
#     def __init__(self,json_filepath=None):
#         super().__init__(json_filepath)

#     def get_buildingblock_kickstage(self,config_name):
#         return self.get_buildingblock(config_name,BB_ID_KICKSTAGE)

#     def get_kickstage_diameter(self, config_name):
#         return self.get_buildingblock_parameter_value(config_name,BB_ID_KICKSTAGE,PARAM_ID_KICKSTAGE_DIAMETER)