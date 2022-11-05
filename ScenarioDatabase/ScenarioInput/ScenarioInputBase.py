from dataclasses import dataclass
from dataclasses import asdict
import json

@dataclass
class ScenarioInputBase:
    # Metadata parameters
    scenario : str = "new_scenario"
    verbose : bool = False
    starting_epoch : str = "2025-01-01 12:00:00"
    dir_path_for_output_files : str = "./Results"
    tradeoff_mission_price_vs_duration : float = 0.1

    # Constellation parameters
    constellation_name : str = "OneWeb"
    sat_mass: float = 147.0
    sat_volume: float = 1.3
    n_planes : int = 3
    n_sats_per_plane : int = 2
    plane_distribution_angle : float = 180.0

    # Launcher parameters
    launcher_use_database : bool = False
    launcher_name : str = "Soyuz_2.1b_Fregat"
    launcher_launch_site: str = "Baikonur"
    launcher_orbit_type: str = "LEO"
    launcher_perf_interpolation_method: str = "linear"
    launcher_performance: float = 5000.0
    launcher_fairing_diameter: float = 3.800
    launcher_fairing_cylinder_height: float = 5.070
    launcher_fairing_total_height: float = 9.518

    # Kickstage parameters
    kickstage_use_database: bool = False
    kickstage_name: str = "Fregat"
    kickstage_height: float = 1.5
    kickstage_diameter: float = 2.0
    kickstage_initial_fuel_mass: float = 500.0
    kickstage_prop_thrust: float = 294000.0
    kickstage_prop_isp: float = 330.0
    kickstage_propulsion_dry_mass: float = 5.0
    kickstage_dispenser_dry_mass: float = 93.3
    kickstage_struct_mass: float = 10.0
    kickstage_propulsion_type: str = "bi-propellant"
    kickstage_remaining_fuel_margin: float = 0.0

    # Orbital parameters               
    apogee_launcher_insertion: float = 400.0
    perigee_launcher_insertion: float = 400.0
    inc_launcher_insertion: float = 87.0
    apogee_launcher_disposal: float = 400.0
    perigee_launcher_disposal: float = 50.0
    inc_launcher_disposal: float = 85.0

    def to_json_file(self,json_filepath):
        json_data = json.dumps(asdict(self))
        with open(json_filepath, "w") as outfile:
            outfile.write(json_data)
