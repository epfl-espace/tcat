import copy
import random

import matplotlib.pyplot as plt
import numpy as np
from astropy import units as u
from poliastro.bodies import Earth
from poliastro.twobody import Orbit

from Phases.Common_functions import nodal_precession


class ADRClients:
    """ ADR Clients consist of a dictionary of potential targets for servicers to remove from orbit.
    The class is initialized with an emtpy dictionary of potential targets.

    Note:
        This class contains methods for automatic creation of constellations.
        This class could be expended to interface with a market analysis module in the future.

    Args:
        clients_id (str): Standard id. Needs to be unique.

    Attributes:
        ID (str): Standard id. Needs to be unique.
        targets (dict): Dictionary of targets that are potential recipients for servicing.
    """

    def __init__(self, clients_id):
        self.ID = clients_id
        self.targets = dict()

    def add_target(self, target):
        """ Adds a target to the Clients class.

        Args:
            target (Target): target to be added
        """
        if target in self.targets:
            warnings.warn('Target ', target.id, ' already in client ', self.id, '.', UserWarning)
        else:
            self.targets[target.ID] = target

    def reset(self):
        """ Calls the reset function for each target.
        This function is used to reset the mass and orbits of targets after a simulation.
        This does not reset the failure state of the satellite.
        """
        for _, target in self.targets.items():
            target.reset()

    def get_failed_satellites(self):
        """ Return dictionary of clients satellites that have a failed state.

        Return:
            (dict(Target)): dictionary containing all failed satellites
        """
        failed_satellites = {}
        for tgt_ID, tgt in self.targets.items():
            if tgt.state == 'failed':
                failed_satellites[tgt_ID] = tgt
        return failed_satellites

    def populate_constellation(self, constellation_id, reference_target, number_of_planes=12, sat_per_plane=43):
        """ Adds targets to form a complete constellation with equiphased planes based on inputs.
        The reference target is duplicated to fill the planes.

        Args:
            constellation_id (str): reference id for the constellation
            reference_target (Target): target that is duplicated to create constellation members
            number_of_planes (int): number of planes for the constellation, equiphased along 180° of raan
            sat_per_plane (int): number of satellites on each plane, equiphased along 360° of anomaly
        """
        # retrieve reference orbits from reference target
        insertion_orbit = reference_target.insertion_orbit
        operational_orbit = reference_target.operational_orbit
        disposal_orbit = reference_target.disposal_orbit
        # for each plane, create the reference orbits by raan offset and populate the plane
        for i in range(0, number_of_planes):
            temp_plane_id = constellation_id + '_plane' + '{:04d}'.format(i)
            temp_insertion_plane_orbit = Orbit.from_classical(Earth, insertion_orbit.a, insertion_orbit.ecc,
                                                              insertion_orbit.inc, i * 180 * u.deg / number_of_planes,
                                                              insertion_orbit.argp, 0. * u.deg,
                                                              insertion_orbit.epoch)
            temp_operational_plane_orbit = Orbit.from_classical(Earth, operational_orbit.a + 4 * u.km * i,
                                                                operational_orbit.ecc,
                                                                operational_orbit.inc,
                                                                i * 180 * u.deg / number_of_planes,
                                                                operational_orbit.argp, 0. * u.deg,
                                                                operational_orbit.epoch)
            temp_disposal_plane_orbit = Orbit.from_classical(Earth, disposal_orbit.a, disposal_orbit.ecc,
                                                             disposal_orbit.inc, i * 180 * u.deg / number_of_planes,
                                                             disposal_orbit.argp, 0. * u.deg,
                                                             disposal_orbit.epoch)
            self.populate_plane(temp_plane_id, reference_target, sat_per_plane, temp_insertion_plane_orbit,
                                temp_operational_plane_orbit, temp_disposal_plane_orbit)

    def populate_plane(self, plane_id, reference_target, sat_per_plane, insertion_orbit, operational_orbit,
                       disposal_orbit):
        """ Adds targets to form a complete plane with equiphased population based on inputs.
        Args:
            plane_id (str): plane id
            reference_target (Target): target that is duplicated to create constellation members
            sat_per_plane (int): number of satellites on each plane, equiphased along 360° of anomaly
            insertion_orbit (poliastro.twobody.Orbit): insertion orbit for the satellites
            operational_orbit (poliastro.twobody.Orbit): operational orbit for the plane, where the capture will occur
            disposal_orbit (poliastro.twobody.Orbit): disposal orbit for the plane, where the servicer will release
                                                      the target in case of servicing
        """
        # for each sat in the plane, create the reference orbit by anomaly offset and add the target to clients
        for i in range(0, sat_per_plane):
            temp_tgt_id = plane_id + '_sat' + '{:04d}'.format(i)
            temp_insertion_orbit = Orbit.from_classical(Earth, insertion_orbit.a, insertion_orbit.ecc,
                                                        insertion_orbit.inc, insertion_orbit.raan,
                                                        insertion_orbit.argp, i * 360 * u.deg / sat_per_plane,
                                                        insertion_orbit.epoch)
            temp_operational_orbit = Orbit.from_classical(Earth, operational_orbit.a, operational_orbit.ecc,
                                                          operational_orbit.inc, operational_orbit.raan,
                                                          operational_orbit.argp, i * 360 * u.deg / sat_per_plane,
                                                          operational_orbit.epoch)
            temp_disposal_orbit = Orbit.from_classical(Earth, disposal_orbit.a, disposal_orbit.ecc,
                                                       disposal_orbit.inc, disposal_orbit.raan,
                                                       disposal_orbit.argp, i * 360 * u.deg / sat_per_plane,
                                                       disposal_orbit.epoch)
            # make a copy of reference target to become new target
            temp_tgt = copy.deepcopy(reference_target)
            # update new target and add it to clients
            temp_tgt.ID = temp_tgt_id
            temp_tgt.insertion_orbit = temp_insertion_orbit
            temp_tgt.operational_orbit = temp_operational_orbit
            temp_tgt.disposal_orbit = temp_disposal_orbit
            temp_tgt.current_orbit = temp_operational_orbit
            temp_tgt.initial_orbit = temp_operational_orbit
            self.add_target(temp_tgt)

    def randomly_fail_satellites(self, reliability=0.99, verbose=False):
        """ Randomly set some targets as failed based on reliability. This includes putting some satellites
        in transition orbits to represent failure during orbit raising or lowering.

        Args:
            reliability (float): (optional) satellite reliability at end of life
            verbose (bool): if True, print failed satellites
        """
        tgt = ["OneWeb_plane0000_sat0016",
               "OneWeb_plane0001_sat0032",
               'OneWeb_plane0002_sat0004',
               'OneWeb_plane0003_sat0031',
               'OneWeb_plane0004_sat0009',

               'OneWeb_plane0005_sat0011',
               'OneWeb_plane0005_sat0019',
               'OneWeb_plane0005_sat0023',
               'OneWeb_plane0006_sat0042',
               'OneWeb_plane0007_sat0000',
               'OneWeb_plane0007_sat0012',
               'OneWeb_plane0009_sat0016',
               'OneWeb_plane0009_sat0022',
               'OneWeb_plane0009_sat0023',
               'OneWeb_plane0009_sat0033',
               'OneWeb_plane0009_sat0043',
               'OneWeb_plane0009_sat0048',
               'OneWeb_plane0010_sat0014',
               'OneWeb_plane0011_sat0029',
               'OneWeb_plane0011_sat0036',
               'OneWeb_plane0011_sat0043']
        for _, target in self.targets.items():
            if target.ID in tgt:
                target.state = 'failed'
            # if verbose and target.state == 'failed':
            #     print(target)


        # # for each target, generate a random number, if it's above reliability, fail the satellite
        # for _, tgt in self.targets.items():
        #     random_gen_failed = random.randint(1, 100)
        #     if random_gen_failed >= reliability * 100:
        #         tgt.state = 'failed'
        #     if verbose and tgt.state == 'failed':
        #         print(tgt)

    def get_global_precession_rotation(self):
        """ Return global nodal precession direction of the client failed satellites.
        If more targets rotate clockwise, return -1, otherwise returns 1

        Return:
            (int): 1 if counter clockwise, -1 if clockwise (right hand convention)
        """
        temp_rotation = 1
        for _, sat in self.get_failed_satellites().items():
            temp_rotation = temp_rotation + np.sign(nodal_precession(sat.operational_orbit)[1].value)
        return int(np.sign(temp_rotation))

    def plot_distribution(self, save=None, save_folder=None):
        """ Plot the distribution of the constellation.

        Args:
            save (str): if given, the plot will be saved under that name
            save_folder (str): if given and save is true, the plot will be saved in the specified folder
        """
        fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(10, 5))
        for _, tgt in self.targets.items():
            if tgt.state == 'failed':
                axes[0].plot(tgt.initial_orbit.raan.to(u.deg).value, tgt.initial_orbit.nu.to(u.deg).value, 'ok')
        axes[0].set_xlabel('raan spacing [°]')
        axes[0].set_ylabel('anomaly spacing [°]')

        for _, tgt in self.targets.items():
            if tgt.state == 'failed':
                axes[1].plot(tgt.initial_orbit.raan.to(u.deg).value,
                             (tgt.initial_orbit.a - tgt.initial_orbit.attractor.R).to(u.km).value, 'ok')
        axes[1].set_xlabel('raan spacing [°]')
        axes[1].set_ylabel('altitude [km]')

        axes[0].grid(True, which='major')
        axes[0].minorticks_on()
        axes[0].grid(True, which='minor', linestyle=':', linewidth='0.5')
        axes[1].grid(True, which='major')
        axes[1].minorticks_on()
        axes[1].grid(True, which='minor', linestyle=':', linewidth='0.5')

        plt.subplots_adjust(left=0.1, bottom=0.15, right=0.95, top=0.9, wspace=0.4)

        plt.show()
        if save:
            if save_folder:
                fig.savefig(save_folder + '/' + save + '.png', bbox_inches='tight')
            else:
                fig.savefig(save + '.png', bbox_inches='tight')

    def __str__(self):
        temp = self.ID
        for _, target in self.targets.items():
            temp = temp + '\n\t' + target.__str__()
        return temp


class Target:
    """ Target consist of an object in an initial orbit that can be moved by servicers.
    The class is initialized by giving the current object mass and orbit at time 0.
    It is added to the Clients class taken as argument during initialization.

    Args:
        target_id (str): Standard id. Needs to be unique.
        initial_mass (u.kg): Object mass at time 0.
        insertion_orbit (poliastro.twobody.Orbit): Object orbit after insertion
        operational_orbit (poliastro.twobody.Orbit): Object orbit after orbit raising
        disposal_orbit (poliastro.twobody.Orbit): Object orbit after post servicer_group disposal
        state (str): descriptor of the satellite state, used to identify different possible failures and states

    Attributes:
        ID (str): Standard id. Needs to be unique.
        initial_mass (u.kg): Object mass at time 0.
        initial_orbit (poliastro.twobody.Orbit): Initial orbit of the satellite
        insertion_orbit (poliastro.twobody.Orbit): Object orbit after insertion
        operational_orbit (poliastro.twobody.Orbit): Object orbit after orbit raising
        disposal_orbit (poliastro.twobody.Orbit): Object orbit after post servicer_group disposal
        current_orbit (poliastro.twobody.Orbit): Object orbit at current time.
        current_mass (u.kg): Object mass at current time.
        state (str): descriptor of the satellite state, used to identify different possible failures and states
    """

    def __init__(self, target_id, initial_mass, insertion_orbit, operational_orbit, disposal_orbit, state='nominal'):
        self.ID = target_id
        self.initial_mass = initial_mass
        self.initial_orbit = operational_orbit
        self.insertion_orbit = insertion_orbit
        self.operational_orbit = operational_orbit
        self.disposal_orbit = disposal_orbit
        self.current_orbit = operational_orbit
        self.current_mass = initial_mass
        self.state = state

    def get_current_mass(self):
        """ Get the current target mass.

        Returns:
            (u.kg): current mass
        """
        return self.current_mass

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
        if not other_object_orbit:
            other_object_orbit = self.disposal_orbit
        _, own_nodal_precession_speed = nodal_precession(own_orbit)
        _, other_nodal_precession_speed = nodal_precession(other_object_orbit)
        delta_nodal_precession_speed = own_nodal_precession_speed - other_nodal_precession_speed
        return (delta_nodal_precession_speed * duration).decompose()

    def reset(self):
        """ Reset the current target orbit and mass to the parameters given during initialization.
        This function is used to reset the state and orbits of the target after a simulation.
        """
        self.current_mass = self.initial_mass
        self.current_orbit = self.initial_orbit

    def __str__(self):
        return self.ID
