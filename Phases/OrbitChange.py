from astropy.time import Time

from Modules.PropulsionModule import *
from Phases.Common_functions import *
from Phases.GenericPhase import GenericPhase
from poliastro.bodies import Earth

from Scenarios.ScenarioParameters import ALTITUDE_ATMOSPHERE_LIMIT


class OrbitChange(GenericPhase):
    """A Phase that represents changes made by a servicer to change orbit.
    The method in Common_functions are used and the assumptions are detailed in their documentation.
    Needs to be assigned to a propulsion module.
    
    Args:
        phase_id (str): Standard id. Needs to be unique.
        plan (Plan_module.Plan): plan the phase belongs to
        final_orbit (poliastro.twobody.Orbit or object with current_orbit attribute): orbit to be reached
                                                                                      or object with current_orbit
        initial_orbit (poliastro.twobody.Orbit): (optional) orbit of the servicer before the phase
                                                 (specified for possible reference during planning)
        delta_v_contingency (float): mass_contingency to be applied to the delta_v
        raan_specified (bool): denotes if the orbit change is made to a specific raan,
                               if True, the raan of the target is matched, either via manoeuver or nodal precession
        raan_cutoff (u.<Angle_unit>): cutoff over which drift phasing is used rather than manoeuvres to correct raan

    Attributes: (plus attributes from GenericPhase, some might be overridden by new definitions in this module)
        final_orbit (poliastro.twobody.Orbit or any object with current_orbit attribute): orbit to be reached
        planned_final_orbit (poliastro.twobody.Orbit): orbit to be reached after maneuvers
                                                       as specified in plan (typically used for phase reset)
        initial_orbit (poliastro.twobody.Orbit): optional, orbit of the servicer before the phase
                                                 (possibly specified for reference during planning)
        planned_initial_orbit (poliastro.twobody.Orbit): optional, orbit of the servicer before the phase
                                                        as specified in plan (typically used for phase reset)
        delta_v_contingency (float): mass_contingency to be applied to the delta_v
        raan_specified (bool): denotes if the orbit change is made to a specific raan,
                               if True, the raan of the target is matched, either via manoeuver or nodal precession
        raan_cutoff (u.<Angle_unit>): cutoff over which drift phasing is used rather than manoeuvres to correct raan
        raan_drift (u.<Angle_unit>): delta raan completed by the servicer during the orbit change
        manoeuvres ([Common_functions.Manoeuvre]): List of manoeuvres to reach the final orbit
    """
    def __init__(self, phase_id, plan, final_orbit, initial_orbit=None, delta_v_contingency=0.1,
                 raan_specified=False, raan_cutoff=0.5 * u.deg, raan_phasing_absolute=False):
        super().__init__(phase_id, plan)
        self.final_orbit = final_orbit
        self.planned_final_orbit = final_orbit
        self.initial_orbit = initial_orbit
        self.planned_initial_orbit = initial_orbit
        self.delta_v_contingency = delta_v_contingency
        self.raan_specified = raan_specified
        self.raan_phasing_absolute = raan_phasing_absolute
        self.raan_cutoff = raan_cutoff
        self.raan_drift = 0. * u.deg
        # TODO: add duration override? add planned delta v?

    def assign_module(self, assigned_module):
        """ Assigns a module of a servicer to the phase. Checks for appropriate module type.
        Also computes first estimates of manoeuvres required to help convergence_margin of propulsion module.

        Args:
            assigned_module (Fleet_module.PropulsionModule or CaptureModule): Added module
        """
        if isinstance(assigned_module, PropulsionModule):
            self.assigned_module = assigned_module
        else:
            raise TypeError('Non-propulsion module assigned to Orbit Change phase.')

        # if both initial and final orbit are available, get first estimate of manoeuvres
        # (helps convergence as propulsion module is sized based on thrust and delta_v required for orbit changes)
        if not isinstance(self.final_orbit, Orbit):
            self.final_orbit = self.final_orbit.current_orbit
        if self.initial_orbit:
            self.compute_main_manoeuvres(initial_orbit=self.initial_orbit, final_orbit=self.final_orbit)

    def get_delta_v(self, contingency=False):
        """ Return total delta v for all manoeuvres in orbit change.

        Return:
            (u.m / u.s): delta v for total
        """
        delta_v = 0. * u.m / u.s
        for manoeuvre in self.manoeuvres:
            delta_v += manoeuvre.get_delta_v()
        if contingency:
            delta_v += delta_v * self.delta_v_contingency
        return delta_v

    def apply(self):
        """ Moves the servicer to the final orbit.
        Asks the propulsion module to consume propellant according to computed manoeuvres.
        Calls generic function to update orbit raan and epoch.
        """
        # In case the final orbit is given as a servicer or target, retrieve the object's orbit
        if not isinstance(self.final_orbit, Orbit):
            self.final_orbit = self.final_orbit.current_orbit

        # update the final orbit by adding raan drift to match servicer epoch
        self.final_orbit = update_orbit(self.final_orbit, self.get_assigned_spacecraft().current_orbit.epoch, self.get_assigned_spacecraft().get_insertion_orbit().epoch)

        # update the initial orbit by retrieving current servicer orbit
        self.initial_orbit = self.get_assigned_spacecraft().current_orbit

        # compute and apply delta v through appropriate propulsion module
        self.apply_manoeuvres()

        # update servicer according to computed orbits and duration
        self.update_spacecraft()
        self.spacecraft_snapshot = self.build_spacecraft_snapshot_string()
    
    # def apply_delta_v(self):
    #     """ Compute the delta v for the maneuver and possible orbit maintenance during phasing.
    #     Apply this delta v according to assigned module.
    #     """
    #     # compute maneuver delta v, duration and possible transfer orbit in case of high thrust orbit change
    #     self.delta_v, maneuver_duration = self.compute_maneuver()
        
    #     # compute phasing maneuver if phasing is applicable
    #     # otherwise simply compute natural raan drift during maneuver
    #     if self.raan_specified:
    #         self.duration, self.raan_drift, optional_delta_v = self.compute_phasing(maneuver_duration)
    #     else:
    #         self.duration, self.raan_drift, optional_delta_v = self.compute_phasing(maneuver_duration,
    #                                                                                 total_duration=maneuver_duration)
    #     # compute additional maintenance delta v on initial orbit in case of significant drifting time at low altitude
    #     self.delta_v = self.delta_v + compute_altitude_maintenance_delta_v(self.duration - maneuver_duration,
    #                                                                        self.initial_orbit) + optional_delta_v
    #     # apply to assigned propulsion module
    #     self.get_assigned_module().apply_delta_v(self.delta_v * (1 + self.delta_v_contingency), 'phasing')

    def update_spacecraft(self, spacecraft=None):
        """ Update the orbits of the servicer and attached targets after phase has ended.
                If no specific servicer is given as attribute, the servicer assigned to the phase is taken.
        Changes are the orbit raan and epoch according to the specified duration and the servicer orbit at time of
        execution. This function may be redefined within inheriting phases.

        Args:
            servicer (Servicer):  (optional) servicer to be updated
                                This optional attributes is used to update servicers connected to the servicer assigned
                                to the phase, for instance to update the whole mothership if a module of a kit is
                                assigned to the phase.
        """
        # update epochs
        self.starting_date = self.initial_orbit.epoch
        self.end_date = self.starting_date + self.duration

        # format raan
        current_raan = (self.initial_orbit.raan + self.raan_drift) % (360. * u.deg)
        if current_raan > 180. * u.deg:
            current_raan = current_raan - 360. * u.deg
            
        # compute new orbit
        new_orbit = Orbit.from_classical(self.final_orbit.attractor, self.final_orbit.a, self.final_orbit.ecc,
                                         self.final_orbit.inc, current_raan,
                                         self.final_orbit.argp, self.final_orbit.nu,
                                         self.end_date)
        self.final_orbit = new_orbit

        if spacecraft is None:
            spacecraft = self.get_assigned_spacecraft()
        # assign new orbit to servicer and attached targets
        spacecraft.change_orbit(new_orbit)

    def apply_manoeuvres(self, mass=None, thrust=None, isp=None):
        """ Compute and apply the delta v for the maneuver and possible orbit maintenance during phasing.
        Specific arguments can be given to overwrite the current attributes.
        This methods calls compute_manoeuvres and compute_phasing.

        Args:
            mass (u.kg): (optional) servicer mass at the start of the maneuver
            thrust (u.N): (optional) servicer thrust capability at the start of the maneuver
            isp (u.s): (optional) servicer isp capability
        """
        # retrieve required module attributes
        if mass is None:
            mass = self.get_assigned_spacecraft().get_current_mass()
        if thrust is None:
            thrust = self.get_assigned_module().reference_thrust
        if isp is None:
            isp = self.get_assigned_module().isp

        # compute main manoeuvres and duration without raan taken into account
        main_manoeuvres, transfer_duration = self.compute_main_manoeuvres(mass=mass, thrust=thrust, isp=isp)
        for manoeuvre in main_manoeuvres:
            self.manoeuvres.append(manoeuvre)

        # compute phasing manoeuvre
        phasing_duration, raan_drift, raan_change_manoeuvre = self.compute_precession(transfer_duration,
                                                                                      raan_phasing=self.raan_specified, raan_phasing_absolute=self.raan_phasing_absolute)
        self.raan_drift = raan_drift
        self.duration = phasing_duration + transfer_duration
        if raan_change_manoeuvre and raan_change_manoeuvre.delta_v > 0. * u.m / u.s:
            self.manoeuvres.append(raan_change_manoeuvre)

        # compute additional maintenance delta v on initial orbit in case of significant drifting time at low altitude
        maintenance_manoeuvre = compute_altitude_maintenance_delta_v(phasing_duration, self.initial_orbit)
        if maintenance_manoeuvre and maintenance_manoeuvre.delta_v > 0. * u.m / u.s:
            self.manoeuvres.insert(0, maintenance_manoeuvre)

        # apply to assigned propulsion module
        self.get_assigned_module().apply_delta_v(self.get_delta_v(contingency=True), 'main_thrusters')

    def compute_main_manoeuvres(self, initial_orbit=None, final_orbit=None, mass=None, thrust=None, isp=None):
        """ Returns the manoeuvres necessary to perform the orbit change, without raan changes.
        This methods applies either low thrust assumptions or high thrust assumption depending on assigned module
        propulsion type. For low thrust manoeuvres, the duty_cycle is assumed to be 0.9, and the coasting cycle 0.75
        (meaning thrusters can be used 25% of the time) which might be conservative for circular orbits. 
        Specific arguments can be given to overwrite the current attributes.

        Args:
            initial_orbit (astropy.time.Time): (optional) initial orbit
            final_orbit (astropy.time.Time): (optional) final orbit
            mass (u.kg): (optional) servicer mass at the start of the maneuver
            thrust (u.N): (optional) servicer thrust capability at the start of the maneuver
            isp (u.s): (optional) servicer isp capability

        Return:
            manoeuvres ([Common_functions.Manoeuvre]): list of manoeuvres to perform orbit change without raan change
            transfer_duration(u.<Time_unit>): duration of transfer (from first burn to last)
        """
        # retrieve default parameters
        if initial_orbit is None:
            initial_orbit = self.initial_orbit
        if final_orbit is None:
            final_orbit = self.final_orbit
        if mass is None:
            mass = self.get_assigned_spacecraft().get_current_mass()
        if thrust is None:
            thrust = self.get_assigned_module().reference_thrust
        if isp is None:
            isp = self.get_assigned_module().isp

        spacecraft_burn_in_atmosphere = False
        # Check if 2nd burn of Homann is required (if spacecraft burns in atmosphere or not)
        if final_orbit.r_p - final_orbit.attractor.R_mean < ALTITUDE_ATMOSPHERE_LIMIT:
            spacecraft_burn_in_atmosphere = True

        # apply appropriate methods depending on propulsion and get manoeuvres and their duration
        if self.assigned_module.prop_type == 'electrical':
            manoeuvres, transfer_duration = low_thrust_delta_v(initial_orbit, final_orbit, mass, thrust, isp)
        else:
            manoeuvres, transfer_duration, transfer_orbit, burned_mass = high_thrust_delta_v(initial_orbit, final_orbit, mass, thrust, isp, spacecraft_burn_in_atmosphere)

        return manoeuvres, transfer_duration

    # def compute_maneuver(self, orbit1=None, orbit2=None, mass=None, thrust=None):
    #     """ Returns the delta v necessary to perform the phase.
    #     Particular orbits, masses and thrusts can be specified to make some quick comparisons or optimizations.
    #     The default orbits used are those defined as initial and final for the phase.

    #     Args:
    #         orbit1 (astropy.time.Time): (optional) initial orbit
    #         orbit2 (astropy.time.Time): (optional) final orbit
    #         mass (u.kg): (optional) servicer mass at the start of the maneuver
    #         thrust (u.N): (optional) servicer thrust capability at the start of the maneuver

    #     Return:
    #         (u.m / u.s) : required delta v
    #         (u.<time unit>): duration of the maneuver (without phasing durations)
    #     """
    #     # retrieve default parameters
    #     if orbit1 is None:
    #         orbit1 = self.initial_orbit
    #     if orbit2 is None:
    #         orbit2 = self.final_orbit
    #     if mass is None:
    #             mass = self.get_assigned_spacecraft().get_current_mass()
    #     if thrust is None:
    #         thrust = self.get_assigned_module().reference_thrust

    #     # apply appropriate function depending on propulsion
    #     if self.assigned_module.prop_type == 'electrical':
    #         delta_v, maneuver_duration = low_thrust_delta_v(orbit1, orbit2, mass, thrust)
    #     elif orbit1.attractor == Earth and orbit2.attractor == Moon:
    #         delta_v, _, _, maneuver_duration, _, _, _ = compute_translunar_injection(orbit1, orbit2)
    #     else:
    #         delta_v, _, _, _, maneuver_duration = high_thrust_delta_v(orbit1, orbit2)
                
    #     return delta_v, maneuver_duration

    def compute_precession(self, manoeuvre_duration, initial_orbit=None, final_orbit=None, raan_phasing=False,
                           mass=None, thrust=None, isp=None, raan_phasing_absolute=False):
        """ Compute raan drift and phasing duration according to either of these two cases:

        Case 1:
            raan_phasing is true, therefore phasing will be computed based on the specified raan
            for the initial and final orbit.

        Case 2:
            raan_phasing is False. In this case, the final orbit raan is disregarded and instead the
            raan drift is computed based on manoeuvre_duration only.

        These computations take into account the raan drift during maneuvers (significant for low-thrust) using
        a simplified linear model.

        Args:
            manoeuvre_duration (u.<time unit>): duration of the maneuver without phasing
            initial_orbit (astropy.twobody.Orbit): (optional) initial orbit (serve as raan reference)
            final_orbit (astropy.twobody.Orbit): (optional) final orbit (serve as raan reference)
            raan_phasing (bool): (optional) if True, final raan the orbit change is designed to target the final raan
            mass (u.kg): (optional) servicer mass at the start of the maneuver
            thrust (u.N): (optional) servicer thrust capability at the start of the maneuver
            isp (u.s): (optional) servicer isp capability

        Return:
             (u.day): total duration
             (u.deg): raan drift
             (Common_functions.Manoeuvre): possible manoeuvre for the raan change if under cutoff
        """
        # retrieve default parameters
        if initial_orbit is None:
            initial_orbit = self.initial_orbit
        if final_orbit is None:
            final_orbit = self.final_orbit
        if mass is None:
            mass = self.get_assigned_spacecraft().get_current_mass()
        if thrust is None:
            thrust = self.get_assigned_module().reference_thrust
        if isp is None:
            isp = self.get_assigned_module().isp

        # compute mean nodal precession during manoeuvre (significant for low thrust manoeuvres)
        _, initial_nodal_precession_speed = nodal_precession(initial_orbit)
        _, final_nodal_precession_speed = nodal_precession(final_orbit)
        transfer_mean_nodal_precession_speed = (initial_nodal_precession_speed + final_nodal_precession_speed) / 2

        # finalorbit.raan != initialorbit.raan
        if raan_phasing:
            # Compute drift occuring during pre-computed manoeuvre
            maneuver_delta_precession = transfer_mean_nodal_precession_speed - final_nodal_precession_speed
            maneuver_delta_raan = manoeuvre_duration * maneuver_delta_precession

            # Compute remainign raan to be covered by phasing
            delta_raan = (final_orbit.raan - initial_orbit.raan - maneuver_delta_raan).to(u.deg) % (360 * u.deg)

            # Correct raan loop
            if delta_raan > 180. * u.deg:
                delta_raan = delta_raan - 360. * u.deg
            if delta_raan < -180. * u.deg:
                delta_raan = delta_raan + 360. * u.deg
 
            # Check if phasing can be avoided to the benefit of direct raan change manoeuvre
            if abs(delta_raan) < self.raan_cutoff:
                phasing_duration = 0. * u.day
                if self.assigned_module.prop_type == 'electrical':
                    raan_change_manoeuvre, raan_change_duration = low_thrust_raan_change_delta_v(delta_raan,
                                                                                                 initial_orbit,
                                                                                                 final_orbit,
                                                                                                 mass, thrust, isp)
                else:
                    raan_change_manoeuvre, raan_change_duration = high_thrust_raan_change_delta_v(delta_raan,
                                                                                                  initial_orbit,
                                                                                                  final_orbit,
                                                                                                  mass, thrust, isp)
                raan_drift = delta_raan + maneuver_delta_raan
            # Cutoff not available, phasing is triggered
            # here nodal precession is computed to reach a specific raan value, taking in account absolute nodal
            # precession
            elif raan_phasing_absolute:
                raan_change_manoeuvre = None
                phasing_duration = delta_raan / initial_nodal_precession_speed
                raan_drift = (initial_nodal_precession_speed * phasing_duration + transfer_mean_nodal_precession_speed * manoeuvre_duration)
            # here nodal precession is computed to reach a specific raan value, taking in account relative nodal
            # precession between two orbits
            else:
                raan_change_manoeuvre = None

                relative_delta_precession = initial_nodal_precession_speed - final_nodal_precession_speed
                if np.sign(delta_raan) != np.sign(relative_delta_precession):
                    raise RuntimeError('Nodal precession phasing problem in ', self.ID,
                                       ' : the precession is in the opposite direction of the phasing.')
                else:
                    phasing_duration = delta_raan / relative_delta_precession

                raan_drift = (initial_nodal_precession_speed * phasing_duration + transfer_mean_nodal_precession_speed * manoeuvre_duration)

        # finalorbit.raan = initialorbit.raan
        else:
            # No manoeuvre needed
            raan_change_manoeuvre = None
            phasing_duration = 0. * u.day

            raan_drift = transfer_mean_nodal_precession_speed * manoeuvre_duration

        return phasing_duration.to(u.day), raan_drift.to(u.deg), raan_change_manoeuvre

    def get_operational_cost(self):
        """ Returns the operational cost of the phase based on assumed FTE and associated costs.

        Return:
            (float): operational cost in Euros
        """
        fte_operation = 0.  # FTE
        cost_fte_operation = 100 * 1000 / u.year  # Euros per year
        return (fte_operation * cost_fte_operation * self.duration).decompose()

    def reset(self):
        """ Reset the orbits, duration, delta v, raan drift and epochs based on parameters defined during planning. """
        # reset main parameters
        self.duration = 0. * u.second
        self.spacecraft_snapshot = None
        self.starting_date = Time("2000-01-01 12:00:00")
        self.end_date = Time("2000-01-01 12:00:00")
        self.raan_drift = 0. * u.deg
        self.manoeuvres = []

        # reset the final orbit
        self.final_orbit = self.planned_final_orbit
        
        # reset the initial orbit
        self.initial_orbit = self.planned_initial_orbit

    def build_spacecraft_snapshot_string(self):
        """ Save current assigned servicer as a snapshot for future references and post-processing. """
        # Combine all manoeuvres into a single string
        manoeuvres_string = ""
        for manoeuvre in self.manoeuvres:
            manoeuvres_string += ("\t\t" + str(manoeuvre) + " \n")

        return('--- \nOrbit change: ' + super().build_spacecraft_snapshot_string()
        + '\n\t\u0394V: ' + "{0:.1f}".format(self.get_delta_v() * (1 + self.delta_v_contingency))
        + "\n\t\u0394m: " + "{0:.1f}".format(self.get_assigned_spacecraft().get_main_propulsion_module().delta_mass)
        + "\n\tManoeuvres: \n " + manoeuvres_string[:-2])

