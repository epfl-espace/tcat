import json

BB_ID_KICKSTAGE = "b02a2165-7e7c-4473-8e5c-1d7ca50dfa3e"
PARAM_ID_KICKSTAGE_DIAMETER = "527f86c2-e3f5-479b-aff4-1d304c7a4cbb"

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

    def get_buildingblock_parameters(self,config_name,buildingblock_id):
        buildingblock = self.get_buildingblock(config_name,buildingblock_id)
        if buildingblock is None:
            return None
        return buildingblock["parameters"]

    def get_buildingblock_parameter(self,config_name,buildingblock_id,param_type_id):
        bb_params = self.get_buildingblock_parameters(config_name,buildingblock_id)
        if bb_params is None: 
            return None

        for param in bb_params:
            if "type" in param:
                if param["type"]["id"] == param_type_id:
                    return param
        return None

    def get_buildingblock_parameter_value(self,config_name,buildingblock_id,param_type_id):
        bb_param = self.get_buildingblock_parameter(config_name,buildingblock_id,param_type_id)
        if bb_param is None: 
            return None
        return bb_param["value"]

    def get_buildingblock_parameter_unit(self,config_name,buildingblock_id,param_type_id):
        bb_param = self.get_buildingblock_parameter(config_name,buildingblock_id,param_type_id)
        if bb_param is None: 
            return None
        if "type" in bb_param:
            if "unit" in bb_param["type"]:
                return bb_param["type"]["unit"]["name"]
        return None

    def get_buildingblock_kickstage(self,config_name):
        return self.get_buildingblock(config_name,BB_ID_KICKSTAGE)

    def get_kickstage_diameter(self, config_name):
        return self.get_buildingblock_parameter_value(config_name,BB_ID_KICKSTAGE,PARAM_ID_KICKSTAGE_DIAMETER)      

if __name__ == "__main__":
    config_name = "test_tcat_1"
    act = ACTConfigLinker("ScenarioDatabase/Configurations.json")
    configs = act.get_configs_name()

    bb = act.get_buildingblock(config_name,BB_ID_KICKSTAGE)
    bb_params = act.get_buildingblock_parameters(config_name,BB_ID_KICKSTAGE)
    bb_param = act.get_buildingblock_parameter(config_name,BB_ID_KICKSTAGE,PARAM_ID_KICKSTAGE_DIAMETER)
    bb_param_val = act.get_buildingblock_parameter_value(config_name,BB_ID_KICKSTAGE,PARAM_ID_KICKSTAGE_DIAMETER)
    bb_param_u = act.get_buildingblock_parameter_unit(config_name,BB_ID_KICKSTAGE,PARAM_ID_KICKSTAGE_DIAMETER)

    bb_kick = act.get_buildingblock_kickstage(config_name)
    kick_diameter = act.get_kickstage_diameter(config_name)
    pass