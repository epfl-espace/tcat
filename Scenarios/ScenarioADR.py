"""
Created:        28.06.2022
Last Revision:  28.06.2022
Author:         Malo Goury
Description:    Scenario for constellation deployment
"""

# Import Class
from Scenarios.Scenario import *
from Constellations.ConstellationForADR import ConstellationForADR

# Class definition
class ScenarioADR(Scenario):
    def __init__(self, scenario_id, json):
        super().__init__(scenario_id, json)

    def create_constellation(self):
        self.constellation = ConstellationForADR(self.constellation_name)