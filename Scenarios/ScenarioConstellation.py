"""
Created:        17.05.2022
Last Revision:  28.06.2022
Author:         Emilien Mingard
Description:    Constellation dedicated Scenario Class definition
"""

# Import Class
from Scenarios.Scenario import *
from Constellations.ConstellationForDeployment import ConstellationForDeployment

# Class definition
class ScenarioConstellation(Scenario):
    def __init__(self, scenario_id, config_file):
        super().__init__(scenario_id, config_file)

    def create_constellation(self):
        self.constellation = ConstellationForDeployment(self.constellation_name)