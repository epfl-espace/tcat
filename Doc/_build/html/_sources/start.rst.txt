===============
Getting started
===============

Using TCAT is decomposed in three tasks:

1. Specify inputs
2. Execute simulations
3. Analyse results

.. note::
    User actions might be different for each use case, therefore each use case implemented might specify their own
    ways to get started with TCAT. Some use cases might provide graphical user interfaces, others will require
    the user to open the python code and manually change inputs.

To help the user get familiar with the logic behind these, we propose a walk-through of a simple example based on the
debris removal use case. This section goes through and explains the code in the 'getting_started_example.py' script
available inside the TCAT folder.


Specifying inputs
===================

General inputs
................
With this example, we will go through how to define a simple debris removal mission with a single target and chaser.

First, let's import what we need to use the general concepts linked to Plans (Plan_module) and the phases we will want to use for
this use case.

.. code-block:: python

    from Plan_module import *
    from Phases.Approach import *
    from Phases.Capture import *
    from Phases.Insertion import *
    from Phases.OrbitChange import *
    from Phases.Release import *

Then, let's import what we need to use the general concepts linked to Fleets (Fleet_module) and the modules we will
want to use for this use case.

.. code-block:: python

    from Fleet_module import *
    from Modules.PropulsionModule import *
    from Modules.CaptureModule import *
    from Modules.StructureModule import *
    from Modules.ThermalModule import *
    from Modules.AOCSModule import *
    from Modules.EPSModule import *
    from Modules.CommunicationModule import *
    from Modules.DataHandlingModule import *
    from Modules.ApproachSuiteModule import *

Lastly, let's import a use case specific class, the ADR_Client class, that gathers useful methods to define the client
of the use case. ADR stands for Active Debris Removal.

.. code-block:: python

    from ADRClient_module import *

We start by fixing the starting time at which the simulation will start (start of the first phase). This will serve as
reference throughout the code.

.. code-block:: python

    starting_epoch = Time("2025-06-02 12:00:00", scale="tdb")

Orbit inputs
...............
Then we will define all orbits required during the mission. The following code block shows how we define the insertion
orbit for the servicer. Notice the use of the astropy Orbit and unit packages (imported as Orbit and u respectively)
to define the units used. The target orbit and reentry orbit are defined similarly but not listed below.

.. code-block:: python

    a = 500. * u.km + Earth.R
    ecc = 0. * u.rad / u.rad
    inc = 98.6 * u.deg
    raan = 30.5 * u.deg
    argp = 0. * u.deg
    nu = 0. * u.deg
    servicer_insertion_orbit = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu, starting_epoch)

.. tip::
    Astropy provides two interesting packages to handled units and constants (Astropy.units and Astropy.constants,
    usually imported in the code as u and const) that are used extensively in TCAT. Using them ensures easy unit
    conversions and highlights immediately formulas with units mismatch.

.. caution::
    The definition of orbits is important to ensure a feasible plan. Make sure that when using TCAT, you are familiar
    with the impact astrodynamics can have on your plan. For instance, if the servicer starts on a similar altitude as
    the target but with a big raan difference, then the phasing duration will be prohibitively long and an additional
    manoeuvre might be required to a lower or higher phasing orbit.

Fleet and servicers inputs
.............................
This part of the inputs let's us define the servicer. First, we define the servicer and its modules. To start, we
create a fleet that will host the servicer. We give it an identifier and an architecture (here single_picker as a
single servicer grabs a single target).

.. code-block:: python

    fleet = Fleet('ADR', 'singe_picker')

Then we similarly create a servicer with its own identifier and a group (here servicers).

.. code-block:: python

    servicer001 = Servicer('servicer001', 'ADR_servicers')

Then, we define the modules of the servicer, giving them appropriate identifiers (based on the servicer identifier) and
specifying that they belong to the servicer.

.. note::
    Each of these modules will use the models linked to the servicer group defined for its servicer.

.. code-block:: python

    reference_structure = StructureModule(servicer001.id + '_structure', servicer001)
    reference_thermal = ThermalModule(servicer001.id + '_thermal', servicer001)
    reference_aocs = AOCSModule(servicer001.id + '_aocs', servicer001)
    reference_eps = EPSModule(servicer001.id + '_eps', servicer001)
    reference_com = CommunicationModule(servicer001.id + '_communication', servicer001)
    reference_data_handling = DataHandlingModule(servicer001.id + '_data_handling', servicer001)
    reference_approach_suite = ApproachSuiteModule(servicer001.id + '_approach_suite', servicer001)

The capture module requires more inputs. Indeed, because multiple modules of the same kind could be placed on a single
servicer it is possible to specify which is the default module used by the servicer to perform capture phases. This is
used to simplify the creation of the plan later.

.. tip::
    Note that when defining the capture module, a dry mass is given to override the usual dry mass model that would
    normally be used. There are a number of arguments that can be given to modules and phases to override or refine
    their parameters.

.. code-block:: python

    reference_capture = CaptureModule(servicer001.id + '_capture', servicer001, dry_mass_override=20. * u.kg)
    reference_capture.define_as_capture_default()

The propulsion module also requires more inputs. Similarly to the capture module, it is possible to specify a default
module to perform orbit change phases (main propulsion) and a module to perform approach phases (RCS, Reaction Control
System) phases.

.. tip::
    When defining default modules, it is possible to assign the same module for different tasks. In our case for
    instance, the same propulsion module is in charge of both orbital maneouvres and reaction control. The underlying
    model takes this into account and will size the module to ensure it has the thrusters necessary to perform its
    tasks.

Most importantly, the propulsion modules requires an initial guess for the propellant mass to
be budgeted. This initial guess is the starting point for the simulation and is refined through convergence.

.. danger::
    It is possible that if the initial propellant guess is too far from the actual value, convergence is not possible.
    This problem is increasingly important with more complex servicers and models. Some use cases implement smart ways
    to define these initial guesses. For this example, the initial guess is set at 100kg of propellant.

.. code-block:: python

    initial_propellant_guess = 100. * u.kg
    reference_rendezvous_propulsion = PropulsionModule(servicer001.id + '_propulsion', servicer001, 'mono-propellant',
                                                       22 * u.N, 0.01 * u.N, 240 * u.s, initial_propellant_guess,
                                                       100. * u.kg, propellant_contingency=0.1)
    reference_rendezvous_propulsion.define_as_rcs_propulsion()
    reference_rendezvous_propulsion.define_as_main_propulsion()

Additionally, parameters of the propulsion can be specified in the declaration of the module itself. Here
the maximum and minimum thrust, the specific impulse, the maximum tank capacity and the propellant contingency to
be used are defined.

.. note::
    Contingencies are used in TCAT to reach realistic solutions. There are dry mass contingencies, propellant
    contingencies and delta v contingencies. Dry mass contingencies can be defined when creating modules, otherwise
    default values will be added. When querying the dry mass of the module, the mass with contingency will be given
    (for instance, this means that the additional mass for contingency is taken into account when dimensioning
    manoeuvres and other modules). There are propellant contingencies, as defined in our example at 10% or 0.1. This
    contingency represents the amount of propellant we want left in the tanks at the end of the plan. When querying the
    propellant mass or wet mass of a servicer, the actual simulated amount of propellant is returned. The delta v
    contingency is defined when defining phases (see below).

Finally, the servicer is added to the fleet.

.. code-block:: python

    fleet.add_servicer(servicer001)

Client inputs
...........................
This part of the inputs varies depending on the use case. For the debris removal use case, the definition of the
debris is required prior to the definition of the plan. The syntax here is specific to the use case and simply defines
the identifier for the target and assigns a mass to it and specify the orbits for its insertion (not relevant here),
its current operational orbit (where the servicer needs to capture it) and its reentry orbit (where the servicer needs
to release it).

.. code-block:: python

    clients = ADRClients('targets')
    target = Target('target', 100. * u.kg, target_orbit, target_orbit, target_orbit)
    clients.add_target(target)


.. note::
    In some use cases, no clients are foreseen. In this case, simply disregard this step.

.. tip::
    For the developers, the use of a client class is very useful to gather all elements that are external to the fleet
    but will still be influenced by the plan (therefore need to be changed during simulations and reset before each
    simulation).

Plan and phase inputs
...............................
This part of the inputs let's use define how we want the servicer to perform the mission.

First we create the plan. We will then create the phase in chronological order.

.. danger::
    If the phases are not created in a chronological manner, then the simulation will run into timing problems.

.. danger::
    If a fleet has multiple agents (multiple servicers for instance), that are in practice performing tasks in parallel,
    the current implementation in TCAT is still valid, as long as there is no interdependence between the tasks
    of each servicer. Otherwise, the simulation's results will be wrong.

.. code-block:: python

    plan = Plan('plan', starting_epoch)


The mission profile is defined as such: launch insertion, rendezvous and approach of target, capture of target,
lowering of orbit to reentry orbit, release of target. Each phase is created with its parameters and assigned to a
module previously created in the servicer.

The insertion phase requires the insertion orbit. In this example, a specific duration is also given. Usually, if
these values are not given explicitly, default values are used.

.. code-block:: python

    insertion = Insertion('Insertion', plan, insertion_orbit, duration=30. * u.day)
    insertion.assign_module(servicer001.get_main_propulsion_module())

Then a first orbit change is performed to the target orbit. An initial orbit is also specified (this is used in early
iterations to ease convergence). A specific delta v contingency is specified.

.. note::
    Delta v contingencies are applied to the delta v computed based on the astrodynamical models for each phase.

Another important option is the option to specify a desired Right Angle of Ascension Node (raan) for the final orbit.
By default or if it is set to False, the orbit change will only affect apogee, perigee and inclination. If it set to
True, the orbit change will also include raan correction and possibly some nodal precession phasing.

.. caution::
    The current astrodynamical models in TCAT do not take differences in argument of periapsis when computing manoeuvres!

.. tip::
    The raan_specified parameter is particularly useful because some manoeuvres care about raan but others do not.
    In our case for instance, the orbit change to reach the target needs to specify the raan so that approach can happen
    , but the orbit change to bring the target on its reentry orbit does not because only the final perigee is
    important.

.. code-block:: python

    orbit_raise = OrbitChange('Raise', plan, target_orbit, raan_specified=True, initial_orbit=insertion_orbit,
                              delta_v_contingency=0.1)
    orbit_raise.assign_module(servicer001.get_main_propulsion_module())


Then, the approach is performed. This phase represents the manoeuvres required to bring two objects in similar orbits
within close proximity of each other. The approach phase needs as inputs an estimation of the consumed propellant during
this phase (here 5 kg based on rough control simulations). The capture phase needs to specify which object is captured
(thus the importance of defining the target beforehand). The same is true for the release phase, which concludes the
plan.

.. code-block:: python

    approach = Approach('Approach', plan, target, 5. * u.kg)
    approach.assign_module(servicer001.get_rcs_propulsion_module())

    capture = Capture('Capture', plan, target)
    capture.assign_module(servicer001.get_capture_module())

    deorbit = OrbitChange('Deorbit', plan, reentry_orbit, raan_specified=False, initial_orbit=target_orbit,
                          delta_v_contingency=0.1)
    deorbit.assign_module(servicer001.get_main_propulsion_module())

    release = Release('Release', plan, target)
    release.assign_module(servicer001.get_capture_module())

This sequence of inputs is the most basic way to set parameters and assumptions. More complex tasks, like setting up
custom models and behaviors require the involvement of a developer to implement new phases, modules and models.

Execute simulation
===================
Now that all inputs are set, the fleet is converged. We need to give it as input the plan and the clients as we defined
them. Here the convergence margin is also specified instead of the default. This margin is the precision we want when
it comes to dry mass models and propellant computations. What this does is that iw will execute the phases of the
mission and change the initial propellant mass until convergence is reached and the servicer is sized to perform the
plan with the contingencies we specified.

.. code-block:: python

    fleet.converge(plan, clients, convergence_margin=0.1 * u.kg)

.. note::
    To execute the code, you can use your favorite IDE to run the script or directly execute the script from your
    OS command prompt. Refer to the Support, Installation and Setup section for more details.

Analyse results
===============
After the simulation runs, a number of tools are available depending on the use case. The crudest way to see the
results of TCAT is to ask for text reports. These will ouptut a description for each fleet, servicer, module, plan and
phase. In our script, the last two lines will trigger the results ot be printed in the command prompt.

.. code-block:: python

    plan.print_report()
    fleet.print_report()


The result will be as follow for the plan. Note the evolution in propellant mass, orbit and date. Also note the
manoeuvres duration which are very long. This let's us know that to be a better representation of the mission, we
probably need to assign intermediate raising and lowering orbits to split the manoeuvres into more manageable durations.
This is an example of output that the tool can provide.

.. code-block:: python

    Start : 2025-06-02 12:00:00.000
    ---
    Insertion: Insertion
            Epoch: 2025-07-02 12:00:00.000
            Servicer: servicer001
            Module: servicer001_propulsion
            Duration : 30.0 d
            Servicer Orbit : 500 km x 500 km, raan: 65 deg, ltan 324 deg
            Servicer Current Mass : 218.2 kg
            Servicer Wet Mass     : 218.2 kg
    ---
    Orbit change: Raise
            Epoch: 2025-10-23 11:50:47.448
            Servicer: servicer001
            Module: servicer001_propulsion
            Duration : 0.3 yr
            Servicer Orbit : 715 km x 729 km, raan: 194 deg, ltan 342 deg
            Servicer Current Mass : 205.8 kg
            Servicer Wet Mass     : 218.2 kg
            Delta v: 137.6 m / s
            Servicer Prop. Mass :
            Initial raan : 64.8 deg
            Manoeuvres :
                    1.7 m / s in 162662.4 min
                    58.3 m / s in 12.3 min
                    65.0 m / s in 13.8 min

    ---
    Approach: Approach
            Epoch: 2025-11-02 11:50:47.448
            Servicer: servicer001
            Module: servicer001_propulsion
            Duration : 10.0 d
            Servicer Orbit : 715 km x 729 km, raan: 205 deg, ltan 343 deg
            Servicer Current Mass : 200.3 kg
            Servicer Wet Mass     : 218.2 kg
            Of target
    ---
    Capture: Capture
            Epoch: 2025-11-03 11:50:47.448
            Servicer: servicer001
            Module: servicer001_capture
            Duration : 1440.0 min
            Servicer Orbit : 715 km x 729 km, raan: 206 deg, ltan 343 deg
            Servicer Current Mass : 300.3 kg
            Servicer Wet Mass     : 218.2 kg
            Of target
    ---
    Orbit change: Deorbit
            Epoch: 2025-11-03 12:36:57.799
            Servicer: servicer001
            Module: servicer001_propulsion
            Duration : 46.2 min
            Servicer Orbit : 50 km x 729 km, raan: 206 deg, ltan 343 deg
            Servicer Current Mass : 275.3 kg
            Servicer Wet Mass     : 218.2 kg
            Delta v: 205.2 m / s
            Servicer Prop. Mass :
            Initial raan : 205.6 deg
            Manoeuvres :
                    186.5 m / s in 53.0 min
                    0.0 m / s in 0.0 min

    ---
    Release: Release
            Epoch: 2025-11-06 12:36:57.799
            Servicer: servicer001
            Module: servicer001_capture
            Duration : 3.0 d
            Servicer Orbit : 50 km x 729 km, raan: 209 deg, ltan 343 deg
            Servicer Current Mass : 175.3 kg
            Servicer Wet Mass     : 218.2 kg
            Of target

The result will be as follow for the fleet.

.. code-block:: python

    ADR
    ----------------------------------------------------------------
    servicer001
    Dry mass : 170.45 kg
    Wet mass : 218.2 kg
    Modules :
    servicer001_structure
              dry mass: 29.7 kg
              reference power 0.0 W
    servicer001_thermal
              dry mass: 8.7 kg
              reference power 26.9 W
    servicer001_aocs
              dry mass: 10.5 kg
              reference power 51.7 W
    servicer001_eps
              dry mass: 11.7 kg
              reference power 40.0 W
    servicer001_communication
              dry mass: 15.1 kg
              reference power 20.0 W
    servicer001_data_handling
              dry mass: 7.0 kg
              reference power 40.0 W
    servicer001_approach_suite
              dry mass: 17.4 kg
              reference power 45.0 W
    servicer001_propulsion
              dry mass: 17.0 kg
              reference power 49.6 W
              prop mass: 47.8 kg
    servicer001_capture
              dry mass: 25.0 kg
              reference power 0.0 W
    Phasing : servicer001_propulsion
    RDV : servicer001_propulsion
    Capture : servicer001_capture
    Mothership : None
    Kits :