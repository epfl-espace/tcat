# Created:          23.06.2022
# Last Revision:    30.06.2022
# Authors:          Emilien Mingard, Malo Goury du Roslan
# Emails:           emilien.mingard@tcdc.ch, malo.goury@tcdc.ch
# Description:      Base class of the Spacecrafts classes

# Import methods
from Modules.StructureModule import StructureModule
from Phases.Common_functions import nodal_precession

# Import libraries
from astropy import units as u
import warnings

from Scenarios.ScenarioParameters import *

# Class definition
class Spacecraft:
    """ Spacecraft acts ase a base Class implementing all necessary attributes relative to any spacecraft

    :param spacecraft_id: Spacecraft identification name
    :type spacecraft_id: str
    :param dry_mass: Spacecraft dry mass
    :type dry_mass: u*kg
    :param volume: Spacecraft volume
    :type volume: u*m**3
    :param insertion_orbit: Insertion orbit
    :type insertion_orbit: poliastro.twobody.Orbit
    :param operational_orbit: Operational orbit
    :type operational_orbit: poliastro.twobody.Orbit
    :param disposal_orbit: Disposal orbit
    :type disposal_orbit: poliastro.twobody.Orbit
    :param state: Spacecraft actual state
    :type state: str
    """
    def __init__(self, spacecraft_id, structure_mass=0.*u.kg, volume=0.*u.m**3, insertion_orbit=None, operational_orbit=None, disposal_orbit=None,state="standby"):
        self.id = spacecraft_id
        self.state = state

        self.initial_volume = volume
        self.current_volume = volume

        self.insertion_orbit = insertion_orbit
        self.operational_orbit = operational_orbit
        self.disposal_orbit = disposal_orbit
        self.current_orbit = None
        self.previous_orbit = None

        self.mothership = None

        self.modules = dict()
        self.structure_module = StructureModule(self.id + '_Structure',
                                                self,
                                                mass_contingency=0.0,
                                                dry_mass_override=structure_mass)

    def add_module(self, module):
        """ Add a module to its list

        :param module: new module
        :type module: :class:`~Modules.GenericModule.GenericModule`
        """
        if module in self.modules:
            warnings.warn('Module ', module.id, ' already in servicer ', self.id, '.', UserWarning)
        else:
            self.modules[module.id] = module

    def change_orbit(self, orbit):
        """ Update current orbit. Save previous orbit

        :param orbit: new orbit
        :type orbit: poliastro.twobody.Orbit
        """
        # Update upperstage own orbit
        self.previous_orbit = self.current_orbit
        self.current_orbit = orbit

    def reset(self):
        """ Reset the instance. Mothership and current orbits are cleared
        """
        # Reset orbits
        self.current_orbit = None
        self.previous_orbit = None

        # Reset mothership link
        self.mothership = None
        self.state = "standby"

    def get_id(self):
        """Get the Spacecraft's id

        :return: instance id
        :rtype: str
        """
        return self.id

    def get_initial_volume(self):
        """ Get the initial volume

        :return: initial volume
        :rtype: (u.m**3)
        """
        return self.initial_volume

    def get_current_volume(self):
        """ Get the current volume

        :return: current volume
        :rtype: (u.m**3)
        """
        return self.current_volume

    def get_dry_mass(self):
        """ Get the dry mass

        :return: dry mass
        :rtype: (u.kg)
        """
        mass = 0.
        for module in self.modules.values():
            mass += module.get_dry_mass()
        return mass

    def get_modules_dry_mass_str(self):
        """ Outputs in a str the dry mass of each module

        :return: Text listing the dry mass of each module
        :rtype: str
        """
        str_mass = ""
        for module in self.modules.values():
            str_mass += f"\n\t\t{module.get_id()}: {module.get_dry_mass():.01f}"
        return str_mass

    def get_current_mass(self):
        """ Get the current mass. Alias to :meth:`~Spacecrafts.Spacecraft.Spacecraft.get_dry_mass`

        :return: current mass
        :rtype: (u.kg)
        """
        mass = 0.
        for module in self.modules.values():
            mass += module.get_current_mass()
        return mass

    def get_initial_wet_mass(self):
        """ Get the initial mass. Alias to :meth:`~Spacecrafts.Spacecraft.Spacecraft.get_dry_mass`

        :return: dry mass
        :rtype: (u.kg)
        """
        mass = 0.
        for module in self.modules.values():
            mass += module.get_initial_wet_mass()
        return mass

    def get_modules_initial_wet_mass_str(self):
        """ Outputs in a str the initial wet mass of each module

        :return: Text listing the initial wet mass of each module
        :rtype: str
        """
        str_mass = ""
        for module in self.modules.values():
            str_mass += f"\n\t\t{module.get_id()}: {module.get_initial_wet_mass():.01f}"
        return str_mass

    def get_current_orbit(self):
        """ Get the current orbit

        :return: current orbit
        :rtype orbit: poliastro.twobody.Orbit
        """
        return self.current_orbit

    def set_current_orbit(self,orbit):
        """ Set the current orbit

        :param orbit: new orbit
        :type orbit: poliastro.twobody.Orbit
        """
        self.current_orbit = orbit

    def get_insertion_orbit(self):
        """ Get the insertion orbit

        :return: insertion orbit
        :rtype orbit: poliastro.twobody.Orbit
        """
        return self.insertion_orbit

    def get_operational_orbit(self):
        """ Get the operational orbit

        :return:  operational orbit
        :rtype orbit: poliastro.twobody.Orbit
        """
        return self.operational_orbit

    def get_disposal_orbit(self):
        """ Get the disposal orbit

        :return: disposal orbit
        :rtype orbit: poliastro.twobody.Orbit
        """
        return self.disposal_orbit

    def get_relative_raan_drift(self, duration, own_orbit=None, other_object_orbit=None):
        """ Returns the relative raan drift between two orbits

        :param duration: drift duration
        :type duration: u.<time unit>
        :param own_orbit: first orbit, defaults to None
        :type own_orbit: poliastro.twobody.Orbit, optional
        :param other_object_orbit: second orbit, defaults to None
        :type other_object_orbit: poliastro.twobody.Orbit, optional
        :return: total raan drift from orbit 1 raan
        :rtype: u.deg
        """
        if not own_orbit:
            own_orbit = self.get_insertion_orbit()
        _, own_nodal_precession_speed = nodal_precession(own_orbit)
        _, other_nodal_precession_speed = nodal_precession(other_object_orbit)
        delta_nodal_precession_speed = own_nodal_precession_speed - other_nodal_precession_speed
        return (delta_nodal_precession_speed * duration).decompose()

    def __str__(self):
        return self.get_id()