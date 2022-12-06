from dataclasses import dataclass
from dataclasses import asdict
import json


@dataclass
class ScenarioInputBase:
    # Metadata parameters
    scenario: str = "new_scenario"
    verbose: bool = False
    starting_epoch: str = "2025-01-01 12:00:00"
    dir_path_for_output_files: str = "./Results"
    tradeoff_mission_price_vs_duration: float = 0.1 # [0.0-1.0]

    # Constellation parameters
    constellation_name: str = "OneWeb"
    sat_mass: float = 147.0 # kg
    sat_volume: float = 1.3 # m3
    n_planes: int = 3
    n_sats_per_plane: int = 2
    plane_distribution_angle: float = 180.0 # deg

    # Launcher parameters
    launcher_use_database: bool = False
    launcher_name: str = "Soyuz_2.1b_Fregat"
    launcher_launch_site: str = "Baikonur"
    launcher_orbit_type: str = "LEO"
    launcher_perf_interpolation_method: str = "linear"
    launcher_performance: float = 5000.0 # kg
    launcher_fairing_diameter: float = 3.800 # m
    launcher_fairing_cylinder_height: float = 5.070 # m
    launcher_fairing_total_height: float = 9.518 # m

    # Kickstage parameters
    kickstage_use_database: bool = False
    kickstage_name: str = "Fregat"
    kickstage_height: float = 1.5 # m
    kickstage_diameter: float = 2.0 # m
    kickstage_initial_fuel_mass: float = 500.0 # kg
    kickstage_prop_thrust: float = 294000.0 # N
    kickstage_prop_isp: float = 330.0 # s
    kickstage_propulsion_dry_mass: float = 5.0 # m
    kickstage_dispenser_dry_mass: float = 93.3 # m
    kickstage_struct_mass: float = 10.0 # kg
    kickstage_propulsion_type: str = "bi-propellant"
    kickstage_remaining_fuel_margin: float = 0.0 # kg

    # Orbital parameters               
    apogee_launcher_insertion: float = 400.0 # km (altitude)
    perigee_launcher_insertion: float = 400.0 # km (altitude)
    inc_launcher_insertion: float = 87.0 # deg
    apogee_kickstage_disposal: float = 400.0 # km (altitude)
    perigee_kickstage_disposal: float = 50.0 # km (altitude)
    inc_kickstage_disposal: float = 85.0 # deg

    def to_json(self):
        return json.dumps(asdict(self))

    def to_json_file(self, json_filepath):
        json_data = self.to_json()
        with open(json_filepath, "w") as outfile:
            outfile.write(json_data)
