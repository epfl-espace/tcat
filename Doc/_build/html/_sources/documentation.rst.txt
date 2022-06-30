==================
Code Documentation
==================

RunTCAT
===================
Creates the proper Scenario object and runs it.

.. automodule:: RunTCAT
   :members:

Senarios
===================
Senario classes instantiate the :py:class:Fleet.Fleet.Fleet, Plan and Constellation objects based on the input json.

Senario
----
.. automodule:: Scenarios.Scenario
   :members:

SenarioConstellation
---------------------
.. automodule:: Scenarios.ScenarioConstellation
   :members:

SenarioADR
---------------------
.. automodule:: Scenarios.ScenarioADR
   :members:

Spacecrafts
===================
These classes define the different types of spacerafts used by the Scenario

Spacecraft
---------------------
.. automodule:: Spacecrafts.Spacecraft
   :members:

Satellite
---------------------
.. automodule:: Spacecrafts.Satellite
   :members:

ActiveSpacecraft
---------------------
.. automodule:: Spacecrafts.ActiveSpacecraft
   :members:

Servicer
---------------------
.. automodule:: Spacecrafts.Servicer
   :members:

UpperStage
---------------------
.. automodule:: Spacecrafts.UpperStage
   :members:

Fleet
===================
This class contain the different Spacecrafts and the Plan required for the Scenario execution.

Fleet
---------------------
.. automodule:: Fleet.Fleet
   :members:

FleetConstellation
---------------------
.. automodule:: Fleet.FleetConstellation
   :members:

FleetADR
---------------------
.. automodule:: Fleet.FleetADR
   :members:

Plan
===================
Contains the different phases requied for the execution of the scenario

Plan
---------------------
.. automodule:: Plan.Plan
   :members:

Constellation
===================
Stores the satellites targeted by the Scenario

Constellation
---------------------
.. automodule:: Constellation.Constellation
   :members:

Phases
===================
These classes and methods describe the different types of phases used. They host astrodynamic models and behavioral
models. All phases inherit from the generic module.

Generic Phase
---------------------
.. automodule:: Phases.GenericPhase
   :members:

Insertion Phase
---------------------
.. automodule:: Phases.Insertion
   :members:

Orbit Change Phase
---------------------
.. automodule:: Phases.OrbitChange
   :members:

Orbit Maintenance Phase
---------------------
.. automodule:: Phases.OrbitMaintenance
   :members:

Refueling Phase
---------------------
.. automodule:: Phases.Refueling
   :members:

Approach Phase
---------------------
.. automodule:: Phases.Approach
   :members:

Capture Phase
---------------------
.. automodule:: Phases.Capture
   :members:

Release Phase
---------------------
.. automodule:: Phases.Release
   :members:


Release Phase
---------------------
.. automodule:: Phases.Release
   :members:

Common Functions used in phases
-----------------------------------
.. automodule:: Phases.Common_functions
   :members:

Modules
===================
These classes and methods describe the different types of modules used. They host mass and power models and behavioral
models. All modules inherit from the generic module.

Generic Module
---------------------
.. automodule:: Modules.GenericModule
   :members:

Data Handling Module
---------------------
.. automodule:: Modules.DataHandlingModule
   :members:

Communication Module
---------------------
.. automodule:: Modules.CommunicationModule
   :members

Electrical Power System Module
---------------------
.. automodule:: Modules.EPSModule
   :members:

Structure Module
---------------------
.. automodule:: Modules.StructureModule
   :members:

Thermal Module
---------------------
.. automodule:: Modules.ThermalModule
   :members:

Attitude and Orbit Control System Module
---------------------
.. automodule:: Modules.AOCSModule
   :members:

Propulsion Module
---------------------
.. automodule:: Modules.PropulsionModule
   :members:

Capture Module
---------------------
.. automodule:: Modules.CaptureModule
   :members:

Approach Suite Module
---------------------
.. automodule:: Modules.ApproachSuiteModule
   :members: