from ScenarioDatabase.ACTConfigLinker.ACTConfigLinker import ACTConfigLinker
from ScenarioDatabase.ACTConfigLinker.ACTConfigIDs import *
from ScenarioDatabase.ScenarioInput.ScenarioInput import ScenarioInput

class ScenarioBaseSetupFromACT(ScenarioInput):
    act_db_linker = ACTConfigLinker()

    def open_act_config_json(self, json_filepath):
        self.act_db_linker.open_act_json(json_filepath)

    def read_act_config(self,act_config_name):
        self.read_mission_config(act_config_name)
        self.read_constellation_config(act_config_name)
        self.read_launcher_config(act_config_name)
        self.read_kickstage_config(act_config_name)
        self.read_orbital_config(act_config_name)

    ### Read Mission Config ###

    def read_mission_config(self,act_config_name):
        self.read_mission_starting_epoch(act_config_name)

    def read_mission_starting_epoch(self,act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value(\
            act_config_name,BB_ID_MISSION,PARAM_ID_STARTING_EPOCH)
        if self.act_db_linker.check_parameter_value(param_value):
            self.starting_epoch = str(param_value)

    ### Read Constellation Config ###

    def read_constellation_config(self,act_config_name):
        pass

    ### Read Launcher Config ###

    def read_launcher_config(self,act_config_name):
        self.read_launcher_name(act_config_name)
        self.read_launcher_launch_site(act_config_name)
        self.read_launcher_orbit_type(act_config_name)
        self.read_launcher_fairing_diameter(act_config_name)
        self.read_launcher_height_cylinder(act_config_name)
        self.read_launcher_height_total(act_config_name)

    def read_launcher_name(self,act_config_name):
        config = self.act_db_linker.get_config(act_config_name)
        name = self.act_db_linker.get_config_name(config)
        if self.act_db_linker.check_parameter_value(name):
            self.launcher_name = str(name)

    def read_launcher_launch_site(self,act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value(\
            act_config_name,BB_ID_MISSION,PARAM_ID_LAUNCH_SITE)
        if self.act_db_linker.check_parameter_value(param_value):
            self.launcher_launch_site = str(param_value)

    def read_launcher_orbit_type(self,act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value(\
            act_config_name,BB_ID_UPPERSTAGE,PARAM_ID_ORBIT_TYPE)
        if self.act_db_linker.check_parameter_value(param_value):
            self.launcher_orbit_type = str(param_value)

    def read_launcher_fairing_diameter(self,act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value(\
            act_config_name,BB_ID_FAIRING,PARAM_ID_DIAMETER)
        if self.act_db_linker.check_parameter_value(param_value):
            self.launcher_fairing_diameter = float(param_value)

    def read_launcher_height_cylinder(self,act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value(\
            act_config_name,BB_ID_FAIRING,PARAM_ID_LENGTH_CYLINDER)
        if self.act_db_linker.check_parameter_value(param_value):
            self.launcher_fairing_cylinder_height = float(param_value)

    def read_launcher_height_total(self,act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value(\
            act_config_name,BB_ID_FAIRING,PARAM_ID_LENGTH_TOTAL)
        if self.act_db_linker.check_parameter_value(param_value):
            self.launcher_fairing_total_height = float(param_value)

    ### Read Kickstage Config ###

    def read_kickstage_config(self,act_config_name):
        self.read_kickstage_diameter(act_config_name)

    def read_kickstage_diameter(self,act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value(\
            act_config_name,BB_ID_KICKSTAGE,PARAM_ID_DIAMETER)
        if self.act_db_linker.check_parameter_value(param_value):
            self.kickstage_diameter = float(param_value)

    ### Read Orbital config ###

    def read_orbital_config(self, act_config_name):
        pass

    ### Link engines and propellants ###

    def get_engines_name(self,act_config_name):
        pass

    def set_kickstage_engine(self,act_config_name,prop,system_name):
        pass