"""
Created:        28.06.2022
Last Revision:  28.06.2022
Author:         Malo Goury
Description:    Scenario for constellation deployment
"""

# Import Class
from Scenarios.Scenario import *

# Class definition
class ScenarioConstellation(Scenario):
    def __init__(self, scenario_id, json):
        super().__init__(scenario_id, json)