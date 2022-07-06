from scipy.interpolate import griddata
from scipy.interpolate import interp2d
from scipy import interpolate
import numpy as np
import time
import astropy.units as u
from matplotlib import pyplot, animation
import logging

"""Input data"""

launch_pad = "ELA-4"


def get_supported_launchers():
    """This function holds all the supported launchers in one place.
    The data are stored with the following rationale:
    dictionary key : launcher name
    first element [0]: launch site
    second element [1]: minimum inclination (deg)
    third element [2]: fairing diameter in the cylindrical section (m)
    forth element [3]: fairing height in the cylindrical section (m)
    fifth element [4]: fairing total height (m)
     """
    supported_launchers = {"Ariane_64": ["Korou", 5, 4.570, 11.185, 18.000],
                           "Ariane_62": ["Korou", 5, 4.570, 11.185, 18.000],
                           "Soyuz": ["Baikonur", 45, 3.800, 5.070, 9.518],
                           "Soyuz_2.1a_Fregat": ["Baikonur", 45, 3.800, 5.070, 9.518],
                           "Soyuz_2.1b_Fregat": ["Baikonur", 45, 3.800, 5.070, 9.518],
                           }
    return supported_launchers


def get_launcher_fairing(launcher):
    """
        This function extracts data from the "Launchers" folder and select the correct file.

        Args:
            launcher: Name of the launcher (Ariane_64, Ariane_62)

        Returns:
            volume_available:
        """
    supported_launchers = get_supported_launchers()

    if launcher in supported_launchers.keys():

        fairing_diameter = supported_launchers[launcher][2] * u.m
        fairing_cylinder_height = supported_launchers[launcher][3] * u.m
        fairing_total_height = supported_launchers[launcher][4] * u.m

        cylinder_volume = np.pi * (fairing_diameter / 2) ** 2 * fairing_cylinder_height
        cone_volume = np.pi * (fairing_diameter / 2) ** 2 * (fairing_total_height - fairing_cylinder_height)

        volume_available = (cylinder_volume + cone_volume).to(u.m ** 3)
        return volume_available
    else:
        raise ValueError(f"The launcher {launcher} is not valid.")


def get_launcher_data(launcher, launch_site, orbit_type):
    """
    This function extracts data from the "Launchers" folder and select the correct file.

    Args:
        launcher: Name of the launcher (Ariane_64, Ariane_62)
        launch_site: Name of the lunch site (Korou)
        orbit_type: Orbit type (LEO, SSO, LPEO, Polar, MTO, GTO, GTO+)

    Returns:
        launcher_data: Data from the .csv files. It can be in the form of [Perigee (km), Apogee (km),
                       Performance (kg)] or [Altitude (km), Inclination (deg), Performance (kg)]
        min_inc: minimum inclination available in the current dataset
    """
    supported_launchers = get_supported_launchers()

    if launcher in supported_launchers.keys():
        min_inc = supported_launchers[launcher][1]
    else:
        raise ValueError(f"The launcher {launcher} is not valid.")

    if supported_launchers[launcher][0] != launch_site:
        raise ValueError(
            f"The launch site {launch_site} is not valid for {launcher}. The only available launch site is {supported_launchers[launcher][0]}")

    elif orbit_type in ["LEO", "SSO", "LPEO", "Polar"]:
        launcher_data = np.genfromtxt(f'Launchers/{launcher}_LEO.csv', delimiter=";", skip_header=2)
        return launcher_data, min_inc

    elif orbit_type == "MTO":
        launcher_data = np.genfromtxt(f'Launchers/{launcher}_MTO.csv', delimiter=";", skip_header=2)
        return launcher_data, min_inc
    elif orbit_type in ["GTO", "GTO+"]:
        launcher_data = np.genfromtxt(f'Launchers/{launcher}_GTO.csv', delimiter=";", skip_header=2)
        return launcher_data, min_inc
    else:
        raise ValueError(f"The orbit type {orbit_type} is not valid.")


def get_launcher_performance(fleet, launcher, launch_site, inclination, apogee, perigee, orbit_type, method="linear",
                             verbose=False, save=None, save_folder=None):
    """
    This function directly take the queried data from the Launchers database in order to return the performance of
    the launcher for several combination of orbit's apogee, perigee and inclination. If the data queried do not match
    the ones in the database, the interpolation is performed

    Args:
        launcher: Name of the launcher (Ariane_64, Ariane_62)
        launch_site: Name of the lunch site (Korou)
        apogee: Apogee of the final orbit
        inclination: Inclination of the final orbit
        method: interpolation method ('linear', 'nearest', 'cubic', 'nearest-up', 'zero',
                              'slinear', 'quadratic', 'previous', 'next')
        verbose: set to True to plot the interpolated dataset

    Returns:
        l_performance: Launcher's performance in kg
    """
    launcher_data, min_inc = get_launcher_data(launcher, launch_site, orbit_type)

    # First check on consistency of the inputs
    if float(inclination) < min_inc:
        UserWarning(f"{launch_site} launch site's latitude is {min_inc}°, your target orbit is {inclination}°. An "
                    f"inclination change maneuvre needs to be performed.")

    # Check if the data is already present in the database, for circular orbits only
    elif perigee == apogee and apogee in launcher_data[:, 0] and inclination in launcher_data[:, 1]:
        try:
            i = np.where((launcher_data[:, 0] == apogee) & (launcher_data[:, 1] == inclination))
            l_performance = launcher_data[i, 2][0][0] * u.kg
        # If data are not found in the database, the code proceed with interpolation
        except IndexError:
            l_performance = interpolate_launcher_data(fleet, launcher_data, apogee, inclination, method, verbose, save=save, save_folder=save_folder)
        return l_performance
    elif perigee == apogee:
        l_performance = interpolate_launcher_data(fleet, launcher_data, apogee, inclination, method, verbose, save=save, save_folder=save_folder)
        return l_performance

    elif inclination != 6:
        raise ValueError("MTO and GTO inclination is 6 deg only. Please consider changing the inclination.")

    # Check if the data is already present in the database, for elliptical transfer orbits only
    elif perigee in launcher_data[:, 0] and apogee in launcher_data[:, 1]:
        try:
            i = np.where((launcher_data[:, 0] == perigee) & (launcher_data[:, 1] == apogee))
            l_performance = launcher_data[i, 2][0][0] * u.kg
        # If data are not found in the database, the code proceed with interpolation
        except IndexError:
            l_performance = interpolate_launcher_data(fleet, launcher_data, apogee, perigee, method, verbose, save=save, save_folder=save_folder)
        return l_performance
    else:
        l_performance = interpolate_launcher_data(fleet, launcher_data, perigee, apogee, method, verbose, save=save, save_folder=save_folder)
        return l_performance.to(u.kg)


def interpolate_launcher_data(fleet, launcher_data, param_one, param_two, interpolation_method, verbose=False, save=None, save_folder=None, create_gif=True):
    """
    This function interpolates the performance data of the launcher and returns the performance of
    the launcher for several combination of orbit's apogee, perigee and inclination.
    Args:
        launcher_data:
        param_one: first parameter for interpolation. Can be either altitude or perigee
        param_two: second parameter for interpolation. Can be either inclination or apogee
        interpolation_method: interopolation method ('linear', 'nearest', 'cubic', 'nearest-up', 'zero',
                              'slinear', 'quadratic', 'previous', 'next')
        verbose: set to True to plot the interpolated dataset

    Returns:
        l_performance: Launcher's performance in kg
    """
    # plot interpolated dataset
    if verbose:
        logging.info(f"Plotting interpolated databases for selected Launch Vehicle...") #TODO: put the LV actual name
        try:
            xx = launcher_data[:, 0]
            yy = launcher_data[:, 1]
            xx, yy = np.meshgrid(xx, yy)
            z = interpolate.griddata(launcher_data[:, 0:2], launcher_data[:, 2], (xx.ravel(), yy.ravel()),
                                     method=interpolation_method)
            fig = pyplot.figure("Performance map")
            ax = fig.add_subplot(111, projection='3d')
            ax.set_title("Performance map")

            if param_two < 180:
                ax.set_xlabel("Altitude [km]")
                ax.set_ylabel("Inclination [deg]")
            else:
                ax.set_xlabel("Perigee [km]")
                ax.set_ylabel("Apogee [km]")

            ax.set_zlabel("Performance [kg]")
            ax.plot_trisurf(xx.ravel(), yy.ravel(), z)
            ax.scatter(launcher_data[:, 0], launcher_data[:, 1], launcher_data[:, 2], s=20, c="red")

        except RuntimeError:
            xx = np.linspace(np.min(launcher_data[:, 1]), np.max(launcher_data[:, 1]), num=25)
            z = interpolate.interp1d(launcher_data[:, 1], launcher_data[:, 2], kind=interpolation_method,
                                     fill_value="extrapolate")
            # z = np.polyfit(launcher_data[:, 1], launcher_data[:, 2], 1)
            # f = np.poly1d(z)
            fig = pyplot.figure("Performance map")
            xnew = np.linspace(np.min(launcher_data[:, 1]) * 0.8, np.max(launcher_data[:, 1]) * 1.1, num=27)
            ynew = z(xnew)  # use interpolation function returned by `interp1d`
            ax = fig.add_subplot(111)
            ax.set_title("Performance map")
            ax.plot(launcher_data[:, 1], launcher_data[:, 2], "o", xnew, ynew, '-')
            ax.set_xlabel("Apogee [km]")
            ax.set_ylabel("Performance [kg]")

        if not fleet.get_graph_status():
            if save_folder and save:

                fig.savefig(os.path.join(save_folder, save, '.png'), bbox_inches='tight', dpi=100, engine="kaleido")

                if create_gif:
                    def rotate(angle):
                        ax.view_init(azim=angle)

                    logging.info("Making animation...")
                    rot_animation = animation.FuncAnimation(fig, rotate, frames=np.arange(0, 359, 5), interval=150)
                    rot_animation.save(save_folder + '/' + save + '.gif', dpi=100, bitrate=1)
                    fleet.set_graph_status(True)

                logging.info("Interpolating...")
            else:
                print("Close the window to continue.")
                pyplot.show()
                print("Interpolating...")
    try:
        l_performance = \
        griddata(launcher_data[:, 0:2], launcher_data[:, 2], [param_one, param_two], method=interpolation_method)[
            0] * u.kg
        if np.isnan(l_performance):
            raise ValueError(f"The orbital parameters inserted exceed the dataset.\n"
                             f"Dataset min/max are:\n"
                             f"{np.min(launcher_data[:, 0])} / {np.max(launcher_data[:, 0])} for 1st parameter\n"
                             f"{np.min(launcher_data[:, 1])} / {np.max(launcher_data[:, 1])} for 2nd parameter\n"
                             f"your 1st and 2nd parameter are {param_one} and {param_two}.")
    except RuntimeError:

        z = interpolate.interp1d(launcher_data[:, 1], launcher_data[:, 2], kind=interpolation_method,
                                 fill_value="extrapolate")
        l_performance = z(param_two) * u.kg

    return l_performance

# print(get_launcher_performance(launcher, launch_site, inclination, apogee, perigee, method=method, verbose=True))
#    tic = time.perf_counter()
# toc = time.perf_counter()
#   print(f"Numpy reading elapsed {toc - tic:0.5f} seconds")
#
