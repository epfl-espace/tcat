from ScenarioDatabase.ACTConfigLinker.ACTConfigLinker import ACTConfigLinker
from ScenarioDatabase.ACTConfigLinker.ACTConfigIDs import *
from ScenarioDatabase.ScenarioInput.ScenarioInput import ScenarioInput


class ScenarioBaseSetupFromACT():
    def __init__(self):
        self.act_db_linker = ACTConfigLinker()
        self.tcat_input_linker = ScenarioInput()

    def open_act_config_json(self, json_str):
        self.act_db_linker.open_act_json(json_str)

    def open_act_config_json_file(self, json_filepath):
        self.act_db_linker.open_act_json_file(json_filepath)

    def get_all_configs_name(self):
        configs_name = []
        for config in self.act_db_linker.get_configs():
            configs_name.append(self.act_db_linker.get_config_name(config))
        return configs_name

    def read_act_config(self, act_config_name):
        self.read_mission_config(act_config_name)
        self.read_constellation_config(act_config_name)
        self.read_launcher_config(act_config_name)
        self.read_kickstage_config(act_config_name)
        self.read_orbit_config(act_config_name)

    def export_config_to_json_tcat_format(self, json_filepath):
        self.tcat_input_linker.to_json_file(json_filepath)

    ### Read Mission Config ###

    def read_mission_config(self, act_config_name):
        self.read_mission_starting_epoch(act_config_name)

    def read_mission_starting_epoch(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_MISSION, PARAM_ID_STARTING_EPOCH)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.starting_epoch = str(param_value)

    ### Read Constellation Config ###

    def read_constellation_config(self, act_config_name):
        pass

    ### Read Launcher Config ###

    def read_launcher_config(self, act_config_name):
        self.read_launcher_name(act_config_name)
        self.read_launcher_launch_site(act_config_name)
        self.read_launcher_orbit_type(act_config_name)
        self.read_launcher_fairing_diameter(act_config_name)
        self.read_launcher_height_cylinder(act_config_name)
        self.read_launcher_height_total(act_config_name)

    def read_launcher_name(self, act_config_name):
        config = self.act_db_linker.get_config(act_config_name)
        name = self.act_db_linker.get_config_name(config)
        if self.act_db_linker.check_parameter_value(name):
            self.tcat_input_linker.launcher_name = str(name)

    def read_launcher_launch_site(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_MISSION, PARAM_ID_LAUNCH_SITE)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.launcher_launch_site = str(param_value)

    def read_launcher_orbit_type(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_UPPERSTAGE, PARAM_ID_ORBIT_TYPE)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.launcher_orbit_type = str(param_value)

    def read_launcher_fairing_diameter(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_FAIRING, PARAM_ID_DIAMETER)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.launcher_fairing_diameter = float(param_value)

    def read_launcher_height_cylinder(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_FAIRING, PARAM_ID_LENGTH_CYLINDER)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.launcher_fairing_cylinder_height = float(param_value)

    def read_launcher_height_total(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_FAIRING, PARAM_ID_LENGTH_TOTAL)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.launcher_fairing_total_height = float(param_value)

    ### Read Kickstage Config ###

    def read_kickstage_config(self, act_config_name):
        self.read_kickstage_name(act_config_name)
        self.read_kickstage_height(act_config_name)
        self.read_kickstage_diameter(act_config_name)
        self.read_kickstage_initial_fuel_mass(act_config_name)
        self.read_kickstage_dispenser_dry_mass(act_config_name)
        self.read_kickstage_struct_dry_mass(act_config_name)
        engine_name = self.get_kickstage_engine_name_from_child(act_config_name)
        if engine_name is not None:
            self.read_kickstage_engine_parameters(act_config_name, engine_name)

    def read_kickstage_name(self, act_config_name):
        config = self.act_db_linker.get_config(act_config_name)
        bb_kickstage = self.act_db_linker.get_config_bb(config, BB_ID_KICKSTAGE)
        name = self.act_db_linker.get_bb_name(bb_kickstage)
        if self.act_db_linker.check_parameter_value(name):
            self.tcat_input_linker.kickstage_name = str(name)

    def read_kickstage_height(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_KICKSTAGE, PARAM_ID_LENGTH_TOTAL)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.kickstage_height = float(param_value)

    def read_kickstage_diameter(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_KICKSTAGE, PARAM_ID_DIAMETER)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.kickstage_diameter = float(param_value)

    def read_kickstage_initial_fuel_mass(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_KICKSTAGE, PARAM_ID_PROPELLANT_MASS)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.kickstage_initial_fuel_mass = float(param_value)

    def read_kickstage_dispenser_dry_mass(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_KICKSTAGE, PARAM_ID_DISPENSER_DRY_MASS)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.kickstage_dispenser_dry_mass = float(param_value)

    def read_kickstage_struct_dry_mass(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_KICKSTAGE, PARAM_ID_DRY_MASS)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.kickstage_struct_mass = float(param_value)

    def get_kickstage_engine_name_from_child(self, act_config_name):
        name = self.act_db_linker.get_bb_child_name_filtered_type_id( \
            act_config_name, BB_ID_KICKSTAGE, BB_ID_ENGINE)
        if not self.act_db_linker.check_parameter_value(name, "kickstage engine"):
            print("Kickstage is missing a child engine block")
            return None
        return name

    ### Read Orbital config ###

    def read_orbit_config(self, act_config_name):
        self.read_orbit_launcher_insertion_apogee(act_config_name)
        self.read_orbit_launcher_insertion_perigee(act_config_name)
        self.read_orbit_launcher_insertion_inclination(act_config_name)
        self.read_orbit_launcher_disposal_apogee(act_config_name)
        self.read_orbit_launcher_disposal_perigee(act_config_name)
        self.read_orbit_launcher_disposal_inclination(act_config_name)

    def read_orbit_launcher_insertion_apogee(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_KICKSTAGE, PARAM_ID_ORBIT_INSERTION_APOGEE)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.apogee_launcher_insertion = float(param_value)

    def read_orbit_launcher_insertion_perigee(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_KICKSTAGE, PARAM_ID_ORBIT_INSERTION_PERIGEE)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.perigee_launcher_insertion = float(param_value)

    def read_orbit_launcher_insertion_inclination(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_KICKSTAGE, PARAM_ID_ORBIT_INSERTION_INCLINATION)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.inc_launcher_insertion = float(param_value)

    def read_orbit_launcher_disposal_apogee(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_KICKSTAGE, PARAM_ID_ORBIT_DISPOSAL_APOGEE)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.apogee_launcher_disposal = float(param_value)

    def read_orbit_launcher_disposal_perigee(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_KICKSTAGE, PARAM_ID_ORBIT_DISPOSAL_PERIGEE)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.perigee_launcher_disposal = float(param_value)

    def read_orbit_launcher_disposal_inclination(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_KICKSTAGE, PARAM_ID_ORBIT_DISPOSAL_INCLINATION)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.inc_launcher_disposal = float(param_value)

    ### Link engines and propellants ###

    def get_all_engines_name(self, act_config_name):
        config = self.act_db_linker.get_config(act_config_name)
        bbs_engine = self.act_db_linker.get_config_bbs_filtered_type(config, BB_ID_ENGINE)
        if bbs_engine is None:
            return None
        engines_name = [self.act_db_linker.get_bb_name(bb_engine) for bb_engine in bbs_engine]
        return engines_name

    def read_kickstage_engine_parameters(self, act_config_name, engine_name):
        self.read_kickstage_propulsion_thrust(act_config_name, engine_name)
        self.read_kickstage_propulsion_dry_mass(act_config_name, engine_name)
        self.read_kickstage_propulsion_isp(act_config_name, engine_name)

    def read_kickstage_propulsion_thrust(self, act_config_name, engine_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_ENGINE, PARAM_ID_ENGINE_THRUST, engine_name)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.kickstage_prop_thrust = float(param_value)

    def read_kickstage_propulsion_isp(self, act_config_name, engine_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_ENGINE, PARAM_ID_ENGINE_ISP, engine_name)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.kickstage_prop_isp = float(param_value)

    def read_kickstage_propulsion_dry_mass(self, act_config_name, engine_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_ENGINE, PARAM_ID_DRY_MASS, engine_name)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.kickstage_propulsion_dry_mass = float(param_value)
