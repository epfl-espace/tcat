import json

class ACTConfigLinker:
    def __init__(self,json_filepath=None):
        self.act_db = []
        if json_filepath is not None:
            self.open_act_json(json_filepath)

    ### public methods ###

    def open_act_json(self,json_filepath):
        with open(json_filepath,"r") as act_json_file:
            self.act_db = json.load(act_json_file)

    def get_all_configs_name(self):
        configs_name = []
        for config in self.act_db:
            configs_name.append(self.get_config_name(config))
        return configs_name

    def get_bb_parameter_value(self,config_name,bb_type_id,param_type_id,bb_name=None):
        config = self.get_config(config_name)
        bb = self.get_config_bb(config,bb_type_id,bb_name)
        param = self.get_bb_parameter(bb,param_type_id)
        return self.get_param_value(param)

    def get_bb_parameter_unit(self,config_name,bb_type_id,param_type_id,bb_name=None):
        config = self.get_config(config_name)
        bb = self.get_config_bb(config,bb_type_id,bb_name)
        param = self.get_bb_parameter(bb,param_type_id)
        return self.get_param_type_unit_name(param)

    def get_bbs_name(self,config_name,bb_type_id):
        config = self.get_config(config_name)
        bbs = self.get_config_bbs(config)

        return self.get_bbs_name(bbs)

    def check_parameter_value(self,param_value):
        if param_value is None:
            return False
        return True

    ### Method to access fields from database

    def get_config(self,config_name):
        for config in self.act_db:
            if self.get_config_name(config) == config_name:
                return config
        print(f"{config_name} config does not exist")
        return None

    ### Methods to access fields from configurations ###

    def check_config(self,config):
        if config is None:
            return False
        else:
            return True

    def get_config_id(self,config):
        if not self.check_config(config):
            return None
        if "id" not in config:
            print(f"config is missing a field: id")
            return None
        return config["id"]

    def get_config_name(self,config):
        if not self.check_config(config):
            return None
        if "name" not in config:
            print(f"{self.get_config_id(config)} config is missing a field: name")
            return None
        return config["name"]    

    def get_config_bbs(self,config):
        if not self.check_config(config):
            return None
        if "buildingBlocks" not in config:
            print(f"{self.get_config_id(config)} config is missing a field: buildingBlocks")
            return None
        return config["buildingBlocks"]

    def get_config_bbs_filtered_type(self,config,bb_type_id):
        if not self.check_config(config):
            return None
        if self.get_config_bbs(config) is None:
            return None
        bbs = []
        for bb in self.get_config_bbs(config):
            if self.get_bb_type_id(bb) == bb_type_id:
                bbs.append(bb)
        if len(bbs) == 0:
            print(f"No building block found with type id: {bb_type_id}")
            return None
        return bbs

    def get_config_bb(self,config,bb_type_id,bb_name=None):
        bbs = self.get_config_bbs_filtered_type(config,bb_type_id)
        if bbs is None:
            return None
        if bb_name is None:
            return bbs[0]
        for bb in bbs:
            if self.get_bb_name(bb) == bb_name:
                return bb
        return None

    ### Methods to access fields from unique building blocks ###

    def check_bb(self,bb):
        if bb is None:
            return False
        else:
            return True

    def get_bb_id(self,bb):
        if not self.check_bb(bb):
            return None
        if "id" not in bb:
            print(f"buildingblock is missing a field: id")
            return None
        return bb["id"]

    def get_bb_name(self,bb):
        if not self.check_bb(bb):
            return None
        if "name" not in bb:
            print(f"{self.get_bb_id(bb)} buildingblock is missing a field: name")
            return None
        return bb["name"]

    def get_bb_type(self,bb):
        if not self.check_bb(bb):
            return None
        if "buildingBlockType" not in bb:
            print(f"{self.get_bb_id(bb)} buildingblock is missing a field: buildingBlockType")
            return None
        return bb["buildingBlockType"]

    def get_bb_type_id(self,bb):
        if not self.check_bb(bb):
            return None
        if self.get_bb_type(bb) is None:
            return None
        if "id" not in self.get_bb_type(bb):
            print(f"{self.get_bb_id(bb)} buildingblock's type is missing a field: id")
            return None
        return self.get_bb_type(bb)["id"] 

    def get_bb_type_name(self,bb):
        if not self.check_bb(bb):
            return None
        if self.get_bb_type(bb) is None:
            return None
        if "name" not in self.get_bb_type(bb):
            print(f"{self.get_bb_id(bb)} buildingblock's type is missing a field: name")
            return None
        return self.get_bb_type(bb)["name"] 

    def get_bb_parameters(self,bb):
        if not self.check_bb(bb):
            return None
        if "parameters" not in bb:
            print(f"{self.get_bb_id(bb)} building block is missing a field: parameters")
            return None
        return bb["parameters"]

    def get_bb_parameter(self,bb,param_type_id):
        if not self.check_bb(bb):
            return None
        if self.get_bb_parameters(bb) is None: 
            return None
        for param in self.get_bb_parameters(bb):
                if self.get_param_type_id(param) == param_type_id:
                    return param
        print(f"{self.get_bb_id(bb)}[{param_type_id}] parameter does not exist")
        return None

    ### Methods to access fields from multiple building blocks ###

    def get_bbs_name(self,bbs):
        if bbs is None:
            return None
        bb_names = []
        for bb in bbs:
            bb_names.append(self.get_bb_name(bb))
        return bb_names

    ### Methods to access fields from parameters

    def check_param(self,param):
        if param is None:
            return False
        else:
            return True
    
    def get_param_id(self,param):
        if not self.check_param(param):
            return None
        if "id" not in param:
            print(f"parameter is missing a field: id")
            return None
        return param["id"]

    def get_param_value(self,param):
        if not self.check_param(param):
            return None
        if "value" not in param:
            print(f"{self.get_param_id(param)} parameter is missing a field: value")
            return None
        return param["value"]

    def get_param_type(self,param):
        if not self.check_param(param):
            return None
        if "type" not in param:
            print(f"{self.get_param_id(param)} parameter is missing a field: type")
            return None
        return param["type"]

    def get_param_type_id(self,param):
        if not self.check_param(param):
            return None
        if self.get_param_type(param) is None:
            return None
        if "id" not in self.get_param_type(param):
            print(f"{self.get_param_id(param)}[type] is missing a field: id")
            return None
        return self.get_param_type(param)["id"]

    def get_param_type_name(self,param):
        if not self.check_param(param):
            return None
        if self.get_param_type(param) is None:
            return None
        if "name" not in self.get_param_type(param):
            print(f"{self.get_param_id(param)}[type] is missing a field: name")
            return None
        return self.get_param_type(param)["name"]

    def get_param_type_unit(self,param):
        if not self.check_param(param):
            return None
        if self.get_param_type(param) is None:
            return None
        if "unit" not in self.get_param_type(param):
            print(f"{self.get_param_id(param)}[type] is missing a field: unit")
            return None
        return self.get_param_type(param)["unit"]

    def get_param_type_unit_name(self,param):
        if not self.check_param(param):
            return None
        if self.get_param_type_unit(param) is None:
            return None
        if "name" not in self.get_param_type_unit(param):
            print(f"{self.get_param_id(param)}[type][unit] is missing a field: name")
            return None
        return self.get_param_type_unit(param)["name"]

    def get_param_type_unit_id(self,param):
        if not self.check_param(param):
            return None
        if self.get_param_type_unit(param) is None:
            return None
        if "id" not in self.get_bb_param_type_unit(param):
            print(f"{self.get_param_id(param)}[type][unit] is missing a field: naidme")
            return None
        return self.get_param_type_unit(param)["id"]