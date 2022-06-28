# array structure [control_name , datatype , lookup_name , speaking_name , default_value , accepted_values]

constellation_mission_params = {
    ('mission_configuration', 'Mission Configuration'): [
        ['select', 'text', 'propulsion_type', 'Propulsion type', 'electrical', ['electrical', 'water', 'mono-propellant', 'solid', 'bi-propellant']],
        ['checkbox', '', 'verbose', 'Debug (display figures)', False, [True, False]],
        ['input', 'datetime-local', 'starting_epoch', 'Starting Epoch', '2025-01-01T12:00', ['2000-01-01T00:00', '2100-01-01T00:00']],
        ['input', 'number', 'mission_cash_limitor', 'Mission Cash Limitor', 0.01, [0.0, 1.0]],
    ],
    ('constellation_configuration', 'Constellation Configuration'): [
        ['input', 'text', 'constellation_name', 'Constellation Name', 'My Constellation', '^[A-Za-z0-9 ]+$'],
        ['input', 'number', 'sat_mass', 'Satellite Mass (kg)', 147, [0.1, 99999.9]],
        ['input', 'number', 'sat_volume', 'Satellite Volume (m^3)', None, [0.001, 99999.9]],
        ['input', 'number', 'n_planes', 'Number of orbital planes', 3, [1, 100]],
        ['input', 'number', 'n_sats_per_plane', 'Number of satellite per orbital plane', 2, [1, 1000]],
        ['input', 'number', 'plane_distribution_angle', 'Distribution angle of orbital planes (deg)', 180, [180, 360]],
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
        #
        ['input', 'number', 'apogee_launcher_insertion', 'Launcher insertion orbit apogee, from Earths surface to highest point of the elliptical orbit (km)', 400.0, [0.0, 400000.0]],
        ['input', 'number', 'perigee_launcher_insertion', 'Launcher insertion orbit perigee, from Earths surface to lowest point of the elliptical orbit (km)', 400.0, [0.0, 400000.0]],
        ['input', 'number', 'inc_launcher_insertion', 'Launcher insertion orbit inclination (deg)', 87.0, [-90.0, 90.0]],
        #
        ['input', 'number', 'apogee_launcher_disposal', 'Launcher disposal orbit apogee, from Earths surface to highest point of the elliptical orbit (km)', 400.0, [0.0, 400000.0]],
        ['input', 'number', 'perigee_launcher_disposal', 'Launcher disposal orbit perigee, from Earths surface to lowest point of the elliptical orbit (km)', 50.0, [0.0, 400000.0]],
        ['input', 'number', 'inc_launcher_disposal', 'Launcher disposal orbit inclination (deg)', 87.0, [-90.0, 90.0]],
    ]
}

adr_mission_params = {
    ('mission_configuration', 'Mission Configuration'): [
        ['select', 'text', 'architecture', 'Architecture', 'single_picker', ['single_picker']],
        ['select', 'text', 'propulsion_type', 'Propulsion type', 'electrical', ['electrical', 'water', 'mono-propellant', 'solid', 'bi-propellant']],
        ['checkbox', '', 'verbose', 'Debug (display figures)', False, [True, False]],
        ['input', 'datetime-local', 'starting_epoch', 'Starting Epoch', '2025-01-01T12:00', ['2000-01-01T00:00', '2100-01-01T00:00']],
        ['input', 'number', 'mission_cash_limitor', 'Mission Cash Limitor', 0.01, [0.0, 1.0]],
    ],
    ('constellation_configuration', 'Constellation Configuration'): [
        ['input', 'text', 'constellation_name', 'Constellation Name', 'My Constellation', '^[A-Za-z0-9 ]+$'],
        ['input', 'number', 'sat_mass', 'Satellite Mass (kg)', 147, [0.1, 99999.9]],
        ['input', 'number', 'sat_volume', 'Satellite Volume (m^3)', None, [0.001, 99999.9]],
        ['input', 'number', 'n_planes', 'Number of orbital planes', 3, [1, 100]],
        ['input', 'number', 'n_sats_per_plane', 'Number of satellite per orbital plane', 2, [1, 1000]],
        ['input', 'number', 'plane_distribution_angle', 'Distribution angle of orbital planes (deg)', 180, [180, 360]],
        ['input', 'number', 'sats_reliability', 'Satellite reliability', 0.5, [0.0, 1.0]],
        ['input', 'number', 'seed_random_sats_failure', 'Seed for random satellite failure', 1234, [1000, 99999999]],
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
        ['input', 'number', 'apogee_sats_operational', 'Satellite operational orbit apogee, from Earths surface to highest point of the elliptical orbit (km)', 1200.0, [0.0, 400000.0]],
        ['input', 'number', 'perigee_sats_operational', 'Satellite operational orbit perigee, from Earths surface to highest point of the elliptical orbit (km)', 1200.0, [0.0, 400000.0]],
        ['input', 'number', 'inc_sats_operational', 'Satellite operational orbit inclination (deg)', 87.4, [-90.0, 90.0]],
        #
        ['input', 'number', 'apogee_sats_disposal', 'Satellite disposal orbit apogee, from Earths surface to highest point of the elliptical orbit (km)', 1500.0, [0.0, 400000.0]],
        ['input', 'number', 'perigee_sats_disposal', 'Satellite disposal orbit perigee, from Earths surface to highest point of the elliptical orbit (km)', 1500.0, [0.0, 400000.0]],
        ['input', 'number', 'inc_sats_disposal', 'Satellite disposal orbit inclination (deg)', 87.4, [-90.0, 90.0]],
        #
        ['input', 'number', 'apogee_launcher_insertion', 'Launcher insertion orbit apogee, from Earths surface to highest point of the elliptical orbit (km)', 400.0, [0.0, 400000.0]],
        ['input', 'number', 'perigee_launcher_insertion', 'Launcher insertion orbit perigee, from Earths surface to lowest point of the elliptical orbit (km)', 400.0, [0.0, 400000.0]],
        ['input', 'number', 'inc_launcher_insertion', 'Launcher insertion orbit inclination (deg)', 87.0, [-90.0, 90.0]],
        #
        ['input', 'number', 'apogee_launcher_disposal', 'Launcher disposal orbit apogee, from Earths surface to highest point of the elliptical orbit (km)', 400.0, [0.0, 400000.0]],
        ['input', 'number', 'perigee_launcher_disposal', 'Launcher disposal orbit perigee, from Earths surface to lowest point of the elliptical orbit (km)', 50.0, [0.0, 400000.0]],
        ['input', 'number', 'inc_launcher_disposal', 'Launcher disposal orbit inclination (deg)', 87.0, [-90.0, 90.0]],
        #
        ['input', 'number', 'apogee_servicer_insertion', 'Servicer insertion orbit apogee, from Earths surface to highest point of the elliptical orbit (km)', 500.0, [0.0, 400000.0]],
        ['input', 'number', 'perigee_servicer_insertion', 'Servicer insertion orbit perigee, from Earths surface to lowest point of the elliptical orbit (km)', 500.0, [0.0, 400000.0]],
        ['input', 'number', 'inc_servicer_insertion', 'Servicer insertion orbit inclination (deg)', 87.0, [-90.0, 90.0]],
        ['input', 'number', 'raan_servicer_insertion', 'Servicer insertion orbit raan (deg)', 0.0, [-90.0, 90.0]],
        ['input', 'number', 'arg_periapsis_servicer_insertion', 'Servicer insertion orbit arg periapsis (deg)', 0.0, [-90.0, 90.0]],
        ['input', 'number', 'true_anomaly_servicer_insertion', 'Servicer insertion orbit true anomaly (deg)', 0.0, [-90.0, 90.0]],
        #
        ['input', 'number', 'apogee_servicer_disposal', 'Servicer disposal orbit apogee, from Earths surface to highest point of the elliptical orbit (km)', 1800.0, [0.0, 400000.0]],
        ['input', 'number', 'perigee_servicer_disposal', 'Servicer disposal orbit perigee, from Earths surface to lowest point of the elliptical orbit (km)', 1800.0, [0.0, 400000.0]],
        ['input', 'number', 'inc_servicer_disposal', 'Servicer disposal orbit inclination (deg)', 87.0, [-90.0, 90.0]],
    ]
}