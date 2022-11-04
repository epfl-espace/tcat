from ScenarioDatabase.ACTConfigLinkers import ACTConfigLinkerBase

class ACTConfigLinker(ACTConfigLinkerBase):
    def __init__(self,json_filepath=None):
        super().__init__(json_filepath)