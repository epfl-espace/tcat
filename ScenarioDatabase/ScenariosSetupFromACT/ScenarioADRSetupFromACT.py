from ScenarioDatabase.ACTConfigLinker.ACTConfigIDs import *
from ScenarioDatabase.ScenariosSetupFromACT.ScenarioBaseSetupFromACT import ScenarioBaseSetupFromACT


class ScenarioADRSetupFromACT(ScenarioBaseSetupFromACT):
    def read_act_config(self, act_config_name):
        super().read_act_config(act_config_name)
        self.read_servicer_config(act_config_name)

    def get_config_as_tcat_json(self):
        return self.tcat_input_linker.get_adr_config_as_json()

    def get_config_as_dict(self):
        return self.tcat_input_linker.get_adr_config_as_dict()

    def export_config_to_json_tcat_format(self, json_filepath):
        self.tcat_input_linker.export_adr_config_to_json(json_filepath)

    ### Read Orbits Config ###

    def read_orbit_config(self, act_config_name):
        super().read_orbit_config(act_config_name)
        self.read_orbit_servicer_disposal_apogee(act_config_name)
        self.read_orbit_servicer_disposal_perigee(act_config_name)
        self.read_orbit_servicer_disposal_inclination(act_config_name)
        self.read_orbit_sats_operational_apogee(act_config_name)
        self.read_orbit_sats_operational_perigee(act_config_name)
        self.read_orbit_sats_operational_inclination(act_config_name)

    def read_orbit_servicer_disposal_apogee(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_SERVICER, PARAM_ID_ORBIT_DISPOSAL_APOGEE)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.apogee_servicer_disposal = float(param_value)

    def read_orbit_servicer_disposal_perigee(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_SERVICER, PARAM_ID_ORBIT_DISPOSAL_PERIGEE)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.perigee_servicer_disposal = float(param_value)

    def read_orbit_servicer_disposal_inclination(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_SERVICER, PARAM_ID_ORBIT_DISPOSAL_INCLINATION)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.inc_servicer_disposal = float(param_value)

    def read_orbit_sats_operational_apogee(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_SERVICER, PARAM_ID_ORBIT_DEBRIS_APOGEE)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.apogee_sats_operational = float(param_value)

    def read_orbit_sats_operational_perigee(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_SERVICER, PARAM_ID_ORBIT_DEBRIS_PERIGEE)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.perigee_sats_operational = float(param_value)

    def read_orbit_sats_operational_inclination(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_SERVICER, PARAM_ID_ORBIT_DEBRIS_INCLINATION)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.inc_sats_operational = float(param_value)

    ### Read Servicer Config ###

    def read_servicer_config(self, act_config_name):
        self.read_servicer_initial_fuel_mass(act_config_name)
        self.read_servicer_capture_module_dry_mass(act_config_name)
        self.read_servicer_struct_mass(act_config_name)
        self.read_servicer_default_volume(act_config_name)
        engine_name = self.get_servicer_engine_name_from_child(act_config_name)
        if engine_name is not None:
            self.read_servicer_engine_parameters(act_config_name, engine_name)

    def read_servicer_initial_fuel_mass(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_SERVICER, PARAM_ID_PROPELLANT_MASS)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.servicer_initial_fuel_mass = float(param_value)

    def read_servicer_capture_module_dry_mass(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_SERVICER, PARAM_ID_CAPTUREMODULE_DRY_MASS)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.servicer_capture_module_dry_mass = float(param_value)

    def read_servicer_struct_mass(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_SERVICER, PARAM_ID_DRY_MASS)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.servicer_struct_mass = float(param_value)

    def read_servicer_default_volume(self, act_config_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_SERVICER, PARAM_ID_VOLUME)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.servicer_default_volume = float(param_value)

    def get_servicer_engine_name_from_child(self, act_config_name):
        name = self.act_db_linker.get_bb_child_name_filtered_type_id( \
            act_config_name, BB_ID_SERVICER, BB_ID_ENGINE)
        if not self.act_db_linker.check_parameter_value(name, "servicer engine"):
            print("Servicer is missing a child engine block")
            return None
        return name

    def read_servicer_engine_parameters(self, act_config_name, engine_name):
        self.read_servicer_propulsion_thrust(act_config_name, engine_name)
        self.read_servicer_propulsion_isp(act_config_name, engine_name)
        self.read_servicer_propulsion_dry_mass(act_config_name, engine_name)

    def read_servicer_propulsion_thrust(self, act_config_name, engine_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_ENGINE, PARAM_ID_ENGINE_THRUST, engine_name)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.servicer_prop_thrust = float(param_value)

    def read_servicer_propulsion_isp(self, act_config_name, engine_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_ENGINE, PARAM_ID_ENGINE_ISP, engine_name)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.servicer_prop_isp = float(param_value)

    def read_servicer_propulsion_dry_mass(self, act_config_name, engine_name):
        param_value = self.act_db_linker.get_bb_parameter_value( \
            act_config_name, BB_ID_ENGINE, PARAM_ID_DRY_MASS, engine_name)
        if self.act_db_linker.check_parameter_value(param_value):
            self.tcat_input_linker.servicer_propulsion_dry_mass = float(param_value)
