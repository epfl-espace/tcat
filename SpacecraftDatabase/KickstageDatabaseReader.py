# Created:          13.09.2022
# Last Revision:    13.09.2022
# Authors:          Malo Goury
# Emails:           malo.goury@tcdc.ch
# Description:      Class for reading Kickstage dataabse

# Import libraries
from astropy import units as u
import csv

# Class definition
class KickstageDatabaseReader:
    def __init__(self,kickstage_db_csv_file):
        self.kickstage_list = []
        self.read_csv_db_to_list(kickstage_db_csv_file)

    def read_csv_db_to_list(self,kickstage_db_csv_file):
        with open(kickstage_db_csv_file, 'r') as data:
            self.kickstage_list = list(csv.DictReader(data))

    def get_kickstage_dict(self, kickstage_name):
        for kickstage_dict in self.kickstage_list:
            if kickstage_dict["name"] == kickstage_name:
                return kickstage_dict
        return None

    def get_kickstage_height(self, kickstage_name):
        kickstage_dict = self.get_kickstage_dict(kickstage_name)
        if kickstage_dict is not None:
            return float(kickstage_dict["height"]) * u.m
        else: return None

    def get_kickstage_diameter(self, kickstage_name):
        kickstage_dict = self.get_kickstage_dict(kickstage_name)
        if kickstage_dict is not None:
            return float(kickstage_dict["diameter"]) * u.m
        else: return None

    def get_kickstage_initial_fuel_mass(self, kickstage_name):
        kickstage_dict = self.get_kickstage_dict(kickstage_name)
        if kickstage_dict is not None:
            return float(kickstage_dict["initial_fuel_mass"]) * u.kg
        else: return None

    def get_kickstage_prop_thrust(self, kickstage_name):
        kickstage_dict = self.get_kickstage_dict(kickstage_name)
        if kickstage_dict is not None:
            return float(kickstage_dict["prop_thrust"]) * u.N
        else: return None

    def get_kickstage_prop_isp(self, kickstage_name):
        kickstage_dict = self.get_kickstage_dict(kickstage_name)
        if kickstage_dict is not None:
            return float(kickstage_dict["prop_isp"]) * u.s
        else: return None

    def get_kickstage_prop_dry_mass(self, kickstage_name):
        kickstage_dict = self.get_kickstage_dict(kickstage_name)
        if kickstage_dict is not None:
            return float(kickstage_dict["prop_dry_mass"]) * u.kg
        else: return None

    def get_kickstage_dispenser_dry_mass(self, kickstage_name):
        kickstage_dict = self.get_kickstage_dict(kickstage_name)
        if kickstage_dict is not None:
            return float(kickstage_dict["dispenser_dry_mass"]) * u.kg
        else: return None

    def get_kickstage_struct_mass(self, kickstage_name):
        kickstage_dict = self.get_kickstage_dict(kickstage_name)
        if kickstage_dict is not None:
            return float(kickstage_dict["struct_mass"]) * u.kg
        else: return None

    def get_kickstage_prop_type(self, kickstage_name):
        kickstage_dict = self.get_kickstage_dict(kickstage_name)
        if kickstage_dict is not None:
            return str(kickstage_dict["prop_type"])
        else: return None