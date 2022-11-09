from ScenarioDatabase.ScenariosSetupFromACT.ScenarioADRSetupFromACT import ScenarioADRSetupFromACT

# Create linker object and select ACT configuration
a2t = ScenarioADRSetupFromACT()
a2t.open_act_config_json_file("ScenarioDatabase/Configurations.json")
config_names = a2t.get_all_configs_name()
config_name = config_names[0]

# Read configuration
a2t.read_act_config(config_name)

# If no engines in the childrenblocks, here is the solution:
engines_name = a2t.get_all_engines_name(config_name)
a2t.read_kickstage_engine_parameters(config_name,engines_name[0])
a2t.read_servicer_engine_parameters(config_name,engines_name[0])

# Export reading to tcat input .json
a2t.export_config_to_json_tcat_format("./my_new_json.json")

pass