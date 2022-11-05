from ScenarioDatabase.ACTConfigLinker.ACTConfigLinker import ACTConfigLinker
from ScenarioDatabase.ACTConfigLinker.ACTConfigIDs import *
from ScenarioDatabase.ScenarioInput.ScenarioInput import ScenarioInput

class ScenarioBaseSetupFromACT(ScenarioInput):
    act_db_linker = ACTConfigLinker()

    def open_act_config_json(self, json_filepath):
        self.act_db_linker.open_act_json(json_filepath)

    def read_act_config(self,act_config_name):
        self.read_kickstage_config(act_config_name)

    def read_kickstage_config(self,act_config_name):
        self.read_kickstage_diameter(act_config_name)

    def read_kickstage_diameter(self,act_config_name):
        param = self.act_db_linker.get_bb_parameter_value(act_config_name,BB_ID_KICKSTAGE,PARAM_ID_KICKSTAGE_DIAMETER)
        if self.act_db_linker.check_parameter_value(param):
            self.kickstage_diameter = float(param)

    def get_engines_name(self,act_config_name):
        pass

    def set_kickstage_engine(self,act_config_name,prop,system_name):
        pass