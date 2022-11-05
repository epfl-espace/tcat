from dataclasses import dataclass

from ScenarioDatabase.ScenarioInput.ScenarioInputBase import ScenarioInputBase

@dataclass
class ScenarioInputADR(ScenarioInputBase):
    sats_reliability: float = 0.5
    seed_random_sats_failure: int = 1234
    mission_architecture: str = "single_picker"

    servicer_initial_fuel_mass: float = 100.0
    servicer_capture_module_dry_mass: float = 10.0 
    servicer_prop_thrust: float = 29400.0
    servicer_prop_isp: float = 330.0
    servicer_propulsion_dry_mass: float = 20.0
    servicer_struct_mass: float = 10.0
    servicer_default_volume: float = 2.0
    servicer_propulsion_type: str = "bi-propellant"
            
    apogee_sats_operational: float = 1200.0
    perigee_sats_operational: float = 1200.0
    inc_sats_operational: float = 87.4
    apogee_sats_disposal: float = 1500.0
    perigee_sats_disposal: float = 1500.0
    inc_sats_disposal: float = 87.4
    apogee_servicer_disposal: float = 1800.0
    perigee_servicer_disposal: float = 1800.0
    inc_servicer_disposal: float = 85.0

    def export_adr_config_to_json(self,json_filepath):
        self.to_json_file(json_filepath)