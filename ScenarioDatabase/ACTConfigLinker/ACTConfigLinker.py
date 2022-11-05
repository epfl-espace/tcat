import json

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

        print(f"{config_name} config does not exist")
        return None

    def get_buildingblock(self,config_name,buildingblock_id):
        config = self.get_config_dict(config_name)
        if config is None:
            return None
        
        for buildingblock in config["buildingBlocks"]:
            if buildingblock["buildingBlockType"]["id"] == buildingblock_id:
                return buildingblock

        print(f"{buildingblock_id} building block does not exist")
        return None

    def get_buildingblock_parameters(self,config_name,buildingblock_id):
        buildingblock = self.get_buildingblock(config_name,buildingblock_id)
        if buildingblock is None:
            return None
        if "parameters" not in buildingblock:
            print(f"{buildingblock_id} building block is missing field: parameters")
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
        
        print(f"{buildingblock_id}[{param_type_id}] parameter does not exist")
        return None

    def get_buildingblock_parameter_value(self,config_name,buildingblock_id,param_type_id):
        bb_param = self.get_buildingblock_parameter(config_name,buildingblock_id,param_type_id)
        if bb_param is None: 
            return None
        if "value" not in bb_param:
            print(f"{buildingblock_id}[{param_type_id}] parameter is missing field: value")
            return None

        return bb_param["value"]

    def get_buildingblock_parameter_unit(self,config_name,buildingblock_id,param_type_id):
        bb_param = self.get_buildingblock_parameter(config_name,buildingblock_id,param_type_id)
        if bb_param is None: 
            return None
        if "type" not in bb_param:
            print(f"{buildingblock_id}[{param_type_id}] parameter is missing field: type")
            return None
        if "unit" not in bb_param["type"]:
            print(f"{buildingblock_id}[{param_type_id}][type] is missing field: unit")
            return None 
        return bb_param["type"]["unit"]["name"]     