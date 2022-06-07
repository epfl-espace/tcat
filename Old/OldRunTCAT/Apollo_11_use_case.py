from ADRClient_module import *

from Commons.Inputs import *
from Fleet_module import *
from Phases.Descending import Descending

from Phases.Capture import Capture
from Phases.Insertion import Insertion
from Phases.Release import Release
from Phases.Ascending import Ascending

from Plan_module import *
from Modules.AOCSModule import AOCSModule
from Modules.ApproachSuiteModule import ApproachSuiteModule
from Modules.CaptureModule import CaptureModule
from Modules.CommunicationModule import CommunicationModule
from Modules.DataHandlingModule import DataHandlingModule
from Modules.EPSModule import EPSModule

from Modules.PropulsionModule import PropulsionModule
from Modules.StructureModule import StructureModule
from Modules.ThermalModule import ThermalModule

from astropy.time import Time
from astropy import units as u

from poliastro.bodies import Moon, Earth
from poliastro.twobody import Orbit
import warnings

warnings.filterwarnings("error")


class Scenario:
    """ A scenario is a class to represent one option within the tradespace of ADR service.
    It consist of objects describing the clients, the servicer fleet and the operational plan.

    The scenario is created based on the following tradespace parameters:
        - client target and load mass
        - main orbits
        - composition of the fleet
        - servicers orbits at insertion

    The scenario is also dependant on parameters defined inside the following object:
        - client_module (load mass, target coordinates)
        - plan_module
            -phases (duration, cost model parameters)
        - fleet_module (convergence criteria, fleet cost models)
            - servicers
                -modules (mass model parameters, cost model parameters, contingencies)

    Args:
        scenario_id (str): Standard ID. Needs to be unique.

    Attributes:
        ID (str): Standard ID. Needs to be unique.
        clients (Client_module.Clients): object describing the client demands (load mass, target on the moon, time constrain)
        fleet (Fleet_module.Fleet): object describing the servicer fleet
        plan (Plan_module.Plan): object describing the operations of the service
        starting_epoch (astropy.Time): reference time of first servicer launch
    """

    def __init__(self, scenario_id="direct", architecture="direct", prop_type='bi-propellant'):
        self.ID = scenario_id
        self.clients = None
        self.fleet = None
        self.plan = None
        self.architecture = architecture
        self.prop_type = prop_type
        self.servicerss = None
        self.orbits = dict()
        self.lunar_transfer_orbit = None
        self.starting_epoch = Time("2025-01-01 12:00:00", scale="tdb")

    def setup(self):
        """ Create the clients, fleet and plan based on inputs and assumptions.
        If clients is given in argument, it is used instead of redefining clients.
        Using clients as argument allows us to run different scenarios with the same moon target.

        Args:

        """
        self.define_clients()
        self.define_fleet()
        self.define_plan(self.architecture, self.fleet)
        self.define_servicer()

    def execute(self, verbose=False):
        """ Execute the scenario until the fleet converges using a method from the fleet class.
        If Verbose is True, convergence information will be printed.

        Args:
            verbose (boolean): if True, print information during scenario execution
        """
        self.fleet.design(self.plan, self.clients, verbose=verbose)

        # try:
        #    self.fleet.design(self.plan, self.clients, verbose=verbose)
        #    return True
        # except RuntimeWarning as warning:
        #    return warning

    # define the new functions needed for the ESA moon exploration
    # def define_nbr_cargo(self, load_mass, servicer_capacity):
    #     """
    #     Define the number of cargo that have to be launch depending on the total load mass
    #     Return: number of cargo
    #     """
    #     nbr_cargo = load_mass / servicer_capacity
    #     return nbr_cargo

    def define_servicer_orbits(self):
        """ Define orbits needed for servicers definition.

        Return:
            (poliastro.twobody.Orbit): servicers insertion orbit
            (poliastro.twobody.Orbit): servicers lunar low orbit
            (poliastro.twobody.Orbit): servicers landing orbit

        """

        # servicers insertion orbit LTO
        a = 202849. * u.km
        ecc = 0.9665 * u.one
        inc = 23.0 * u.deg
        raan = 0. * u.deg
        argp = 90. * u.deg
        nu = 0. * u.deg
        lunar_transfer_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, self.starting_epoch)
        # servicers lunar low orbit
        a = 1837000. * u.m
        ecc = 0. * u.one
        inc = 27 * u.deg
        raan = 0. * u.deg
        argp = 90. * u.deg
        nu = 0. * u.deg
        lunar_low_orbit = Orbit.from_classical(Moon, a, ecc, inc, raan, argp, nu, self.starting_epoch)
        # servicers landing orbit // define a function to calculate it
        per_alt = 18000. *u.m
        perigee = per_alt + Moon.R
        ap_alt = 100. * u.km
        apogee = ap_alt + Moon.R
        a = (apogee + perigee) / 2
        ecc = (apogee - perigee) / (apogee + perigee)
        inc = 27. * u.deg
        raan = 0. * u.deg
        argp = 90. * u.deg
        nu = 0. * u.deg
        landing_orbit = Orbit.from_classical(Moon, a, ecc, inc, raan, argp, nu, self.starting_epoch)
        self.orbits = lunar_transfer_orbit, lunar_low_orbit,  landing_orbit
        self.lunar_transfer_orbit = lunar_transfer_orbit
        return lunar_transfer_orbit, lunar_low_orbit, landing_orbit

    def get_orbits(self):

        return self.orbits


    def define_fleet(self):
        # Define relevant orbits
        lunar_transfer_orbit, lunar_low_orbit, landing_orbit = self.define_servicer_orbits()
        # Define fleet
        fleet = Fleet('Servicers')
        # Iterate for the number of servicers, create appropriate servicers and add it to the fleet  #as soon as more scenarios are added
        if self.architecture == 'direct':

            temp_servicer = self.create_service_module('service_module', lunar_transfer_orbit)
            fleet.add_servicer(temp_servicer)
            temp_servicer = self.create_lunar_module('lunar_module', lunar_transfer_orbit)
            fleet.add_servicer(temp_servicer)
            temp_servicer = self.create_ascent_module('ascent_module', lunar_transfer_orbit)
            fleet.add_servicer(temp_servicer)
        else:
            raise Exception('Unknown architecture {}'.format(self.architecture))
        # Assign fleet as attribute of class
        self.fleet = fleet
        return fleet.servicers

    def create_service_module(self, servicer_id, orbit):

        service_module = Servicer(servicer_id, orbit, 'servicing', 'planetary',ref_mass=24520, ref_inertia=50573, expected_number_of_targets=1,
                                  additional_dry_mass=3000. * u.kg, contingency=0.1)

        servicer_lunar_low_orbit_initial_propellant_guess = 5000. * u.kg
        servicer_lunar_low_orbit_propulsion = PropulsionModule(servicer_id + '_lunar_low_orbit',
                                                               service_module, 'bi-propellant', 91000 * u.N,
                                                               1000 * u.N, 314 * u.s,
                                                               servicer_lunar_low_orbit_initial_propellant_guess,
                                                               250 * u.kg, propellant_contingency=0,
                                                               is_refueler=False)

        servicer_lunar_low_orbit_propulsion.define_as_main_propulsion()

        servicer_capture_module = CaptureModule('Capture_module', service_module, ref_power=2500)
        servicer_capture_module.define_as_capture_default()
        servicer_module_structure = StructureModule(servicer_id + '_structure', service_module)
        servicer_module_thermal = ThermalModule(servicer_id + '_thermal', service_module)
        servicer_module_aocs = AOCSModule(servicer_id + '_aocs', service_module)
        servicer_module_eps = EPSModule(servicer_id + '_eps', service_module)
        servicer_module_com = CommunicationModule(servicer_id + '_communication', service_module)
        servicer_module_data_handling = DataHandlingModule(servicer_id + '_data_handling', service_module)
        return service_module

    def create_lunar_module(self, servicer_id, orbit):

        lunar_module = Servicer(servicer_id, orbit, 'servicing', 'planetary', expected_number_of_targets=1,
                                additional_dry_mass=200. * u.kg, contingency=0.05)

        servicer_descent_initial_propellant_guess = 5000. * u.kg
        servicer_descent_initial_propulsion = PropulsionModule(servicer_id + '_landing_orbit',
                                                               lunar_module, 'bi-propellant', 44000 * u.N,
                                                               4000 * u.N, 311 * u.s,
                                                               servicer_descent_initial_propellant_guess,
                                                               250 * u.kg, propellant_contingency=0, is_refueler=False)

        servicer_descent_initial_propulsion.define_as_main_propulsion()
        lunar_module_capture_module = CaptureModule('Capture_module', lunar_module)
        lunar_module_capture_module.define_as_capture_default()
        lunar_module_structure = StructureModule(servicer_id + '_structure', lunar_module)
        lunar_module_thermal = ThermalModule(servicer_id + '_thermal', lunar_module)
        lunar_module_aocs = AOCSModule(servicer_id + '_aocs', lunar_module)
        lunar_module_eps = EPSModule(servicer_id + '_eps', lunar_module)
        lunar_module_com = CommunicationModule(servicer_id + '_communication', lunar_module)
        lunar_module_data_handling = DataHandlingModule(servicer_id + '_data_handling', lunar_module)

        return lunar_module

    def create_ascent_module(self, servicer_id, orbit):

        ascent_module = Servicer(servicer_id, orbit, 'servicing', 'planetary', expected_number_of_targets=1,
                                 additional_dry_mass=400. * u.kg, contingency=0.15)

        servicer_descent_initial_propellant_guess = 800. * u.kg
        servicer_descent_initial_propulsion = PropulsionModule(servicer_id + '_landing_orbit',
                                                               ascent_module, 'bi-propellant', 16000 * u.N,
                                                               4000 * u.N, 311 * u.s,
                                                               servicer_descent_initial_propellant_guess,
                                                               250 * u.kg,
                                                               propellant_contingency=0, is_refueler=False)
        servicer_descent_initial_propulsion.define_as_main_propulsion()

        ascent_module_structure = StructureModule(servicer_id + '_structure', ascent_module)
        ascent_module_thermal = ThermalModule(servicer_id + '_thermal', ascent_module)
        ascent_module_aocs = AOCSModule(servicer_id + '_aocs', ascent_module)
        ascent_module_eps = EPSModule(servicer_id + '_eps', ascent_module)
        ascent_module_com = CommunicationModule(servicer_id + '_communication', ascent_module)
        ascent_module_data_handling = DataHandlingModule(servicer_id + '_data_handling', ascent_module)

        return ascent_module

    def define_servicer(self):
        service_module_test = self.fleet.servicers.get('servicer')
        self.servicerss = service_module_test

    def define_plan(self, architecture, fleet):
        # Define relevant orbits
        lunar_transfer_orbit, lunar_low_orbit, landing_orbit = self.define_servicer_orbits()
        # Define module
        # temp_service_module = self.create_service_module('service_module', lunar_transfer_orbit)
        # lunar_module = self.create_lunar_module('lunar_module', lunar_low_orbit)
        temp_service_module = fleet.servicers.get('service_module')
        temp_lunar_module = fleet.servicers.get('lunar_module')
        temp_ascent_module = fleet.servicers.get('ascent_module')

        # TO DO : alignment phase --> how to modelise it
        plan = Plan('Plan', self.starting_epoch)

        if architecture == 'direct':
            # insertion of the modules in the Lunar Transfer Orbit
            insertion1 = Insertion('Insertion_LTO_service_module', plan, lunar_transfer_orbit,
                                   duration=0. * u.h)  # CHECK DURATION OF LTO INSERTION
            insertion1.assign_module(temp_service_module.get_phasing_module())
            insertion2 = Insertion('Insertion_LTO_lunar_module', plan, lunar_transfer_orbit, duration=0. * u.h)
            insertion2.assign_module(temp_lunar_module.get_landing_module())
            insertion3 = Insertion('Insertion_LTO_ascent_module', plan, lunar_transfer_orbit, duration=0. * u.h)
            insertion3.assign_module(temp_ascent_module.get_ascent_module())
            # captures
            lunar_module_capture = Capture('Lunar_module_capture', plan, temp_lunar_module, duration=0. * u.day)
            lunar_module_capture.assign_module(temp_service_module.get_capture_module())
            ascent_module_capture = Capture('Ascent_module_capture', plan, temp_ascent_module, duration=0. * u.day)
            ascent_module_capture.assign_module(temp_lunar_module.get_capture_module())
            # orbit circularised in a lunar low orbit
            insertion_llo = OrbitChange('Insertion_llo_', plan, lunar_low_orbit, duration=3. * u.day,
                                         delta_v=1000. * u.m / u.s, contingency=0.1)
            insertion_llo.assign_module(temp_service_module.get_phasing_module())
            # release of lunar module
            release_lunar_module = Release('release_lunar_module', plan, temp_lunar_module)
            release_lunar_module.assign_module(temp_service_module.get_capture_module())
            # landing
            landing = Descending('Descent_', plan, orbit=None, duration=3. * u.h, delta_v=2400. * u.m / u.s,
                                 contingency=0.1)
            landing.assign_module(temp_lunar_module.get_landing_module())
            # release of ascent module
            release_ascent_module = Release('release_ascent_module', plan, temp_ascent_module)
            release_ascent_module.assign_module(temp_lunar_module.get_capture_module())
            # ascent
            ascent = Ascending('Ascent', plan, lunar_low_orbit, duration=3. * u.h, delta_v=2000. * u.m / u.s,
                               contingency=0.1)
            ascent.assign_module(temp_ascent_module.get_ascent_module())
            # capture ascent module
            ascent_module_capture2 = Capture('Ascent_module_capture_2', plan, temp_ascent_module, duration=5. * u.h)
            ascent_module_capture2.assign_module(temp_service_module.get_capture_module())
            # release ascent module 2
            release_ascent_module2 = Release('release_ascent_module2', plan, temp_ascent_module)
            release_ascent_module2.assign_module(temp_service_module.get_capture_module())
            # return
            backhome = OrbitChange('return', plan, lunar_transfer_orbit, duration=3. * u.day, delta_v=1000. * u.m / u.s,
                              contingency=0.1)
            backhome.assign_module(temp_service_module.get_phasing_module())

        # add new plan if the scenario architecture change
        # we can also add a creat plan function when plan become more complex

        self.plan = plan

    def define_clients(self):
        """Define clients object.

        Args:
            mass of the load : u.kg
            target : moon coordinates (yet, only around equator +- 30°)
            time constrain (optional)

        Return:
            (Client_module.Clients): created clients

        #target= moon_coordinates() # add the moon surface coordinate
        """
        # Define reference load
        # mass_load = 5000. * u.kg

        # Assign clients as class attribute
        clients = Clients("ESA")
        self.clients = clients

    def __str__(self):
        return self.ID
