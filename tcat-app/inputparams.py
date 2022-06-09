# control-datatype-lookup_name-speaking_name-default_value-accepted_values
params = {
    ('mission_configuration', 'Mission Configuration'): [
        ['select', 'text', 'architecture', 'Architecture / Mission profile', 'launch_vehicle', ['launch_vehicle', 'upper_stage']],
        ['select', 'text', 'propulsion_type', 'Propulsion type', 'electrical', ['electrical', 'water', 'mono-propellant', 'solid', 'bi-propellant']],
        ['select', 'text', 'deployment_strategy', 'Deployment strategy', 'one_plane_at_a_time_sequential', ['one_plane_at_a_time_sequential', 'one_sat_per_plane_sequential']],
        ['checkbox', '', 'verbose', 'Debug', False, [True, False]],
        ['input', 'date', 'starting_epoch', 'Starting Epoch', '01.07.2022', None]
    ],
    ('constellation_configuration', 'Constellation Configuration'): [
        ['input', 'text', 'constellation_name', 'Constellation Name', 'My Constellation', '^[A-Za-z0-9 ]+$'],
        ['input', 'number', 'sat_mass', 'Satellite Mass (kg)', 147, [0.1, 99999.9]],
        ['input', 'number', 'sat_volume', 'Satellite Volume (m^3)', 1.3, [0.1, 99999.9]],
        ['input', 'number', 'n_planes', 'Number of orbital planes', 3, [1, 100]],
        ['input', 'number', 'n_sats_per_plane', 'Number of satellite per orbital plane', 2, [1, 1000]],
        ['input', 'number', 'plane_distribution_angle', 'Distribution angle of orbital planes (deg)', 180, [180, 360]],
        ['input', 'number', 'n_sats_simultaneously_deployed', 'Maximum number of satellites to be simultaneously deployed', 4, [1, 1000]],
    ],
    ('launch_vehicle_configuration', 'Launch Vehicle Configuration'): [
        ['select', 'text', 'launcher', 'Launch vehicle name and variant', 'Soyuz_2.1a_Fregat', ['Ariane_62', 'Ariane_64', 'Soyuz_2.1a_Fregat', 'Soyuz_2.1b_Fregat', 'Soyuz']],
        ['select', 'text', 'launch_site', 'Launch Site', 'Baikonur', ['Korou', 'Baikonur']],
        ['select', 'text', 'orbit_type', 'Orbit Type', 'LEO', ['LEO', 'SSO', 'LPEO', 'Polar', 'MTO', 'GTO', 'GTO+']],
        ['input', 'number', 'dispenser_tech_level', 'Dispenser technological level', 1.1, [0.1, 1.9]],
        ['input', 'text', 'custom_launcher_name', 'Custom launch vehicle name', None, '^[A-Za-z0-9 ]+$'],
        ['input', 'number', 'custom_launcher_performance', 'Custom launch vehicle performance (kg)', None, [0.1, 99999.9]],
        ['input', 'number', 'fairing_diameter', 'Fairing diameter (m)', None, [0.1, 100.0]],
        ['input', 'number', 'fairing_cylinder_height', 'Fairing height of the cylindrical section (m)', None, [0.1, 100.0]],
        ['input', 'number', 'fairing_total_height', 'Fairing total height (m)', None, [0.1, 100.0]],
        ['select', 'text', 'interpolation_method', 'Interpolation method for the launch vehicle performance', 'linear', ['linear', 'nearest', 'cubic', 'nearest-up', 'zero', 'slinear', 'quadratic', 'previous', 'next']]
    ],
    ('orbits_configuration', 'Orbits Configuration'): [
        ['input', 'number', 'apogee_sats_insertion', 'Satellite insertion orbit apogee, from Earths surface to highest point of the elliptical orbit (km)', 600.0, [0.0, 400000.0]],
        ['input', 'number', 'perigee_sats_insertion', 'Satellite insertion orbit perigee, from Earths surface to lowest point of the elliptical orbit (km)', 450.0, [0.0, 400000.0]],
        ['input', 'number', 'inc_sats_insertion', 'Satellite insertion orbit inclination (deg)', 87.4, [-90.0, 90.0]],
        ['input', 'number', 'apogee_sats_operational', 'Satellite operational orbit apogee, from Earths surface to highest point of the elliptical orbit (km)', 1200.0, [0.0, 400000.0]],
        ['input', 'number', 'perigee_sats_operational', 'Satellite operational orbit perigee, from Earths surface to lowest point of the elliptical orbit (km)', 1200.0, [0.0, 400000.0]],
        ['input', 'number', 'inc_sats_operational', 'Satellite operational orbit inclination (deg)', 90.0, [-90.0, 90.0]],
        ['input', 'number', 'apogee_launcher_insertion', 'Launcher insertion orbit apogee, from Earths surface to highest point of the elliptical orbit (km)', 400.0, [0.0, 400000.0]],
        ['input', 'number', 'perigee_launcher_insertion', 'Launcher insertion orbit perigee, from Earths surface to lowest point of the elliptical orbit (km)', 400.0, [0.0, 400000.0]],
        ['input', 'number', 'inc_launcher_insertion', 'Launcher insertion orbit inclination (deg)', 87.0, [-90.0, 90.0]],
        ['input', 'number', 'apogee_launcher_disposal', 'Launcher disposal orbit apogee, from Earths surface to highest point of the elliptical orbit (km)', 400.0, [0.0, 400000.0]],
        ['input', 'number', 'perigee_launcher_disposal', 'Launcher disposal orbit perigee, from Earths surface to lowest point of the elliptical orbit (km)', 50.0, [0.0, 400000.0]],
        ['input', 'number', 'inc_launcher_disposal', 'Launcher disposal orbit inclination (deg)', 87.0, [-90.0, 90.0]],
    ]
}
