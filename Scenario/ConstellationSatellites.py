"""
Created:        ?
Last Revision:  23.05.2022
Author:         ?,Emilien Mingard
Description:    Constellation,Satellite Classes definitions
"""
# Import Classes
from Phases.Common_functions import nodal_precession

# Import libraries
import copy
import matplotlib.pyplot as plt
import numpy as np
from astropy import units as u
from poliastro.bodies import Earth
from poliastro.twobody import Orbit
from poliastro.plotting import OrbitPlotter3D
import warnings
warnings.filterwarnings("error")

class Constellation:
    """ Constellation consists of a dictionary of potential satellites for launch servicers to place into orbit.
        The class is initialized with an empty dictionary of potential satellites.
    """

    """
    Init
    """
    def __init__(self, constellation_id):
        # Set id
        self.ID = constellation_id

        # Instanciate dictionnary containing all satellites
        self.satellites = dict()

    """
    Methods
    """
    def add_satellite(self, satellite):
        """ Adds a satellite to the Constellation class.

        Args:
            Satellite: to be added
        """
        
        # Check if satellite already in dict
        if satellite in self.satellites:
            warnings.warn('Target ', satellite.ID, ' already in constellation ', self.ID, '.', UserWarning)
        else:
            # Add new satellite to general list of satellites
            self.satellites[satellite.ID] = satellite

    def set_optimized_ordered_satellites(self,list_of_satellites):
        """ Set list of ordered satellites to be released.
        """
        self.optimized_ordered_satellites = list_of_satellites

    def get_optimized_ordered_satellites(self):
        """ Set list of ordered satellites to be released.

        Return:
            (List(Satellite)): List containing optimized ordered satellites left
        """
        return self.optimized_ordered_satellites

    def remove_in_ordered_satellites(self,satellites):
        """ Remove already assigned satellites
        """
        for satellite in satellites:
            self.optimized_ordered_satellites.remove(satellite)

    def get_standby_satellites(self):
        """ Return dictionary of satellites that have a standby state.

        Return:
            (dict(Satellite)): dictionary containing all standby satellites
        """
        standby_satellites = {}
        for satellite_ID, satellite in self.satellites.items():
            if satellite.state == 'standby':
                standby_satellites[satellite_ID] = satellite
        return standby_satellites

    def get_number_satellites(self):
        """ Compute and return number of satellites

        Return:
            (int): number of satellites
        """
        return len(self.satellites.keys())

    def get_global_precession_rotation(self):
        """ Return global nodal precession direction of the client failed satellites.
        If more targets rotate clockwise, return -1, otherwise returns 1

        Return:
            (int): 1 if counter clockwise, -1 if clockwise (right hand convention)
        """
        temp_rotation = 0
        for _, satellite in self.get_standby_satellites().items():
            temp_rotation = temp_rotation + np.sign(nodal_precession(satellite.operational_orbit)[1].value)
        return int(np.sign(temp_rotation))

    def reset(self):
        """ Calls the reset function for each satellite.
            This function is used to reset the mass and orbits of targets after a simulation.
        """
        for _, satellite in self.satellites.items():
            satellite.reset()

    def populate_standard_constellation(self, constellation_name, reference_satellite, number_of_planes=2, sat_per_plane=10, plane_distribution_angle=180, altitude_offset = 10*u.km):
        """ Adds satellites to form a complete constellation with equi-phased planes based on inputs.
            The reference satellite is duplicated to fill the planes.

        Args:
            plane_distribution_angle (int): Angle over which to distribute the RAAN of the orbital planes. Generally
                                            180° for constellations composed of polar orbits and 360° for the others.
            constellation_name (str): constellation name as provided by input json
            reference_satellite (ConstellationSatellites.Satellite): target that is duplicated to create constellation members
            number_of_planes (int): number of planes for the constellation, equiphased along 180° of raan
            altitude_offset (u.km): ?
            sat_per_plane (int): number of satellites on each plane, equiphased along 360° of anomaly
        """
        # Add reference_satellite as attribut
        self.reference_satellite = reference_satellite
        
        # Extract reference satellite orbits
        insertion_orbit = reference_satellite.insertion_orbit
        operational_orbit = reference_satellite.operational_orbit
        
        # For each plane, create the reference orbits by raan offset and populate the plane
        for i in range(0, number_of_planes):
            # Set plane id
            temp_plane_id = constellation_name + '_plane' + '{:04d}'.format(i)
            
            # Create insertion orbit relative to the plane
            temp_insertion_plane_orbit = Orbit.from_classical(Earth, insertion_orbit.a, insertion_orbit.ecc,
                                                              insertion_orbit.inc, i * plane_distribution_angle * u.deg / number_of_planes,
                                                              insertion_orbit.argp, 0. * u.deg,
                                                              insertion_orbit.epoch)
            
            # Create operational orbit relative to the plane
            temp_operational_plane_orbit = Orbit.from_classical(Earth, operational_orbit.a + altitude_offset * (i-int((number_of_planes+1)/2)),
                                                                operational_orbit.ecc,
                                                                operational_orbit.inc,
                                                                i * plane_distribution_angle * u.deg / number_of_planes,
                                                                operational_orbit.argp, 0. * u.deg,
                                                                operational_orbit.epoch)
            
            
            # Populate the plane with its own reference satellite
            self.populate_plane(temp_plane_id, reference_satellite, sat_per_plane, temp_insertion_plane_orbit,
                                temp_operational_plane_orbit,)

    def populate_plane(self, plane_id, reference_satellite, sat_per_plane, insertion_orbit, operational_orbit):
        """ Adds satellites to form a complete plane with equiphased population based on inputs.

        Args:
            plane_id (str): plane id
            reference_satellite (ConstellationSatellites.Satellite): target that is duplicated to create constellation members
            sat_per_plane (int): number of satellites on each plane, equiphased along 360° of anomaly
            insertion_orbit (poliastro.twobody.Orbit): insertion orbit for the satellites
            operational_orbit (poliastro.twobody.Orbit): operational orbit for the plane, where the capture will occur
        """
        # For each satellite in the plane, create the reference orbit by anomaly offset and add the target to clients
        for i in range(0, sat_per_plane):
            # Set target id
            temp_satellite_id = plane_id + '_sat' + '{:04d}'.format(i)
            
            # Create insertion orbit relative to the satellite ref
            temp_insertion_orbit = Orbit.from_classical(Earth, insertion_orbit.a, insertion_orbit.ecc,
                                                        insertion_orbit.inc, insertion_orbit.raan,
                                                        insertion_orbit.argp, i * 360 * u.deg / sat_per_plane,
                                                        insertion_orbit.epoch)
            
            # Create operational orbit relative to the satellite ref
            temp_operational_orbit = Orbit.from_classical(Earth, operational_orbit.a, operational_orbit.ecc,
                                                          operational_orbit.inc, operational_orbit.raan,
                                                          operational_orbit.argp, i * 360 * u.deg / sat_per_plane,
                                                          operational_orbit.epoch)
            
            # Make a copy of reference target to become new target
            temp_satellite = copy.deepcopy(reference_satellite)
            
            # Update new target and add it to clients
            temp_satellite.ID = temp_satellite_id
            temp_satellite.insertion_orbit = temp_insertion_orbit
            temp_satellite.operational_orbit = temp_operational_orbit
            temp_satellite.current_orbit = None
            temp_satellite.initial_orbit = temp_insertion_orbit
            self.add_satellite(temp_satellite)

    def plot_distribution(self, save=None, save_folder=None):
        """ Plot the distribution of the constellation. If a save location is provided, the plot is directly saved,
            otherwise it is displayed.

        Args:
            save (str): if given, the plot will be saved under that name
            save_folder (str): if given and save is true, the plot will be saved in the specified folder
        """
        fig, axes = plt.subplots(nrows=1, ncols=1, figsize=(10, 5))
        for _, tgt in self.satellites.items():
            if tgt.state == 'standby':
                axes.plot(tgt.operational_orbit.raan.to(u.deg).value, tgt.operational_orbit.nu.to(u.deg).value, 'ok')
        axes.set_xlabel('raan spacing [°]')
        axes.set_ylabel('anomaly spacing [°]')

        axes.grid(True, which='major')
        axes.minorticks_on()
        axes.grid(True, which='minor', linestyle=':', linewidth='0.5')

        if save:
            if save_folder:
                fig.savefig(save_folder + '/' + save + 'RAAN_anomaly.png', bbox_inches='tight', dpi=100, engine="kaleido")
            else:
                fig.savefig(save + '.png', bbox_inches='tight', dpi=100)
        else:
            plt.show()
        fig, axes = plt.subplots(nrows=1, ncols=1, figsize=(10, 5))
        for _, tgt in self.satellites.items():
            if tgt.state == 'standby':
                axes.plot(tgt.operational_orbit.raan.to(u.deg).value,
                             (tgt.operational_orbit.a - tgt.operational_orbit.attractor.R).to(u.km).value, 'ok')
        axes.set_xlabel('raan spacing [°]')
        axes.set_ylabel('altitude [km]')

        axes.grid(True, which='major')
        axes.minorticks_on()
        axes.grid(True, which='minor', linestyle=':', linewidth='0.5')

        plt.subplots_adjust(left=0.1, bottom=0.15, right=0.95, top=0.9, wspace=0.4)

        if save:
            if save_folder:
                fig.savefig(save_folder + '/' + save + 'RAAN_altitude.png', bbox_inches='tight', dpi=100, engine="kaleido")
            else:
                fig.savefig(save + '.png', bbox_inches='tight', dpi=100)
        else:
            plt.show()

    def plot_3D_distribution(self, save=None, save_folder=None):
        """ Plot the distribution of the constellation in 3D graph. If a save location is provided, the plot is directly
            saved, otherwise it is displayed.

        Args:
            save (str): if given, the plot will be saved under that name
            save_folder (str): if given and save is true, the plot will be saved in the specified folder
        """

        fig = OrbitPlotter3D(num_points=15)

        i = 0
        for _, target in self.satellites.items():
            i += 1
            if i < len(self.satellites):
                fig.plot(target.operational_orbit)
            else:
                if save_folder and save:
                    fig.plot(target.operational_orbit).write_image(file=save_folder + "/"+ save+".png", format="png", scale="2", engine="kaleido")
                else:
                    fig.plot(target.operational_orbit).show(render_mode='webgl')

    def print_KPI(self):
        """ Print KPI related to the constellation"""
        # Total mass delivered into space
        satellites_masses = [self.satellites[key].initial_mass for key in self.satellites.keys()]
        print(f"Total payload mass released in space: {sum(satellites_masses):.2f}")
    
    def __str__(self):
        temp = self.ID
        for _, target in self.satellites.items():
            temp = temp + '\n\t' + target.__str__()
        return temp



class Satellite:
    """ Satellite consist of an object in an initial orbit that can be moved by servicers.
    The class is initialized by giving the current object mass and orbit at time 0.
    It is added to the Clients class taken as argument during initialization.

    Args:
        satellite_id (str): Standard id. Needs to be unique.
        initial_mass (u.kg): Object mass at time 0.
        insertion_orbit (poliastro.twobody.Orbit): Object orbit after insertion
        operational_orbit (poliastro.twobody.Orbit): Object orbit after orbit raising
        state (str): descriptor of the satellite state, used to identify different possible failures and states

    Attributes:
        ID (str): Standard id. Needs to be unique.
        initial_mass (u.kg): Object mass at time 0.
        volume (u.m^3): Volume of the satellite
        initial_orbit (poliastro.twobody.Orbit): Initial orbit of the satellite
        insertion_orbit (poliastro.twobody.Orbit): Object orbit after insertion
        operational_orbit (poliastro.twobody.Orbit): Object orbit after orbit raising
        current_orbit (poliastro.twobody.Orbit): Object orbit at current time.
        current_mass (u.kg): Object mass at current time.
        state (str): descriptor of the satellite state, used to identify different possible failures and states
    """

    def __init__(self, satellite_id, initial_mass, volume, insertion_orbit, operational_orbit, state, is_stackable=False):
        self.ID = satellite_id
        self.initial_mass = initial_mass
        self.volume = volume
        self.insertion_orbit = insertion_orbit
        self.initial_orbit = insertion_orbit
        self.operational_orbit = operational_orbit
        self.current_orbit = None
        self.current_mass = initial_mass
        self.state = state
        self.mothership = None

    def get_current_mass(self):
        """ Get the current satellite mass.

        Returns:
            (u.kg): current mass
        """
        return self.current_mass

    def get_volume(self):
        """ Get the satellite volume.

        Returns:
             (u.m**3): volume
        """
        return self.volume

    def get_initial_mass(self):
        """ Get the initial satellite mass.

        Returns:
            (u.kg): initial mass
        """
        return self.initial_mass

    def get_current_orbit(self):
        """ Get the current orbit

        Returns:
            (poliastro.twobody.Orbit): current orbit
        """
        return self.current_orbit

    def get_relative_raan_drift(self, duration, own_orbit=None, other_object_orbit=None):
        """ Returns the relative raan drift between the target and an hypothetical servicer.
            Used for planning purposes, to make sure phasing is feasible with current raan.

        Args:
            duration (u.<time unit>): duration after which to compute relative raan drift
            own_orbit (poliastro.twobody.Orbit): orbit of the target,
                                                 by default the target operational orbit
            other_object_orbit (poliastro.twobody.Orbit): orbit of the other object,
                                                          by default the target insertion orbit
        Return:
            (u.deg): relative raan drift after duration from current orbits
        """
        if not own_orbit:
            own_orbit = self.operational_orbit
        _, own_nodal_precession_speed = nodal_precession(own_orbit)
        _, other_nodal_precession_speed = nodal_precession(other_object_orbit)
        delta_nodal_precession_speed = own_nodal_precession_speed - other_nodal_precession_speed
        return (delta_nodal_precession_speed * duration).decompose()

    def reset(self):
        """ Reset the current satellite orbit and mass to the parameters given during initialization.
            This function is used to reset the state and orbits of the target after a simulation.
        """
        self.current_mass = self.initial_mass
        self.current_orbit = self.initial_orbit
        self.state = "standby"

    def __str__(self):
        return self.ID