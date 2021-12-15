import numpy as np
import sys

from astropy import units as u

from poliastro.bodies import Earth, Moon
from poliastro.twobody import Orbit
from poliastro.iod import lambert
from Modules import PropulsionModule
from poliastro.constants import R_moon
from astropy.constants import g0, G
from scipy import integrate
import matplotlib.pyplot as plt


def ascent(liftoff_mass, final_mass):
    """Returns the delta v necessary to perform the powered ascent phase from the Moon surface.
       This takes into account the transfer from the surface to a circular orbit.
       This takes into account the downrange distance and the altitude at burnout.
       This function is not applicable to ascents in atmosphere.
       The circularization burn is modelled as impulsive.

       Args:
           initial_coord: takeoff lunar coordinates                    #Find a way to insert Lunar coord
           final_orbit (poliastro.twobody.Orbit): final orbit
           liftoff_mass (u.kg): initial mass
           final_mass (u.kg): final mass

       Return:
           (u.m / u.s): total delta v to reach circular orbit
           (u.m / u.s): gravity losses
           (u.km): circular orbit height
           (u.s): ascent duration
           (poliastro.twobody.Orbit): final circular orbit
       """

    "Constants calling"

    g_0 = g0.value
    g_m0 = (G * Moon.mass / R_moon ** 2).value  # Lunar gravitational acceleration on the surface
    Rmoon = R_moon.value
    mi_moon = Moon.k.value  # Moon's gravitational parameter
    m_i = liftoff_mass  # Initial mass, at liftoff
    m_f = final_mass  # Final mass, at circular orbit

    "Propulsion system constants"

    #thrust = PropulsionModule.PropulsionModule.reference_thrust  # Takeoff thrust
    thrust = (16000. * u.N).value  # Takeoff thrust
    # isp = PropulsionModule.isp  # Engine Specific Impulse [s]
    isp = 311.  # Engine Specific Impulse [s]

    err = 11  # Initialize the error control
    m_f_coast = m_f    # Initialize the mass at the end of ascension phase
    i=0
    while np.abs(err) > 5:

        m_dot = thrust / isp / g_0  # Propellant mass flow rate [kg/s]
        m_prop_ascent = m_i - m_f_coast  # Propellant mass used in the ascent phase
        t_burn = m_prop_ascent / m_dot  # Burn time

        h_turn = 50.  # Height at which pitchover begins [m]

        t_0 = 0.  # Initial time for the numerical integration [s]
        t_coast = 500.  # Coasting time [s]
        t_f = t_burn + t_coast  # Final time for the numerical integration
        step = num = 500  # Number of integration step
        t_span = (t_0, t_f)  # Range of integration

        "Initial conditions"

        v_0 = 0.  # Initial velocity
        gamma_0 = (89.85 * u.deg).to(u.rad).value  # Initial flight path angle [deg]. TO DO: add a vertical phase and then an instant gamma change.
        x_0 = 0.  # Initial downrange distance
        h_0 = 0.  # Initial altitude
        vG_0 = 0.  # Initial value of velocity loss due to gravity

        f_0 = ([v_0, gamma_0, x_0, h_0, vG_0, m_i])  # Initial conditions vector

        """Check that T2mW is possible"""

        T2mW = thrust / (m_i * g_m0)  # Thrust to moon weight ratio

        if T2mW <= 1:
            print('Thrust to Moon Weight ratio must be greater than 1.\n'
                  'Try to reduce initial mass and/or to increase the maximum thrust')
            sys.exit()

        "Auxiliary functions"
        "REF: Howard D. Curtis, Orbital Mechanics for Engineering Students, 3rd ed., "

        def rates(t, f):
            """
            Calculates the time rates df/dt of the variables f(t)
            in the equations of motion of a gravity turn trajectory.cd
            """
            dfdt = np.zeros(6)  # Initialize dfdt as a column vector

            v = f[0]  # Velocity
            gamma = f[1]  # Flight path angle
            x = f[2]  # Downrange distance
            h = f[3]  # Altitude
            vG = f[4]  # Velocity loss due to gravity
            m = f[5]  # Total mass of the vehicle
            g = g_m0 / (1 + h / Rmoon) ** 2  # Gravitational variation with altitude h

            """When time t exceeds the burn time, set the thrust and the mass flow
            rate equal to zero:"""

            if t < t_burn:
                m_dot = - thrust / isp / g_0
                T = thrust  # Current thrust
                # m = (m_i + m_dot * t)  # Current vehicle mass
            else:
                T = 0.  # Current thrust
                # m = m_i - m_dot * t_burn  # Current vehicle mass
                m_dot = 0.

            """Define the first derivatives of v, gamma, x, h, and vG and
            ("dot" means time derivative):"""

            """Start the gravity turn when h = h_turn:"""

            if h < h_turn:
                gamma_dot = 0.
                v_dot = T / m - g
                x_dot = 0.
                h_dot = v
                vG_dot = -g


            else:
                v_dot = T / m - g * np.sin(gamma)  # Eqn. 11.6
                gamma_dot = -1. / v * (g - v ** 2 / (Rmoon + h)) * np.cos(gamma)  # Eqn. 11.7
                x_dot = Rmoon / (Rmoon + h) * v * np.cos(gamma)  # Eqn. 11.8
                h_dot = v * np.sin(gamma)  # Eqn. 11.8
                vG_dot = -g * np.sin(gamma)  # Gravity loss rate

            "Load the first derivatives of f(t) into the vector dfdt:"

            dfdt[0] = v_dot
            dfdt[1] = gamma_dot
            dfdt[2] = x_dot
            dfdt[3] = h_dot
            dfdt[4] = vG_dot
            dfdt[5] = m_dot

            return dfdt

        """Call to Runge-Kutta numerical integrator 'RK45'. 
        RK45 solves the system of equations df/dt = f(t)"""

        t = np.linspace(t_0, t_f, step)

        def turn_completed(t, f):  # This part is needed to stop the integration
            return f[1]

        turn_completed.terminal = True  # when the flight path angle becomes zero.

        def burnout(t, f):
            return f[4]

        sol = integrate.solve_ivp(rates, t_span, f_0, t_eval=t, dense_output=True, events=(turn_completed, burnout))
        #print(sol.sol(sol.t_events[0]))
        t = sol.t
        v = sol.y[0, :] / 1000.  # Velocity [km / s]
        gamma = (sol.y[1, :] * u.rad).to(u.deg)  # Flight path angle [deg]
        x = sol.y[2, :] / 1000.  # Downrange distance [km]
        h = sol.y[3, :] / 1000.  # Altitude [km]
        vG = sol.y[4, :] / 1000.  # Velocity loss due to gravity [km / s]
        m = sol.y[5, :]  # Vehicle mass [kg]
        print(gamma)

        """Delta-v computation"""

        def find_nearest(array, value):
            array = np.asarray(array)
            idx = (np.abs(array - value)).argmin()
            return array[idx]

        vG_bo = vG[np.where(t == find_nearest(t, t_burn))] * 1000  # Gravity loss computed until burnout
        delta_v_ascent = isp * g_0 * np.log(m_i / m[-1]) - vG_bo  # delta-v computed from the launch pad to the aposelene
        delta_v_circ = np.sqrt(mi_moon / (Rmoon + h[-1] * 1000)) - v[-1] * 1000  # delta-v computed from the aposelene suborbital trajectory to the corrispondent circular orbit
        m_f_actual = m[-1] * np.e ** (-delta_v_circ / isp / g_0)    # final mass relative to circularization maneuver

        # delta_v_trans=np.sqrt(mi_moon*(2./(17000+Rmoon)-1/(17000+2*Rmoon+83000)))-(delta_v_circ+v[-1] * 1000)
        # delta_v_recirc=np.sqrt(mi_moon / (Rmoon + 100000.))-np.sqrt(mi_moon*(2./(100000.+Rmoon)-1/(h[-1]*1000.+2*Rmoon+100000.)))
        #
        # print(f'deltav trans {delta_v_trans}')
        # print(f'deltav recirc {delta_v_recirc}')
        err = m_f_actual - m_f
        if err < 0:
            m_f_coast += -err
        else:
            m_f_coast += err

        i+=1

        if i==30:
            print('\nSomething went wrong. The iteration takes too long.')
            sys.exit()

        print(err, m_f_coast, m_f_actual)         # Changing final mass, the script fails because the t_burn > t_bo, and for some reason this affect the mass calculation (see the script without while loop)



    """PLOTS"""

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
    #
    return print(f"Delta-v needed for the ascent phase is {delta_v_ascent /1000 * u.km / u.s}.\n"
                             f"Delta-v needed for circularization in LLO of {h[-1] * u.km} is {delta_v_circ /1000 * u.km / u.s}.\n"
                             f"The total delta-v needed is {(delta_v_ascent + delta_v_circ) / 1000 * u.km / u.s}.\n"
                              f"The time needed to complete the ascent and circularization is {t[-1] * u.s}."), \
           # plt.show()

ascent(4700., 2400.)
plt.show()
