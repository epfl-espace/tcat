import numpy as np
import sys

from astropy import units as u

from poliastro.bodies import Earth, Moon
from poliastro.twobody import Orbit
from poliastro.iod import lambert
from Modules import PropulsionModule
from poliastro.constants import R_moon
#from astropy.constants import g0, G
from scipy import integrate
import matplotlib.pyplot as plt
from Phases.GenericPhase import GenericPhase
from Phases.Common_functions import *


class Descent(GenericPhase):
    """Returns the delta v necessary to perform the powered descent phase to the Moon surface.
    The powered descent phase starts from a descent orbit around the Moon (100 x 18.5 km)
    and this delta-v is assumed equal to 1.85 km/s.
       This function is not applicable to descents in atmosphere.

           Args:
               phase_id (str): Standard ID. Needs to be unique.
               plan (Plan_module.Plan): plan the phase belongs to
               initial_orbit (poliastro.twobody.Orbit): orbit from which start the descent phase
               delta_v_contingency (float): contingency to be applied to the delta_v

           Return:
               (u.m / u.s): total delta v to reach circular orbit
               (u.m / u.s): gravity losses
               (u.km): circular orbit height
               (u.s): ascent duration
               (poliastro.twobody.Orbit): final circular orbit
        """

    def __init__(self, phase_id, plan, initial_orbit, delta_v_contingency=0.1):
        super().__init__(phase_id, plan)
        self.initial_orbit = initial_orbit
        self.delta_v_contingency = delta_v_contingency
        self.delta_v = 1.85 * u.km / u.s

    def transfer(self):
        #TODO: add an input for the descent obit
        per_alt = 18.5 * u.km
        perigee = per_alt + R_moon
        ap_alt = 100. * u.km
        apogee = ap_alt + R_moon
        a = (apogee + perigee) / 2
        ecc = (apogee - perigee) / (apogee + perigee)

        descent_orbit = Orbit.from_classical(Moon, a, ecc, self.initial_orbit.inc, self.initial_orbit.raan,
                                             self.initial_orbit.argp, self.initial_orbit.nu, self.initial_orbit.epoch)

        return high_thrust_delta_v(self.initial_orbit, descent_orbit) # here there is also the duration of the transfer, outputs are (delta_v, transfer_orbit, delta_v_1, delta_v_2, duration)

    def apply(self):
        """ Asks the propulsion module to consume propellant according to delta v.
        Calls generic function to update orbit raan and epoch.
        """
        delta_v = self.delta_v + self.transfer().delta_v
        self.get_assigned_module().apply_delta_v(delta_v * (1 + self.delta_v_contingency), 'LTO-NRHO')
        self.update_servicer()


    def __str__(self):
        return ('--- \nLTO-NRHO: ' + super().__str__()
                + '\n\tDelta V ' + str((self.delta_v + self.transfer().delta_v) * (1 + self.delta_v_contingency)))




        #
        #
        # if h_0 >= 100 * u.km:
        #
        #     delta_v_desc_circ = np.sqrt(mi_moon/((h_0 + R_moon)**2)) \
        #                       - np.sqrt(mi_moon * (2. / (h_0 + R_moon) - 2. / (h_0 + 2 * R_moon + 100*u.km))) \
        #                       + np.sqrt(mi_moon * (2. / (100*u.km + R_moon) - 2. / (h_0 + 2 * R_moon + 100*u.km))) \
        #                       - np.sqrt(mi_moon/((100*u.km + R_moon)**2))
        #
        # else:
        #     raise ValueError("The initial orbit provided is lower than 100km.")
        #
        # return
#
# def descent(initial_height, initial_mass, landed_mass):
#     """Returns the delta v necessary to perform the powered ascent phase from the Moon surface.
#        This takes into account the transfer from the surface to a circular orbit.
#        This takes into account the downrange distance and the altitude at burnout.
#        This function is not applicable to ascents in atmosphere.
#        The circularization burn is modelled as impulsive.
#
#        Args:
#            initial_coord: takeoff lunar coordinates                    #Find a way to insert Lunar coord
#            final_orbit (poliastro.twobody.Orbit): final orbit
#            initial_mass (u.kg): initial mass
#            landed_mass (u.kg): final mass
#
#        Return:
#            (u.m / u.s): total delta v to reach circular orbit
#            (u.m / u.s): gravity losses
#            (u.km): circular orbit height
#            (u.s): ascent duration
#            (poliastro.twobody.Orbit): final circular orbit
#        """
#
#     "Constants calling"
#
#     g_0 = g0.value
#     g_m0 = (G * Moon.mass / R_moon ** 2).value  # Lunar gravitational acceleration on the surface
#     Rmoon = R_moon.value
#     mi_moon = Moon.k.value  # Moon's gravitational parameter
#     m_i = initial_mass  # Initial mass, at liftoff
#     m_f = landed_mass  # Final mass, at circular orbit
#     h_0 = initial_height
#
#     "Propulsion system constants"
#
#     #thrust = PropulsionModule.PropulsionModule.reference_thrust  # Takeoff thrust
#     thrust = (44000. * u.N).value  # Takeoff thrust
#     # isp = PropulsionModule.isp  # Engine Specific Impulse [s]
#     isp = 311.  # Engine Specific Impulse [s]
#
#     err_h = 150
#     err_v = 150 # Initialize the error control
#     thrust_temp = thrust    # Initialize the mass at the end of ascension phase
#     i=0
#     while err_h > 100 or err_v > 100:
#
#         m_dot = thrust_temp / isp / g_0  # Propellant mass flow rate [kg/s]
#         m_prop_descent = m_i - m_f  # Propellant mass used in the ascent phase
#         t_burn = m_prop_descent / m_dot  # Burn time
#
#         # h_turn = 50.  # Height at which pitchover begins [m]
#
#         t_0 = 0.  # Initial time for the numerical integration [s]
#         t_coast = 500.  # Coasting time [s]
#         t_f = t_burn + t_coast  # Final time for the numerical integration
#         step = num = 500.  # Number of integration step
#         t_span = (t_0, t_f)  # Range of integration
#
#         "Initial conditions"
#
#         g = g_m0 / (1 + h_0 / Rmoon) ** 2  # Gravitational variation with altitude h
#         v_0 = np.sqrt(mi_moon * (2. / (h_0 + Rmoon) - 1 / (h_0 + 2 * Rmoon + 100000)))  # Initial velocity
#         gamma_0 = (-1. * u.deg).to(u.rad).value  # Initial flight path angle [deg]. TO DO: add a vertical phase and then an instant gamma change.
#         x_0 = 0.  # Initial downrange distance
#         h_0 = initial_height  # Initial altitude
#         vG_0 = -g * np.sin(gamma_0)  # Initial value of velocity loss due to gravity
#
#         f_0 = ([v_0, gamma_0, x_0, h_0, vG_0, m_i])  # Initial conditions vector
#
#
#         "Auxiliary functions"
#         "REF: Howard D. Curtis, Orbital Mechanics for Engineering Students, 3rd ed., "
#
#         def rates(t, f):
#             """
#             Calculates the time rates df/dt of the variables f(t)
#             in the equations of motion of a gravity turn trajectory.cd
#             """
#             dfdt = np.zeros(6)  # Initialize dfdt as a column vector
#
#             v = f[0]  # Velocity
#             gamma = f[1]  # Flight path angle
#             x = f[2]  # Downrange distance
#             h = f[3]  # Altitude
#             vG = f[4]  # Velocity loss due to gravity
#             m = f[5]  # Total mass of the vehicle
#             g = g_m0 / (1 + h / Rmoon) ** 2  # Gravitational variation with altitude h
#
#             """When time t exceeds the burn time, set the thrust_temp and the mass flow
#             rate equal to zero:"""
#
#             if t < t_burn:
#                 m_dot = - thrust_temp / isp / g_0
#                 T = thrust_temp  # Current thrust_temp
#                 # m = (m_i + m_dot * t)  # Current vehicle mass
#             else:
#                 T = 0.  # Current thrust
#                 # m = m_i - m_dot * t_burn  # Current vehicle mass
#                 m_dot = 0.
#
#             """Define the first derivatives of v, gamma, x, h, and vG and
#             ("dot" means time derivative):"""
#
#             """Start the gravity turn when h = h_turn:"""
#
#             # if h < h_turn:
#             #     gamma_dot = 0.
#             #     v_dot = T / m - g
#             #     x_dot = 0.
#             #     h_dot = v
#             #     vG_dot = -g
#             #
#             #
#             # else:
#             v_dot = -T / m - g * np.sin(gamma)  # Eqn. 11.6
#             gamma_dot = -1. / v * (g - v ** 2 / (Rmoon + h)) * np.cos(gamma)  # Eqn. 11.7
#             x_dot = Rmoon / (Rmoon + h) * v * np.cos(gamma)  # Eqn. 11.8
#             h_dot = - v * np.sin(gamma)  # Eqn. 11.8
#             vG_dot = - g * np.sin(gamma)  # Gravity loss rate
#
#             "Load the first derivatives of f(t) into the vector dfdt:"
#
#             dfdt[0] = v_dot
#             dfdt[1] = gamma_dot
#             dfdt[2] = x_dot
#             dfdt[3] = h_dot
#             dfdt[4] = vG_dot
#             dfdt[5] = m_dot
#
#             return dfdt
#
#         """Call to Runge-Kutta numerical integrator 'RK45'.
#         RK45 solves the system of equations df/dt = f(t)"""
#
#         t = np.linspace(t_0, t_f, step)
#
#         #print(t)
#
#         def landing_completed1(t, f):  # This part is needed to stop the integration
#             return f[3]
#
#         def landing_completed2(t, f):  # This part is needed to stop the integration
#             return f[0]
#
#         landing_completed1.terminal = True  # when the altitude becomes zero.
#         landing_completed2.terminal = True  # when the velocity becomes zero.
#
#         def landing_velocity(t, f):
#             return f[0]
#
#         sol = integrate.solve_ivp(rates, t_span, f_0, t_eval=t, dense_output=True, events=(landing_completed1, landing_completed2, landing_velocity))
#         #print(sol.sol(sol.t_events[0]))
#         t = sol.t
#         v = sol.y[0, :] / 1000.  # Velocity [km / s]
#         gamma = (sol.y[1, :] * u.rad).to(u.deg)  # Flight path angle [deg]
#         x = sol.y[2, :] / 1000.  # Downrange distance [km]
#         h = sol.y[3, :] / 1000.  # Altitude [km]
#         vG = sol.y[4, :] / 1000.  # Velocity loss due to gravity [km / s]
#         m = sol.y[5, :]  # Vehicle mass [kg]
#         # print(sol)
#
#         """Delta-v computation"""
#
#         def find_nearest(array, value):
#             array = np.asarray(array)
#             idx = (np.abs(array - value)).argmin()
#             return array[idx]
#
#         vG_bo = vG[np.where(t == find_nearest(t, t_burn))]  # Gravity loss computed until burnout
#         delta_v_descent = isp * g_0 * np.log(m_i / m[-1]) - vG_bo  # delta-v computed from the launch pad to the aposelene
#             # delta_v_circ = np.sqrt(mi_moon / (Rmoon + h[-1])) - v[-1]  # delta-v computed from the aposelene suborbital trajectory to the corrispondent circular orbit
#             # m_f_actual = m[-1] * np.e ** (-delta_v_descent / isp / g_0)    # final mass relative to circularization maneuver
#
#         err_h = np.abs(h[-1] * 1000)
#
#         if err_h > 10:
#             thrust_temp = thrust_temp - 15
#             print("altezza", err_h, thrust_temp)
#
#
#         err_v = np.abs(v[-1] * 1000)
#         if err_v > 10:
#             thrust_temp = thrust_temp + 10
#             print("velocità",err_v, thrust_temp)
#
#
#
#
#
#
#
#
#         # err = m_f_actual - m_f
#         # if err < 0:
#         #     m_f_coast += -err
#         # else:
#         #     m_f_coast += err
#
#         i+=1
#
#         if i==5000:
#             print('\nSomething went wrong. The iteration takes too long.')
#             sys.exit()
#
#         # print(err, thrust_temp, thrust_temp_old)         # Changing final mass, the script fails because the t_burn > t_bo, and for some reason this affect the mass calculation (see the script without while loop)
#
#
#
#         # """PLOTS"""
#         # plt.close('all')
        #
        # f1 = plt.figure(1)
        # plt.plot(x, h)
        # plt.xlabel('Downrange distance [km]')
        # plt.ylabel('Altitude [km]')
        # plt.show()
        #
        # f2 = plt.figure(2)
        # plt.plot(t, gamma)
        # plt.xlabel('Time [s]')
        # plt.ylabel('Flight path angle [deg]')
        # plt.show()
        #
        # f3 = plt.figure(3)
        # plt.plot(t, v)
        # plt.xlabel('Time [s]')
        # plt.ylabel('Velocity [km/s]')
        # plt.show()
        #
        # f4 = plt.figure(4)
        # plt.plot(t, x)
        # plt.xlabel('Time [s]')
        # plt.ylabel('Downrange distance [km]')
        # plt.show()
        #
        # f5 = plt.figure(5)
        # plt.plot(t, h)
        # plt.xlabel('Time [s]')
        # plt.ylabel('Altitude [km]')
        # plt.show()
        #
        # f6 = plt.figure(6)
        # plt.plot(t, vG)
        # plt.xlabel('Time [s]')
        # plt.ylabel('Velocity loss [km/s]')
        # plt.show()
        #
        # f7 = plt.figure(7)
        # plt.plot(t, m)
        # plt.xlabel('Time [s]')
        # plt.ylabel('Vehicle mass [kg]')
        # plt.show()
        # plt.close('all')
        #
        # return print(f"Delta-v needed for the descent phase is {delta_v_descent /1000 * u.km / u.s}.\n"
        #                          # f"Delta-v needed for circularization in LLO of {h[-1] * u.km} is {delta_v_circ /1000 * u.km / u.s}.\n"
        #                          # f"The total delta-v needed is {(delta_v_descent + delta_v_circ) /1000 * u.km / u.s}.\n"
        #                           f"The time needed to complete the descent is {t[-1] * u.s}."), \
        #        plt.show()

# descent(15500, 15100., 8000.)
# plt.show()