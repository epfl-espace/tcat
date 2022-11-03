import json

from numpy import empty

BB_ID_KICKSTAGE = "b02a2165-7e7c-4473-8e5c-1d7ca50dfa3e"
KICKSTAGE_PARAM_ID_DIAM = "527f86c2-e3f5-479b-aff4-1d304c7a4cbb"

class ACTConfigLinker:
    def __init__(self,json_filepath=None):
        self.act_db = []
        self.open_act_json(json_filepath)

    def open_act_json(self,json_filepath):
        with open(json_filepath,"r") as act_json_file:
            self.act_db = json.load(act_json_file)

    def get_configs_name(self):
        configs_name = []
        for config in self.act_db:
            configs_name.append(config["name"])
        return configs_name

    def get_config_dict(self,config_name):
        for config in self.act_db:
            if config["name"] == config_name:
                return config
        return None

    def get_buildingblock(self,config_name,buildingblock_id):
        config = self.get_config_dict(config_name)
        if config is None:
            return None
        
        for buildingblock in config["buildingBlocks"]:
            if buildingblock["buildingBlockType"]["id"] == buildingblock_id:
                return buildingblock
        return None

    def get_buildingblock_kickstage(self,config_name):
        return self.get_buildingblock(config_name,BB_ID_KICKSTAGE)

    def get_prameter_value(self,param_list,param_type_id):
        for param in param_list:
            if param["type"]["id"] == param_type_id:
                return param["value"]
        return None

    def get_kickstage_height(self, config_name):
        config_dict = self.get_configs_dict(config_name)
        if config_dict is None:
            return None
        

if __name__ == "__main__":
    config_name = "test_tcat_1"
    act = ACTConfigLinker("ScenarioDatabase/Configurations.json")
    configs = act.get_configs_name()
    bb = act.get_buildingblock(config_name,BB_ID_KICKSTAGE)
    bb_kick = act.get_buildingblock_kickstage(config_name)
    pass