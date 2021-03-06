===============================
Support, Installation and Setup
===============================

Getting Support
================

For contractual and licence question, please contact the `Project Manager <https://people.epfl.ch/emmanuelle.david>`_.

For code support and debugging, please contact the `Code Maintainer <https://people.epfl.ch/flavio.brancato>`_.

Getting The Code
=================
The TCAT code base is hosted on gitlab: https://gitlab.com/eSpace-epfl/tcat.git.
After creating an account on the gitlab website, access can be requested from the `Code Maintainer
<https://people.epfl.ch/flavio.brancato>`_.

.. image:: images/gitlab.png

The "Clone" button at the bottom of the page allows you to clone the repository, if you want to use git and its
features. The download button next to it allows you to download the TCAT code directly to your computer.

Installing and using the code
==================================
The Python programming language is required to use TCAT. Please refer to your IT services to install python and the
following packages.

============  ==================
Package       Usage
============  ==================
astropy       Orbital dynamics
xlrd          read Excel files
gurobi        optimization
mystic        optimization
poliastro     orbital dynamics
TLE-tools     read TLE
============  ==================

Alternatively, you can use `Anaconda <https://www.anaconda.com/products/individual>`_ to simplify the management of your
python environment.

Scripts to execute are then found inside the TCAT folder. To execute a script, the simplest way is to open your os
command prompt, and run python as follow:

.. code-block::

    python <path to the scrip>.py

Developing the code
===========================
For developers, the following additional packages are necessary for documentation purposes.

============  ==================
Package       Usage
============  ==================
sphinx        Documentation
============  ==================

You can use the IDE of your choice, but we recommend `Pycharm <https://www.jetbrains.com/pycharm/>`_.
