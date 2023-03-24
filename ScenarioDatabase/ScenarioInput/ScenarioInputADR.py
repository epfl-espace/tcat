from dataclasses import dataclass

from ScenarioInput.ScenarioInputBase import ScenarioInputBase


@dataclass
class ScenarioInputADR(ScenarioInputBase):
    # Metadata parameters
    mission_architecture: str = "single_picker"

    # Constellation parameters
    sats_reliability: float = 0.5 # [0-1]
    seed_random_sats_failure: int = 1234

    # Servicer parameters
    servicer_initial_fuel_mass: float = 100.0 # kg
    servicer_capture_module_dry_mass: float = 10.0 # kg
    servicer_prop_thrust: float = 29400.0 # N
    servicer_prop_isp: float = 330.0 # s
    servicer_propulsion_dry_mass: float = 20.0 # kg
    servicer_struct_mass: float = 10.0 # kg
    servicer_default_volume: float = 2.0 # m3
    servicer_propulsion_type: str = "bi-propellant"

    # Orbital parameters 
    apogee_sats_operational: float = 1200.0 # km (altitude)
    perigee_sats_operational: float = 1200.0 # km (altitude)
    inc_sats_operational: float = 87.4 # deg
    apogee_sats_disposal: float = 1500.0 # km (altitude)
    perigee_sats_disposal: float = 1500.0 # km (altitude)
    inc_sats_disposal: float = 87.4 # deg
    apogee_servicer_disposal: float = 1800.0 # km (altitude)
    perigee_servicer_disposal: float = 1800.0 # km (altitude)
    inc_servicer_disposal: float = 85.0 # deg

    def get_adr_config_as_json(self):
        return self.to_json()

    def export_adr_config_to_json(self, json_filepath):
        self.to_json_file(json_filepath)
