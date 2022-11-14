import json

class ACTConfigLinker:
    def __init__(self, json_filepath=None):
        self.act_db = []
        if json_filepath is not None:
            self.open_act_json_file(json_filepath)

    def open_act_json_file(self, json_filepath):
        with open(json_filepath, "r") as act_json_file:
            self.act_db = json.load(act_json_file)

    def open_act_json(self, json_str):
        self.act_db = json.loads(json_str)

    def check_parameter_value(self, param_value, parameter_name="not defined"):
        if param_value is None:
            print(f"Invalid value for parameter: {parameter_name}")
            return False
        return True

    ### higher level methods (to give examples on how to use module) ###

    def get_bb_parameter_value(self, config_name, bb_type_id, param_type_id, bb_name=None):
        config = self.get_config(config_name)
        bb = self.get_config_bb(config, bb_type_id, bb_name)
        param = self.get_bb_parameter(bb, param_type_id)
        return self.get_param_value(param)

    def get_bb_parameter_unit(self, config_name, bb_type_id, param_type_id, bb_name=None):
        config = self.get_config(config_name)
        bb = self.get_config_bb(config, bb_type_id, bb_name)
        param = self.get_bb_parameter(bb, param_type_id)
        return self.get_param_type_unit_name(param)

    def get_bb_child_name_filtered_type_id(self, config_name, bb_type_id, child_bb_type_id):
        config = self.get_config(config_name)
        servicer_bb = self.get_config_bb(config, bb_type_id)
        child_bbs = self.get_bb_child(servicer_bb)
        engine_bbs = self.filter_bbs_by_type_id(child_bbs, child_bb_type_id)
        if engine_bbs is None:
            return None
        elif len(engine_bbs) == 0:
            return None
        return self.get_bb_name(engine_bbs[0])

    ### Method to access fields from database

    def get_configs(self):
        if len(self.act_db) == 0:
            print("No configuration available")
            return None
        return self.act_db

    def get_config(self, config_name):
        for config in self.act_db:
            if self.get_config_name(config) == config_name:
                return config
        print(f"{config_name} config does not exist")
        return None

    ### Methods to access fields from configurations ###

    def check_config(self, config):
        if config is None:
            return False
        else:
            return True

    def get_config_id(self, config):
        if not self.check_config(config):
            return None
        if "id" not in config:
            print(f"config is missing a field: id")
            return None
        return config["id"]

    def get_config_name(self, config):
        if not self.check_config(config):
            return None
        if "name" not in config:
            print(f"{self.get_config_id(config)} config is missing a field: name")
            return None
        return config["name"]

    def get_config_type(self, config):
        if not self.check_config(config):
            return None
        if "configurationType" not in config:
            print(f"{self.get_config_id(config)} config is missing a field: configurationType")
            return None
        return config["configurationType"]

    def get_config_type_id(self, config):
        if self.get_config_type(config) is None:
            return None
        if "id" not in self.get_config_type(config):
            print(f"{self.get_config_id(config)}[type] is missing a field: id")
            return None
        return self.get_config_type(config)["id"]

    def get_config_type_name(self, config):
        if self.get_config_type(config) is None:
            return None
        if "name" not in self.get_config_type(config):
            print(f"{self.get_config_id(config)}[type] is missing a field: name")
            return None
        return self.get_config_type(config)["name"]

    def get_config_type_description(self, config):
        if self.get_config_type(config) is None:
            return None
        if "description" not in self.get_config_type(config):
            print(f"{self.get_config_id(config)}[type] is missing a field: description")
            return None
        return self.get_config_type(config)["description"]

    def get_config_bbs(self, config):
        if not self.check_config(config):
            return None
        if "buildingBlocks" not in config:
            print(f"{self.get_config_id(config)} config is missing a field: buildingBlocks")
            return None
        return config["buildingBlocks"]

    ### Methods to access and filter buildingblocks ###

    def get_config_bbs_filtered_type(self, config, bb_type_id):
        return self.filter_bbs_by_type_id(self.get_config_bbs(config), bb_type_id)

    def filter_bbs_by_type_id(self, bbs, bb_type_id):
        if bbs is None:
            return None
        bbs_filtered = list(filter(lambda bb: self.get_bb_type_id(bb) == bb_type_id, bbs))
        if len(bbs_filtered) == 0:
            print(f"No building block found with type id: {bb_type_id}")
            return None
        return bbs_filtered

    def filter_bbs_by_name(self, bbs, bb_name):
        if bbs is None:
            return None
        bbs_filtered = list(filter(lambda bb: self.get_bb_name(bb) == bb_name, bbs))
        if len(bbs_filtered) == 0:
            print(f"No building block found with name: {bb_name}")
            return None
        return bbs_filtered

    def filter_bbs_by_id(self, bbs, bb_id):
        if bbs is None:
            return None
        bbs_filtered = list(filter(lambda bb: self.get_bb_id(bb) == bb_id, bbs))
        if len(bbs_filtered) == 0:
            print(f"No building block found with id: {bb_id}")
            return None
        return bbs_filtered

    def get_config_bb(self, config, bb_type_id, bb_name=None):
        bbs = self.get_config_bbs(config)
        bbs = self.filter_bbs_by_type_id(bbs, bb_type_id)
        if bb_name is not None:
            bbs = self.filter_bbs_by_name(bbs, bb_name)
        if bbs is None:
            return None
        return bbs[0]

    ### Methods to access fields from unique building blocks ###

    def check_bb(self, bb):
        if bb is None:
            return False
        else:
            return True

    def get_bb_id(self, bb):
        if not self.check_bb(bb):
            return None
        if "id" not in bb:
            print(f"buildingblock is missing a field: id")
            return None
        return bb["id"]

    def get_bb_name(self, bb):
        if not self.check_bb(bb):
            return None
        if "name" not in bb:
            print(f"{self.get_bb_id(bb)} buildingblock is missing a field: name")
            return None
        return bb["name"]

    def get_bb_type(self, bb):
        if not self.check_bb(bb):
            return None
        if "buildingBlockType" not in bb:
            print(f"{self.get_bb_id(bb)} buildingblock is missing a field: buildingBlockType")
            return None
        return bb["buildingBlockType"]

    def get_bb_type_id(self, bb):
        if self.get_bb_type(bb) is None:
            return None
        if "id" not in self.get_bb_type(bb):
            print(f"{self.get_bb_id(bb)} buildingblock's type is missing a field: id")
            return None
        return self.get_bb_type(bb)["id"]

    def get_bb_type_name(self, bb):
        if self.get_bb_type(bb) is None:
            return None
        if "name" not in self.get_bb_type(bb):
            print(f"{self.get_bb_id(bb)} buildingblock's type is missing a field: name")
            return None
        return self.get_bb_type(bb)["name"]

    def get_bb_parameters(self, bb):
        if not self.check_bb(bb):
            return None
        if "parameters" not in bb:
            print(f"{self.get_bb_id(bb)} building block is missing a field: parameters")
            return None
        return bb["parameters"]

    def get_bb_parameter(self, bb, param_type_id):
        if self.get_bb_parameters(bb) is None:
            return None
        for param in self.get_bb_parameters(bb):
            if self.get_param_type_id(param) == param_type_id:
                return param
        print(f"{self.get_bb_id(bb)}[{param_type_id}] parameter does not exist")
        return None

    def get_bb_child(self, bb):
        if not self.check_bb(bb):
            return None
        if "childBlocks" not in bb:
            print(f"{self.get_bb_id(bb)} building block is missing a field: childBlocks")
        return bb["childBlocks"]

    ### Methods to access fields from parameters

    def check_param(self, param):
        if param is None:
            return False
        else:
            return True

    def get_param_id(self, param):
        if not self.check_param(param):
            return None
        if "id" not in param:
            print(f"parameter is missing a field: id")
            return None
        return param["id"]

    def get_param_value(self, param):
        if not self.check_param(param):
            return None
        if "value" not in param:
            print(f"{self.get_param_id(param)} parameter is missing a field: value")
            return None
        return param["value"]

    def get_param_type(self, param):
        if not self.check_param(param):
            return None
        if "type" not in param:
            print(f"{self.get_param_id(param)} parameter is missing a field: type")
            return None
        return param["type"]

    def get_param_type_id(self, param):
        if self.get_param_type(param) is None:
            return None
        if "id" not in self.get_param_type(param):
            print(f"{self.get_param_id(param)}[type] is missing a field: id")
            return None
        return self.get_param_type(param)["id"]

    def get_param_type_name(self, param):
        if self.get_param_type(param) is None:
            return None
        if "name" not in self.get_param_type(param):
            print(f"{self.get_param_id(param)}[type] is missing a field: name")
            return None
        return self.get_param_type(param)["name"]

    def get_param_type_unit(self, param):
        if self.get_param_type(param) is None:
            return None
        if "unit" not in self.get_param_type(param):
            print(f"{self.get_param_id(param)}[type] is missing a field: unit")
            return None
        return self.get_param_type(param)["unit"]

    def get_param_type_unit_name(self, param):
        if self.get_param_type_unit(param) is None:
            return None
        if "name" not in self.get_param_type_unit(param):
            print(f"{self.get_param_id(param)}[type][unit] is missing a field: name")
            return None
        return self.get_param_type_unit(param)["name"]

    def get_param_type_unit_id(self, param):
        if self.get_param_type_unit(param) is None:
            return None
        if "id" not in self.get_bb_param_type_unit(param):
            print(f"{self.get_param_id(param)}[type][unit] is missing a field: naidme")
            return None
        return self.get_param_type_unit(param)["id"]
