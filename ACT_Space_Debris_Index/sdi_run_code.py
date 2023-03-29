# Created:          15.07.2022
# Last Revision:    07.12.2022
# Authors:          Mathieu Udriot
# Emails:           mathieu.udriot@epfl.ch
# Description:      Script for computation needed for the space debris index to be used in ACT, inputs

# import class
from ACT_Space_Debris_Index.sdi_space_debris_index import *

# imports
from astropy import units as u
from astropy.time import Time
from poliastro.bodies import Earth

# local inputs
starting_epoch = Time("2018-01-01 12:00:00", scale="tdb")
op_duration = 1 * u.year

mass = 1150 * u.kg
cross_section = 15.5 * u.m ** 2 # TODO the cross section can be computed from the CROC tool (from ESA) based on the dimensions --> what is possible to do ?
mean_thrust = 20 * u.N
Isp = 210 * u.s
number_of_launch_es = 1

apogee_object_op = 3000 * u.km
perigee_object_op = 3000 * u.km
inc_object_op = 98 * u.deg

EOL_manoeuvre = True
PMD_success = 0.9
        
apogee_object_disp = 3000 * u.km
perigee_object_disp = 3000 * u.km
inc_object_disp = 98 * u.deg

ADR_stage = True
m_ADR = 200 * u.kg
ADR_cross_section = 9 * u.m ** 2
ADR_mean_thrust = 8 * u.N
ADR_Isp = 300 * u.s
ADR_manoeuvre_success = 0.999
ADR_capture_success = 0.9

m_debris = 100 * u.kg
debris_cross_section = 5 * u.m ** 2
apogee_debris = 1000 *u.km
perigee_debris = 900 *u.km
inc_debris = 98 * u.deg

apogee_debris_removal = 200 *u.km
perigee_debris_removal = 200 *u.km
inc_debris_removal = 98 * u.deg

def sdi_main(starting_epoch, op_duration, mass, cross_section, mean_thrust, Isp, number_of_launch_es, apogee_object_op, perigee_object_op, inc_object_op, EOL_manoeuvre, PMD_success, apogee_object_disp, perigee_object_disp, 
            inc_object_disp, ADR_stage, m_ADR, ADR_cross_section, ADR_mean_thrust, ADR_Isp, ADR_manoeuvre_success, ADR_capture_success, m_debris, debris_cross_section, apogee_debris, perigee_debris, inc_debris, 
            apogee_debris_removal, perigee_debris_removal, inc_debris_removal, CF_file_path = 'sdi_space_debris_CF_for_code.csv', reduced_lifetime_file_path = 'sdi_reduced_lifetime.csv'):

    print('Creating inputs...')
    # input parameters

    # NOTE this script is based on the literature:
    # 1. Thibaut Maury et alli. “Towards the integration of orbital space use in Life Cycle Impact Assessment”. In: Science of the Total Environment (2017)
    # 2. Thibaut Maury et alli. “Application of environmental life cycle assessment (LCA) within the space sector: A state of the art”. In: Acta Astronautica (2019).
    # A newer version of the SDI, methodologically more correct for LCA, has been published by T. Maury et alli, "A new impact assessment model to integrate space debris within the life cycle assessment-based environmental footprint of space systems", (2022)
    # But this script has not been updated yet

    # for future improvements / developements :
    # TODO allow users to define more than 1 operational orbit, ideally would use more of TCAT to compute impact at each manoeuvres, also with changes in inclination ? (can be neglected for launchers but not for active spacecrafts (kickstage, ADR servicers))
    # TODO include collision avoidance manoeuvres and passivation in the assessment ?
    # TODO add check with propellant mass if maneuvres can be performed (would be solved by using TCAT directly)
    # TODO add other means of manoeuvring else than propulsive (drag sails, tumbling ?)
    # TODO compute time spent in region B (GEO) ? and other sensitive regions (eg. Galileo) ?

    if op_duration.value < 0:
        raise ValueError("Operation duration must not be negative [years].")

    if number_of_launch_es <= 0:
        raise ValueError("Number of launch(es) must be at least 1 (integer).")

    if mass.value <= 0:
        raise ValueError("LV mass must be a positive number (kg).")

    if cross_section.value <= 0:
        raise ValueError("LV cross section must be a positive number (m^2).")
    
    if mean_thrust.value < 0:
        raise ValueError("Mean thrust must be a positive number (N).")

    if Isp.value < 0:
        raise ValueError("Specific impulse must be a positive number (s).")

    if perigee_object_op.value <= 0:
        raise ValueError("LV operational perigee must be a positive number (km).")
    elif apogee_object_op < perigee_object_op:
        raise ValueError("LV operational apogee must be larger or equal to perigee (km).")

    if inc_object_op >= 180 * u.deg:
        raise ValueError("LV operational inclination not in the range 0 <= inc < 180.")
    elif inc_object_op < 0 * u.deg:
        raise ValueError("LV operational inclination not in the range 0 <= inc < 180.")

    a_op = (apogee_object_op + perigee_object_op) / 2 + Earth.R
    ecc_op = (apogee_object_op + Earth.R - a_op) / a_op * u.one

    if EOL_manoeuvre == True:
        if PMD_success > 1 or PMD_success < 0:
            raise ValueError("PMD success rate must be between 0 and 1.")
        
        if perigee_object_disp <= 0:
            raise ValueError("LV disposal perigee must be a positive number (km).")
        elif apogee_object_disp < perigee_object_disp:
            raise ValueError("LV disposal apogee must be larger or equal to perigee (km).")
        
        a_disp = (apogee_object_disp + perigee_object_disp) / 2 + Earth.R
        ecc_disp = (apogee_object_disp + Earth.R - a_disp) / a_disp * u.one

        if inc_object_disp >= 180 * u.deg:
            raise ValueError("LV disposal inclination not in the range 0 <= inc < 180.")
        elif inc_object_disp < 0 * u.deg:
            raise ValueError("LV disposal inclination not in the range 0 <= inc < 180.")
    # case without manoeuvre
    else:
        PMD_success = 0
        a_disp = a_op
        ecc_disp = ecc_op
        inc_object_disp = inc_object_op

    print("\n --- Debris risk from launch vehicle orbital stage. ---")
    LV_SDI_results = SDI_compute(starting_epoch, mass, cross_section, op_duration, mean_thrust, Isp, EOL_manoeuvre, PMD_success, a_op, ecc_op, inc_object_op,
                                a_disp, ecc_disp, inc_object_disp, CF_file_path, reduced_lifetime_file_path)

    # For case with ADR stage included
    if ADR_stage == True:        

        if m_ADR.value <= 0:
            raise ValueError("ADR stage mass must be a positive number (kg).")
        
        if ADR_cross_section.value <= 0:
            raise ValueError("ADR stage cross section must be a positive number (m^2).")

        if ADR_mean_thrust.value < 0:
            raise ValueError("ADR stage mean thrust must be a positive number (N).")

        if ADR_Isp.value < 0:
            raise ValueError("ADR stage specific impulse must be a positive number (s).")

        if ADR_manoeuvre_success > 1 or ADR_manoeuvre_success < 0:
            raise ValueError("ADR manoeuvre success rate must be between 0 and 1.")

        if ADR_capture_success > 1 or ADR_capture_success < 0:
            raise ValueError("ADR capture success rate must be between 0 and 1.")

        if m_debris.value <= 0:
            raise ValueError("Debris mass must be a positive number (kg).")

        if debris_cross_section.value <= 0:
            raise ValueError("Debris cross section must be a positive number (m^2).")

        if perigee_debris <= 0:
            raise ValueError("Debris perigee must be a positive number (km).")
        elif apogee_debris < perigee_debris:
            raise ValueError("Debris apogee must be larger or equal to perigee (km).")

        a_debris = (apogee_debris + perigee_debris) / 2 + Earth.R
        ecc_debris = (apogee_debris + Earth.R - a_debris) / a_debris * u.one

        if inc_debris >= 180 * u.deg:
            raise ValueError("Debris inclination not in the range 0 <= inc < 180.")
        elif inc_debris < 0 * u.deg:
            raise ValueError("Debris inclination not in the range 0 <= inc < 180.")

        if perigee_debris_removal <= 0:
            raise ValueError("Debris removal perigee must be a positive number (km).")
        elif apogee_debris_removal < perigee_debris_removal:
            raise ValueError("Debris removal apogee must be larger or equal to perigee (km).")

        a_debris_removal = (apogee_debris_removal + perigee_debris_removal) / 2 + Earth.R
        ecc_debris_removal = (apogee_debris_removal + Earth.R - a_debris_removal) / a_debris_removal * u.one

        if inc_debris_removal >= 180 * u.deg:
            raise ValueError("Debris removal inclination not in the range 0 <= inc < 180.")
        elif inc_debris_removal < 0 * u.deg:
            raise ValueError("Debris removal inclination not in the range 0 <= inc < 180.")

        print("\n\n --- Debris risk from active debris removal servicer, from insertion to debris orbit. ---")
        # Assumes ADR inserted at launcher's operational orbit, the "disposal manoeuvre" here describes the trajectory from insertion to the debris
        ADR_servicer_SDI = SDI_compute(starting_epoch, m_ADR, ADR_cross_section, 0 * u.year, ADR_mean_thrust, ADR_Isp, True, ADR_manoeuvre_success, a_op, ecc_op, inc_object_op,
                                a_debris, ecc_debris, inc_debris, CF_file_path, reduced_lifetime_file_path)

        # compute risk generated by debris if not removed, debris assumed inert (no propulsion capability)
        print("\n\n --- Residual debris risk from debris. ---")
        debris_residual_SDI = SDI_compute(starting_epoch, m_debris, debris_cross_section, 0 * u.year, 0 * u.N, 0 * u.s, False, 0, a_debris, ecc_debris, inc_debris,
                                a_debris, ecc_debris, inc_debris, CF_file_path, reduced_lifetime_file_path)

        # assumes the debris is captured directly after ADR servicer manoeuvre from its insertion to the debris' orbit
        print("\n\n --- Debris risk from removal operations, from debris orbit to target disposal. ---")
        SDI_debris_removal = SDI_compute(starting_epoch, m_debris + m_ADR - ADR_servicer_SDI["Mass_burnt"], max(debris_cross_section, ADR_cross_section), 0 * u.year, ADR_mean_thrust, ADR_Isp, True, 
                                        ADR_manoeuvre_success*ADR_capture_success, a_debris, ecc_debris, inc_debris, a_debris_removal , ecc_debris_removal, inc_debris_removal, CF_file_path, reduced_lifetime_file_path)

        print("\n\n Final impact with ADR risk reduction:", "{:.3f}".format(number_of_launch_es*(LV_SDI_results["Space_Debris_Index"] + ADR_servicer_SDI["Disposal_manoeuvre_percentage"]*ADR_servicer_SDI["Space_Debris_Index"]
                + SDI_debris_removal["Space_Debris_Index"] - debris_residual_SDI["Space_Debris_Index"])))

        sdi_results = {"LCS3": number_of_launch_es*(LV_SDI_results["Space_Debris_Index"]*LV_SDI_results["Operational_percentage"] + ADR_servicer_SDI["Disposal_manoeuvre_percentage"]*ADR_servicer_SDI["Space_Debris_Index"]
                + SDI_debris_removal["Space_Debris_Index"]*SDI_debris_removal["Disposal_manoeuvre_percentage"] - debris_residual_SDI["Space_Debris_Index"]), 
                "LCS4": number_of_launch_es*(LV_SDI_results["Space_Debris_Index"]*(1-LV_SDI_results["Operational_percentage"]) + ADR_servicer_SDI["Natural_decay_percentage"]*ADR_servicer_SDI["Space_Debris_Index"] + 
                SDI_debris_removal["Space_Debris_Index"]*SDI_debris_removal["Natural_decay_percentage"]), "BB_orbital_stage": number_of_launch_es*LV_SDI_results["Space_Debris_Index"], 
                "BB_ADR_stage": number_of_launch_es*(ADR_servicer_SDI["Space_Debris_Index"] + SDI_debris_removal["Space_Debris_Index"]), "BB_EOL_strategy": - debris_residual_SDI["Space_Debris_Index"]}

        return sdi_results
    else:
        print("\n\n Final impact:", "{:.3f}".format(number_of_launch_es*LV_SDI_results["Space_Debris_Index"]))

        sdi_results = {"LCS3": number_of_launch_es*LV_SDI_results["Space_Debris_Index"]*LV_SDI_results["Operational_percentage"], "LCS4": number_of_launch_es*LV_SDI_results["Space_Debris_Index"]*(1 - LV_SDI_results["Operational_percentage"]), 
        "BB_orbital_stage": number_of_launch_es*LV_SDI_results["Space_Debris_Index"], "BB_ADR_stage": 0, "BB_EOL_strategy": 0}

        return sdi_results


def SDI_compute(starting_epoch, mass, cross_section, op_duration, mean_thrust, Isp, EOL_manoeuvre, PMD_success, a_op, ecc_op, inc_object_op,
                a_disp, ecc_disp, inc_object_disp, CF_file_path = 'sdi_space_debris_CF_for_code.csv', reduced_lifetime_file_path = 'sdi_reduced_lifetime.csv'):
    
    # input .csv file for characterization factor
    CF_file = np.genfromtxt(CF_file_path, delimiter=",", skip_header=1)
    # input .csv file for natural decay
    reduced_lifetime_file = np.genfromtxt(reduced_lifetime_file_path, delimiter=",", skip_header=2)

    operational_orbit = Orbit.from_classical(Earth, 
                                            a_op, 
                                            ecc_op, 
                                            inc_object_op, 
                                            0. * u.deg,
                                            90. * u.deg,
                                            0. * u.deg,
                                            starting_epoch)

    disposal_orbit = Orbit.from_classical(Earth, 
                                            a_disp, 
                                            ecc_disp, 
                                            inc_object_disp, 
                                            0. * u.deg,
                                            90. * u.deg,
                                            0. * u.deg,
                                            starting_epoch)

    # Impact score computation
    print('Start finding the orbital case and computing impact score...')

    # #1 Case if operational perigee is lower than the atmosphere limit, no natural decay hereafter
    if (operational_orbit.r_p - Earth.R) < ALTITUDE_ATMOSPHERE_LIMIT:
        # Case if object is already completely in the atmosphere
        if (operational_orbit.r_a - Earth.R) < ALTITUDE_ATMOSPHERE_LIMIT:
            print("Object will reenter directly.")
            impact_score = 0 * u.year *u.pot_fragments
            op_impact_percentage = 0
            disp_maneuver_impact_percentage = 0
            natural_impact_percentage = 0
            print("--\n Computed space debris impact score is", impact_score, ".")

            results = {"Space_Debris_Index": impact_score, "Operational_percentage": op_impact_percentage, "Disposal_manoeuvre_percentage": disp_maneuver_impact_percentage, "Natural_decay_percentage": natural_impact_percentage,
                        "Transfer_duration": 0 * u.year, "Mass_burnt": 0 * u.kg}
            return results
        else:
            # Case if apogee is in space and perigee in the atmosphere: direct reentry
            print("Direct reentry.")
            # Compute impact of reentry: decompose elliptical orbit and use time_to_anomaly after finding LTAN from position meaning altitude
            disposal_impact = elliptical_orbit_decomposition(CF_file, operational_orbit, mass)

            impact_score = disposal_impact*mass*cross_section
            op_impact_percentage = 0
            disp_maneuver_impact_percentage = 100
            transfer_duration = (np.pi*np.sqrt(a_op ** 3 / Earth.k)).value * u.year # half ellipse period
            natural_impact_percentage = 0
            print("--\n Computed space debris impact score is", "{:.3f}".format(impact_score), ". 0 percent operational impact, 100 percent disposal impact.")

            results = {"Space_Debris_Index": impact_score, "Operational_percentage": op_impact_percentage, "Disposal_manoeuvre_percentage": disp_maneuver_impact_percentage, "Natural_decay_percentage": natural_impact_percentage, 
                        "Transfer_duration": transfer_duration, "Mass_burnt": 0 * u.kg}
            return results

    # #2 Case if object's perigee is higher than LEO
    elif (operational_orbit.r_p - Earth.R) > ALTITUDE_LEO_LIMIT:
        print("Operational orbit is higher than LEO, no debris impact computed for the operational phase.")
        CF_op = 0
        op_impact_percentage = 0
        # Check disposal orbit
        if (disposal_orbit.r_p - Earth.R) > ALTITUDE_LEO_LIMIT:
            print("Graveyard orbit outside of LEO, no debris impact computed for the disposal phase.")
            manoeuvres, transfer_duration, transfer_orbit, burned_mass = high_thrust_delta_v(operational_orbit, disposal_orbit, mass, mean_thrust, Isp, False)
            if burned_mass > mass:
                raise ValueError("Propellant mass is not sufficient to perform manoeuvre.")
            # TODO add decay from above LEO limit ? No we assume graveyard decays so slowly the spacecraft will no enter LEO protected region
            impact_score = 0 * u.year *u.pot_fragments
            disp_maneuver_impact_percentage = 0
            natural_impact_percentage = 0
            print("--\n Computed space debris impact score is", impact_score, ".")

            results = {"Space_Debris_Index": impact_score, "Operational_percentage": op_impact_percentage, "Disposal_manoeuvre_percentage": disp_maneuver_impact_percentage, "Natural_decay_percentage": natural_impact_percentage,
                        "Transfer_duration": transfer_duration.to(u.year), "Mass_burnt": burned_mass}
            return results
        else:
            print("Reentry manoeuvre from operational orbit higher than LEO.")
            if (disposal_orbit.r_p - Earth.R) < ALTITUDE_ATMOSPHERE_LIMIT:
                no_2nd_burn = True
            else:
                no_2nd_burn = False
            manoeuvres, transfer_duration, transfer_orbit, burned_mass = high_thrust_delta_v(operational_orbit, disposal_orbit, mass, mean_thrust, Isp, no_2nd_burn)
            if burned_mass > mass:
                raise ValueError("Propellant mass is not sufficient to perform manoeuvre.")
            # Compute impact of disposal manoeuvre: decompose elliptical orbit and use time_to_anomaly after finding LTAN from position meaning altitude
            disposal_impact = elliptical_orbit_decomposition(CF_file, transfer_orbit, mass - burned_mass)*(mass - burned_mass)*cross_section

            if disposal_orbit.r_p < ALTITUDE_ATMOSPHERE_LIMIT + Earth.R:
                natural_decay_impact = 0 * u.year *u.pot_fragments
            else:
                natural_decay_time, natural_decay_impact = natural_decay(reduced_lifetime_file, CF_file, disposal_orbit, cross_section, mass - burned_mass, transfer_duration, op_duration, SUCCESS)
            
            # impact of unsuccessful manoeuvre would be 0 since spacecraft would stay above LEO region
            total_impact_score = (disposal_impact + natural_decay_impact)*PMD_success
            print("/!\ no impact computed if no disposal, lower impact if low PMD success rate, only because no CFs outside LEO protected region...")

            natural_impact_percentage = natural_decay_impact*PMD_success/total_impact_score*100
            disp_maneuver_impact_percentage = 100 - natural_impact_percentage
            print("--\n Computed space debris impact score is", "{:.3f}".format(total_impact_score), ". 0 percent operational impact, 100 percent disposal impact. Of which", "{:.3f}".format(disp_maneuver_impact_percentage), "percent from the disposal manoeuvre, ", "{:.3f}".format(natural_impact_percentage), "percent from the natural decay.")
            
            results = {"Space_Debris_Index": total_impact_score, "Operational_percentage": op_impact_percentage, "Disposal_manoeuvre_percentage": disp_maneuver_impact_percentage, "Natural_decay_percentage": natural_impact_percentage, 
                        "Transfer_duration": transfer_duration.to(u.year), "Mass_burnt": burned_mass}
            return results

    # #3 Cases if object has perigee in LEO
    # Case of LEO circular orbit
    elif operational_orbit.r_a == operational_orbit.r_p:
        print("LEO circular")
        CF_op = get_characterization_factor(CF_file, (operational_orbit.r_p - Earth.R), operational_orbit.inc)
        OP_impact = cross_section*mass*CF_op*alpha_param(mass)*op_duration

        # disposal manoeuvre
        if EOL_manoeuvre:
            print("EOLM")
            if (disposal_orbit.r_p - Earth.R) < ALTITUDE_ATMOSPHERE_LIMIT:
                no_2nd_burn = True
            else:
                no_2nd_burn = False
            manoeuvres, transfer_duration, transfer_orbit, burned_mass = high_thrust_delta_v(operational_orbit, disposal_orbit, mass, mean_thrust, Isp, no_2nd_burn)
            if burned_mass > mass:
                raise ValueError("Propellant mass is not sufficient to perform manoeuvre.")
            # Compute impact of disposal manoeuvre
            # Case from LEO into deorbitation
            if disposal_orbit.a < operational_orbit.a:
                disposal_impact = elliptical_orbit_decomposition(CF_file, transfer_orbit, mass - burned_mass) # intermediate impact
                if disposal_orbit.r_p < ALTITUDE_ATMOSPHERE_LIMIT + Earth.R:
                    natural_decay_impact = 0 * u.year *u.pot_fragments
                else:
                    # natural decay impact after successful EOLM
                    natural_decay_time, natural_decay_impact = natural_decay(reduced_lifetime_file, CF_file, disposal_orbit, cross_section, mass - burned_mass, transfer_duration, op_duration, SUCCESS)
            # case going from LEO to above LEO in graveyard
            elif disposal_orbit.a > operational_orbit.a:
                disposal_impact = elliptical_orbit_decomposition_up(CF_file, transfer_orbit, mass - burned_mass) # intermediate impact
                if disposal_orbit.r_p < ALTITUDE_LEO_LIMIT + Earth.R:
                    # natural decay impact after successful EOLM
                    natural_decay_time, natural_decay_impact = natural_decay(reduced_lifetime_file, CF_file, disposal_orbit, cross_section, mass - burned_mass, transfer_duration, op_duration, SUCCESS)
                else:
                    natural_decay_impact = 0 * u.year *u.pot_fragments
            else:
                disposal_impact = 0 * u.year *u.pot_fragments * u.kg **(-1) * u.m **(-2) # intermediate impact
                natural_decay_impact = 0 * u.year *u.pot_fragments
        else:
            transfer_duration = 0 * u.year
            disposal_impact = 0 * u.pot_fragments * u.year * u.kg **(-1) * u.m **(-2) # intermediate impact
            natural_decay_impact = 0 * u.pot_fragments * u.year
            burned_mass = 0 * u.kg

        # Compute impact of natural decay in the case of no EOLM or an unsuccessful end-of-life manoeuvre (EOLM)
        uns_natural_decay_time, uns_natural_decay_impact = natural_decay(reduced_lifetime_file, CF_file, operational_orbit, cross_section, mass, 0 * u.day, op_duration, FAIL)

        total_impact_score = OP_impact + (cross_section*(mass - burned_mass)*disposal_impact + natural_decay_impact)*PMD_success + (1-PMD_success)*uns_natural_decay_impact

        natural_impact_percentage = (natural_decay_impact*PMD_success + (1-PMD_success)*uns_natural_decay_impact)/total_impact_score*100
        op_impact_percentage = OP_impact/total_impact_score*100
        disp_maneuver_impact_percentage = 100 - natural_impact_percentage - op_impact_percentage

        print("--\n Computed space debris impact score is", "{:.3f}".format(total_impact_score), ".", "{:.3f}".format(op_impact_percentage), "percent from operations, ", "{:.3f}".format(disp_maneuver_impact_percentage), "percent from disposal manoeuvre, ", "{:.3f}".format(natural_impact_percentage), "percent from natural decay.")
        
        results = {"Space_Debris_Index": total_impact_score, "Operational_percentage": op_impact_percentage, "Disposal_manoeuvre_percentage": disp_maneuver_impact_percentage, "Natural_decay_percentage": natural_impact_percentage,
                    "Transfer_duration": transfer_duration.to(u.year), "Mass_burnt": burned_mass}
        return results

    # Cases of elliptical operational orbit
    else:
        print("Elliptical operational orbit partially higher than LEO or completely in LEO.")

        # Compute impact of half elliptical operational orbit, times two for the complete impact of one pass in LEO, times the number of orbits during the operational lifetime
        operational_impact = cross_section*mass*2*elliptical_orbit_decomposition(CF_file, operational_orbit, mass)*op_duration/operational_orbit.period.to(u.year)

        # disposal manoeuvre
        if EOL_manoeuvre:
            print("EOLM")
            if (disposal_orbit.r_p - Earth.R) < ALTITUDE_ATMOSPHERE_LIMIT:
                no_2nd_burn = True
            else:
                no_2nd_burn = False
            manoeuvres, transfer_duration, transfer_orbit, burned_mass = high_thrust_delta_v(operational_orbit, disposal_orbit, mass, mean_thrust, Isp, no_2nd_burn)
            if burned_mass > mass:
                raise ValueError("Propellant mass is not sufficient to perform manoeuvre.")
            # decompose elliptical disposal orbit and use time_to_anomaly after finding LTAN from position (meaning altitude)
            # Case from LEO into deorbitation
            if disposal_orbit.a < operational_orbit.a:
                disposal_impact = elliptical_orbit_decomposition(CF_file, transfer_orbit, mass - burned_mass) # intermediate impact
                if disposal_orbit.r_p < ALTITUDE_ATMOSPHERE_LIMIT + Earth.R:
                    natural_decay_impact = 0 * u.pot_fragments * u.year
                else:
                    # natural decay impact after successful EOLM
                    natural_decay_time, natural_decay_impact = natural_decay(reduced_lifetime_file, CF_file, disposal_orbit, cross_section, mass - burned_mass, transfer_duration, op_duration, SUCCESS)
            # case going from LEO to above LEO in graveyard
            elif disposal_orbit.a > operational_orbit.a:
                disposal_impact = elliptical_orbit_decomposition_up(CF_file, transfer_orbit, mass - burned_mass) # intermediate impact
                if disposal_orbit.r_p < ALTITUDE_LEO_LIMIT + Earth.R:
                    # natural decay impact after successful EOLM
                    natural_decay_time, natural_decay_impact = natural_decay(reduced_lifetime_file, CF_file, disposal_orbit, cross_section, mass - burned_mass, transfer_duration, op_duration, SUCCESS)
                else:
                    natural_decay_impact = 0 * u.pot_fragments * u.year
            else:
                disposal_impact = 0 * u.pot_fragments * u.year * u.kg **(-1) * u.m **(-2) # intermediate impact
                natural_decay_impact = 0 * u.pot_fragments * u.year
        else:
            transfer_duration = 0 * u.year
            disposal_impact = 0 * u.pot_fragments * u.year * u.kg **(-1) * u.m **(-2) # intermediate impact
            natural_decay_impact = 0 * u.pot_fragments * u.year
            burned_mass = 0 * u.kg
        
        # Compute impact of natural decay in the case of no EOLM or an unsuccessful end-of-life manoeuvre (EOLM)
        uns_natural_decay_time, uns_natural_decay_impact = natural_decay(reduced_lifetime_file, CF_file, operational_orbit, cross_section, mass, 0 * u.day, op_duration, FAIL)

        total_impact_score = operational_impact + (cross_section*(mass - burned_mass)*disposal_impact + natural_decay_impact)*PMD_success + (1-PMD_success)*uns_natural_decay_impact

        natural_impact_percentage = (natural_decay_impact*PMD_success + (1-PMD_success)*uns_natural_decay_impact)/total_impact_score*100
        op_impact_percentage = operational_impact/total_impact_score*100
        disp_maneuver_impact_percentage = 100 - natural_impact_percentage - op_impact_percentage

        print("--\n Computed space debris impact score is", "{:.3f}".format(total_impact_score), ".", "{:.3f}".format(op_impact_percentage), "percent from operations, ", "{:.3f}".format(disp_maneuver_impact_percentage), "percent from disposal manoeuvre, ", "{:.3f}".format(natural_impact_percentage), "percent from natural decay.")
        
        results = {"Space_Debris_Index": total_impact_score, "Operational_percentage": op_impact_percentage, "Disposal_manoeuvre_percentage": disp_maneuver_impact_percentage, "Natural_decay_percentage": natural_impact_percentage,
                    "Transfer_duration": transfer_duration.to(u.year), "Mass_burnt": burned_mass}
        return results