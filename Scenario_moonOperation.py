from ADRClient_module import *

from Commons.Inputs import *
from Fleet_module import *
from Phases.Descending import Descending
from Phases.Capture import Capture
from Phases.Insertion import Insertion
from Phases.Release import Release
from Phases.From_NRHO import From_NRHO
from Phases.To_NRHO import To_NRHO
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
    # TODO: include fleet and plan definitions via input files to Fleet_module and Plan_module
    def __init__(self, scenario_id=None, architecture=None, prop_type=None, load_mass=None):
        self.ID = scenario_id
        self.clients = None
        self.fleet = None
        self.plan = None
        self.load_mass = load_mass
        self.architecture = architecture
        self.prop_type = prop_type
        self.orbits = dict()
        self.starting_epoch = Time("2025-01-01 12:00:00", scale="tdb")
        self.reference_data = {
            'service_module_ref_power': 2000., 'landing_module_ref_power': 2500., 'cargo_module_ref_power': 1000.,
            'service_module_ref_mass': 24520., 'landing_module_ref_mass': 11624., 'cargo_module_ref_mass': 14327,
            'service_module_ref_inertia': 50573., 'landing_module_ref_inertia': 26052.,
            'cargo_module_ref_inertia': 99000,
            'service_module_ref_mass_EPS': 1200., 'landing_module_ref_mass_EPS': 500.,
            'cargo_module_ref_mass_EPS': 700}

    def setup(self):
        """ Create the clients, fleet and plan based on inputs and assumptions.
        """

        self.define_clients()
        # Define relevant orbits
        self.define_servicer_orbits()
        # Define fleet given attributes of the class .
        self.define_fleet()
        # Define plan, given attributes of the class.
        self.define_plan(self.architecture)

    def execute(self, verbose=False):
        """ Execute the scenario until the fleet converges using a method from the fleet class.
        If Verbose is True, convergence information will be printed.

        Args:
            verbose (boolean): if True, print information during scenario execution
        """

        self.fleet.design(self.plan, self.clients, verbose=verbose)

        # try:
        #     self.fleet.design(self.plan, self.clients, verbose=verbose)
        #     return True
        # except RuntimeWarning as warning:
        #     return warning

    def define_nbr_cargo(self, load_mass, servicer_capacity):
        """
        Define the number of cargo that have to be launch depending on the total load mass
        Return: number of cargo
        """
        nbr_cargo = load_mass / servicer_capacity
        return nbr_cargo

    def define_servicer_orbits(self):
        """ Define orbits needed for servicers definition.
        
        Return:
            A dictionary having:
            - as index the name of the orbit
            - as value the defined orbit, using (poliastro.twobody.Orbit)
        """
        # Retrieve all the orbit names from the input file
        orbit_names = Inputs().list_element_in_a_row("Orbits", "Name")
        # For each orbit, create an ordered list with all the parameters needed for Orbit.from_classical.
        for i in range(len(orbit_names)):
            In = Inputs().call_set_from_reference("Orbits", "Name", orbit_names[i])
            orbit = [In[x] for x in (
                "Main body", "Semi major axis [km]", "Eccentricity", "Inclination [deg]", "RAAN [deg]",
                "Arg. of perigee [deg]",
                "True anomaly [deg]", "Epoch [YYYY-MM-DD hh:mm:ss]")]
            # This if-loop is necessary to "transform" a string to a variable.
            if orbit[0] == "Earth":
                orbit[0] = Earth
            elif orbit[0] == "Moon":
                orbit[0] = Moon
            else:
                raise ValueError(f"{orbit[0]} is mistyped or not yet included in this model.")
            # Put the right unit to each value
            orbit[1] = orbit[1] * u.km
            orbit[2] = orbit[2] * u.one
            orbit[3] = orbit[3] * u.deg
            orbit[4] = orbit[4] * u.deg
            orbit[5] = orbit[5] * u.deg
            orbit[6] = orbit[6] * u.deg
            orbit[7] = Time(orbit[7], scale="tdb")
            # Append to the "orbits" dictionary, in the Orbit.from_classical() format.
            self.orbits.update({orbit_names[i]: Orbit.from_classical(*orbit)})

        return self.orbits

    def define_fleet(self):
        # Retrieve all the vehicle names, depending on the architecture, from the input file
        vehicle_names = Inputs().list_element_in_a_row_if_attribute_is_present("Fleet", "Name", self.architecture,
                                                                               "Mission architecture")
        # Instantiate a dictionary.
        vehicles = {}
        # For each vehicle, create an ordered list with all the parameters needed for "create_vehicle()" function.
        for i in range(len(vehicle_names)):
            In = Inputs().call_set_from_reference("Fleet", "Name", vehicle_names[i])

            vehicle = [In[x] for x in ("Name", "Insertion orbit")]

            vehicle[1] = self.orbits.get(vehicle[1])
            # Append to the "vehicles" dictionary, in the "create_vehicle()" format.
            vehicles.update({vehicle_names[i]: vehicle})
        # --------------------------------------------------------------------------------------------------------------
        # Define fleet
        fleet = Fleet('Servicers')
        for vehicle_names in vehicle_names:
            temp_servicer = self.create_vehicle(*vehicles[vehicle_names])
            fleet.add_servicer(temp_servicer)

        self.fleet = fleet
        return fleet.servicers

    def create_vehicle(self, servicer_id, orbit):

        # Retrieve all the data from a specific vehicle (servicer_id) in the input file
        vehicle_data = Inputs().call_set_from_reference("Fleet", "Name", servicer_id)
        if vehicle_data["Vehicle type"]== "cargo_module":
            vehicle = Servicer(servicer_id, orbit, vehicle_data["Vehicle type"], vehicle_data["Mission type"],
                           self.reference_data['service_module_ref_mass'],
                           self.reference_data['service_module_ref_inertia'], expected_number_of_targets=1,
                           additional_dry_mass=self.load_mass,
                           contingency=vehicle_data["Contingency"])
        else:
            vehicle = Servicer(servicer_id, orbit, vehicle_data["Vehicle type"], vehicle_data["Mission type"],
                           self.reference_data['service_module_ref_mass'],
                           self.reference_data['service_module_ref_inertia'], expected_number_of_targets=1,
                           additional_dry_mass=0 * u.kg,
                           contingency=vehicle_data["Contingency"])

        # Retrieve all the the propulsion system data of a specific vehicle (servicer_id) in the input file
        prop_data = Inputs().call_set_from_reference(servicer_id, 'Subsystem', "Propulsion")
        servicer_service_module_propulsion = PropulsionModule(servicer_id + '_propulsion',
                                                              vehicle, prop_data['Propellant type'],
                                                              prop_data['Max thrust [N]'] * u.N,
                                                              prop_data['Min thrust [N]'] * u.N,
                                                              prop_data['ISP [s]'] * u.s,
                                                              prop_data['Propellant mass (guess) [kg]'] * u.kg,
                                                              prop_data['Tank capacity [kg]'] * u.kg,
                                                              propellant_contingency=prop_data[
                                                                  'Propellant contingency'],
                                                              is_refueler=False)

        servicer_service_module_propulsion.define_as_main_propulsion()
        capture_data = Inputs().call_set_from_reference(servicer_id, 'Subsystem', "Docking")
        # Provide capture module only when necessary
        if not isinstance(capture_data['Dry mass [kg]'], str) or capture_data['Dry mass [kg]'] != 0.:
            vehicle_capture_module = CaptureModule('Capture_module', vehicle,
                                                   self.reference_data[vehicle_data["Vehicle type"] + '_ref_power'],
                                                   capture_data['Dry mass [kg]'] * u.kg)
            vehicle_capture_module.define_as_capture_default()

        vehicle_structure = StructureModule(servicer_id + '_structure', vehicle)
        vehicle_thermal = ThermalModule(servicer_id + '_thermal', vehicle,
                                        self.reference_data[vehicle_data["Vehicle type"] + '_ref_power'],
                                        self.reference_data[vehicle_data["Vehicle type"] + '_ref_mass'])
        vehicle_aocs = AOCSModule(servicer_id + '_aocs', vehicle,
                                  self.reference_data[vehicle_data["Vehicle type"] + '_ref_inertia'])
        vehicle_eps = EPSModule(servicer_id + '_eps', vehicle,
                                self.reference_data[vehicle_data["Vehicle type"] + '_ref_power'],
                                self.reference_data[vehicle_data["Vehicle type"] + '_ref_mass'],
                                self.reference_data[vehicle_data["Vehicle type"] + '_ref_mass_EPS'])
        vehicle_com = CommunicationModule(servicer_id + '_communication', vehicle)
        vehicle_data_handling = DataHandlingModule(servicer_id + '_data_handling', vehicle,
                                                   self.reference_data[vehicle_data["Vehicle type"] + '_ref_power'])
        return vehicle

    def define_plan(self, architecture):

        plan = Plan('Plan', self.starting_epoch)
        # --------------------------------------------------------------------------------------------------------------
        # Retrieve all the phases names, depending on the architecture, from the input file
        phases_names = Inputs().list_element_in_a_row_if_attribute_is_present("Plan", "Name", architecture,
                                                                              "Mission architecture")
        # Instantiate a dictionary.
        phases = {}
        # For each vehicle, create an ordered list with all the parameters needed for each function in "Phases" folder.
        for i in range(len(phases_names)):
            In = Inputs().call_set_from_reference("Plan", "Name", phases_names[i], "Mission architecture", architecture)

            phase = [In[x] for x in (
                "Name", "Insertion orbit", 'Duration [hours]', 'Delta-V required [km/s]', 'Contingency', 'Phase',
                'Servicer involved', "Captured/released object")]
            phase[0] = phase[0] + str(' / Architecture: ') + architecture
            phase.insert(1, plan)
            phase[2] = self.orbits.get(phase[2])
            # Put the right unit to each entry
            phase[3] = phase[3] * u.hr
            if not isinstance(phase[4], str):
                phase[4] = phase[4] * u.km / u.s
            # Substitute string with "servicer" properties
            phase[7] = self.fleet.servicers.get(phase[7])
            phase[8] = self.fleet.servicers.get(phase[8])
            # Append to the "phases" dictionary, in the Phases format.
            phases.update({phases_names[i]: phase})
        # --------------------------------------------------------------------------------------------------------------
        # For each phase assign relevant data (servicers, orbits, duration, delta-v, ...)
        for phase in phases_names:

            if phases[phase][6] in ("Capture", "Release"):
                if phases[phase][7] == None:
                    print("There is an error with vehicle names, please look for typos")
                argument = [phases[phase][0], phases[phase][1], phases[phase][8], phases[phase][3]]
                eval(phases[phase][6])(*argument).assign_module(phases[phase][7].get_capture_module())
            else:
                if phases[phase][7] == None:
                    print("There is an error with vehicle names, please look for typos")
                eval(phases[phase][6])(*phases[phase][0:5]).assign_module(phases[phase][7].get_phasing_module())

        self.plan = plan

    def define_clients(self):
        """Define clients object.

        Return:
            (Client_module.Clients): created clients

        """

        # Assign clients as class attribute
        clients = ADRClients("ESA")
        self.clients = clients

    def __str__(self):
        return self.ID
