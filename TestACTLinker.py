from ScenarioDatabase.ScenariosSetupFromACT.ScenarioADRSetupFromACT import ScenarioADRSetupFromACT

config_name = "test_tcat_1"
a2t = ScenarioADRSetupFromACT()
a2t.open_act_config_json("ScenarioDatabase/Configurations.json")
a2t.read_act_config(config_name)
a2t.export_adr_config_to_json("./my_new_json.json")

pass