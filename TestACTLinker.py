from ScenarioDatabase.ScenariosSetupFromACT.ScenarioADRSetupFromACT import ScenarioADRSetupFromACT

a2t = ScenarioADRSetupFromACT()
a2t.open_act_config_json("ScenarioDatabase/Configurations.json")
config_names = a2t.get_all_configs_name()
config_name = config_names[0]

a2t.read_act_config(config_name)

engines_name = a2t.get_all_engines_name(config_name)
a2t.read_kickstage_engine_parameters(config_name,engines_name[0])
a2t.read_servicer_engine_parameters(config_name,engines_name[0])

a2t.export_config_to_json_tcat_format("./my_new_json.json")

pass