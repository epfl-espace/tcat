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
            warnings.warn('Target ', satellite.get_id(), ' already in constellation ', self.ID, '.', UserWarning)
        else:
            # Add new satellite to general list of satellites
            self.satellites[satellite.get_id()] = satellite

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
            temp_rotation = temp_rotation + np.sign(nodal_precession(satellite.get_default_orbit())[1].value)
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
        insertion_orbit = reference_satellite.get_insertion_orbit()
        operational_orbit = reference_satellite.get_operational_orbit()
        disposal_orbit = reference_satellite.get_disposal_orbit()

        temp_insertion_plane_orbit = None 
        temp_operational_plane_orbit = None
        temp_disposal_plane_orbit = None       
        
        # For each plane, create the reference orbits by raan offset and populate the plane
        for i in range(0, number_of_planes):
            # Set plane id
            temp_plane_id = constellation_name + '_plane' + '{:04d}'.format(i)
            
            # Create insertion orbit relative to the plane
            if(insertion_orbit is not None):
                temp_insertion_plane_orbit = Orbit.from_classical(Earth, insertion_orbit.a, insertion_orbit.ecc,
                                                                    insertion_orbit.inc, i * plane_distribution_angle * u.deg / number_of_planes,
                                                                    insertion_orbit.argp, 0. * u.deg,
                                                                    insertion_orbit.epoch)
            
            # Create operational orbit relative to the plane
            if(operational_orbit is not None):
                temp_operational_plane_orbit = Orbit.from_classical(Earth, operational_orbit.a + altitude_offset * (i-int((number_of_planes+1)/2)),
                                                                    operational_orbit.ecc,
                                                                    operational_orbit.inc,
                                                                    i * plane_distribution_angle * u.deg / number_of_planes,
                                                                    operational_orbit.argp, 0. * u.deg,
                                                                    operational_orbit.epoch)
            # Create graveyard orbit relative to the plane
            if(disposal_orbit is not None):
                temp_disposal_plane_orbit = Orbit.from_classical(Earth, disposal_orbit.a, disposal_orbit.ecc,
                                                                    disposal_orbit.inc, i * plane_distribution_angle * u.deg / number_of_planes,
                                                                    disposal_orbit.argp, 0. * u.deg,
                                                                    disposal_orbit.epoch)
            
            # Populate the plane with its own reference satellite
            self.populate_plane(temp_plane_id, reference_satellite, sat_per_plane, temp_insertion_plane_orbit,
                                temp_operational_plane_orbit,temp_disposal_plane_orbit)

    def populate_plane(self, plane_id, reference_satellite, sat_per_plane, insertion_orbit, operational_orbit, disposal_orbit):
        """ Adds satellites to form a complete plane with equiphased population based on inputs.

        Args:
            plane_id (str): plane id
            reference_satellite (ConstellationSatellites.Satellite): target that is duplicated to create constellation members
            sat_per_plane (int): number of satellites on each plane, equiphased along 360° of anomaly
            insertion_orbit (poliastro.twobody.Orbit): insertion orbit for the satellites
            operational_orbit (poliastro.twobody.Orbit): operational orbit for the plane, where the capture will occur
        """
        temp_insertion_orbit = None
        temp_operational_orbit = None
        temp_disposal_orbit = None

        # For each satellite in the plane, create the reference orbit by anomaly offset and add the target to clients
        for i in range(0, sat_per_plane):
            # Set target id
            temp_satellite_id = plane_id + '_sat' + '{:04d}'.format(i)
            
            # Create insertion orbit relative to the satellite ref
            if(insertion_orbit is not None):
                temp_insertion_orbit = Orbit.from_classical(Earth, insertion_orbit.a, insertion_orbit.ecc,
                                                            insertion_orbit.inc, insertion_orbit.raan,
                                                            insertion_orbit.argp, i * 360 * u.deg / sat_per_plane,
                                                            insertion_orbit.epoch)
            
            # Create operational orbit relative to the satellite ref
            if(operational_orbit is not None):
                temp_operational_orbit = Orbit.from_classical(Earth, operational_orbit.a, operational_orbit.ecc,
                                                            operational_orbit.inc, operational_orbit.raan,
                                                            operational_orbit.argp, i * 360 * u.deg / sat_per_plane,
                                                            operational_orbit.epoch)

            if(disposal_orbit is not None):
                temp_disposal_orbit = Orbit.from_classical(Earth, disposal_orbit.a, disposal_orbit.ecc,
                                                            disposal_orbit.inc, disposal_orbit.raan,
                                                            disposal_orbit.argp, i * 360 * u.deg / sat_per_plane,
                                                            disposal_orbit.epoch)
            
            # Make a copy of reference target to become new target
            temp_satellite = copy.deepcopy(reference_satellite)
            
            # Update new target and add it to clients
            temp_satellite.id = temp_satellite_id
            temp_satellite.insertion_orbit = temp_insertion_orbit
            temp_satellite.operational_orbit = temp_operational_orbit
            temp_satellite.disposal_orbit = temp_disposal_orbit
            temp_satellite.current_orbit = None
            temp_satellite.initial_orbit = None
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
                axes.plot(tgt.get_operational_orbit().raan.to(u.deg).value, tgt.get_operational_orbit().nu.to(u.deg).value, 'ok')
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
                axes.plot(tgt.get_operational_orbit().raan.to(u.deg).value,
                             (tgt.get_operational_orbit().a - tgt.get_operational_orbit().attractor.R).to(u.km).value, 'ok')
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
                fig.plot(target.get_operational_orbit())
            else:
                if save_folder and save:
                    fig.plot(target.get_operational_orbit()).write_image(file=save_folder + "/"+ save+".png", format="png", scale="2", engine="kaleido")
                else:
                    fig.plot(target.get_operational_orbit()).show(render_mode='webgl')

    def print_KPI(self):
        """ Print KPI related to the constellation"""
        # Total mass delivered into space
        satellites_masses = [self.satellites[key].get_dry_mass() for key in self.satellites.keys()]
        print(f"Total payload mass released in space: {sum(satellites_masses):.2f}")
    
    def __str__(self):
        temp = self.ID
        for _, target in self.satellites.items():
            temp = temp + '\n\t' + target.__str__()
        return temp
