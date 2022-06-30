=====================
General concepts
=====================
TCAT has two objectives:


- Offer quick assessment of feasibility of space missions (both in systems design and operations)

- Enable trade-offs of architectures, technologies, etc. by providing rough estimates of cost and performance figures

The main concepts that are used by TCAT to fulfill its objectives are:

Use Case
    A use case is a particular type of service that fulfills the needs of a client. The original purpose of TCAT was the
    use case of active debris removal for large satellite constellations. Another use case that was implemented in TCAT
    was the transfer of cargo to the Moon for institutional actors. The goal of TCAT is to consolidate a number of tools
    and methods that are not specific to a use case, but can be used to analyse, optimize and trade-off multiple aspects
    of any use case, given appropriate delta development. The code base linked to use cases is separate from the core of
    TCAT.

Scenario
    A scenario is a particular configuration of a **use case** described by a number of parameters. These parameters are
    usually linked to the overall architecture of the service, the design of the systems, the orbits, the operations.
    A scenario for active debris removal could be for instance 3 servicers, with their design and insertion orbits
    defined, each visiting 5 targets to perform orbit lowering with a visit to a tanker for refueling between each
    target. The code base linked to scenarios is separate from the core of TCAT and linked to the code base of the use
    case.

Fleet
    A fleet is a collection of *servicers* (satellites, launchers, ground segments, etc) that will be used to fulfill
    a **scenario**. Within a fleet, servicers can be grouped together depending on their purpose and design.
    For instance the  active debris removal fleet can consist of removers and tankers. The code base linked to the
    definition, management and use of fleets is not dependant on the use case.

Servicer
    A servicer is a collection of *modules* (propulsion, communication, data handling, cargo, etc) that is part of a
    **fleet**.

Module
    Each module that constitutes the **servicer** needs to be thought of as a functional block. The most important
    modules for a servicer will generally be modules that deal with transport and propellant (launch, orbit change,
    planetary insertions, etc). Each module has models for their power consumption and dry mass and possible
    additional performance models (propulsion specific impulse, etc). These models can be different depending on the
    servicer group. The code base linked to the definition, management and use of servicers is not dependant on the use
    case. Each new use case might require the refinement of existing modules or the creation of additional modules.

Plan
    A plan is a collection of *phases* that will be required to perform a **scenario** (launch, orbit changes,
    rendezvous, servicing, etc) . A plan has a chronological order. The code base linked to the definition, management
    and use of plans is not dependant on the use case.

Phase
    A phase describes any type of operations performed during a **plan**. Each phase needs to be assigned to a
    **module**. For instance, an orbit change needs to be assigned to a propulsion module of the servicer that will
    perform the operation. The phase is defined in terms of its duration and its impact on the performing servicer
    and on its environment. These impacts are usually either changes in orbits, consumption or production of resources
    or servicing operations. For instance, a capture phase, performed by a capture module on a servicer needs to be
    assigned a target (removal client) and will link the motion of the target with the servicer until a release phase
    is called. Each new use case might require the refinement of existing phases or the creation of additional modules.
