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
    """ Helper for reading .csv Kickstage database.
    Create an object by providing .csv file and then call the diffferent getters providing a kicktage name.
    If the Kickstage doesn't exist, return values of getters are None.
    """
    def __init__(self,kickstage_db_csv_file):
        self.kickstage_list = []
        self.read_csv_db_to_list(kickstage_db_csv_file)

    def read_csv_db_to_list(self,kickstage_db_csv_file):
        """ Opens the .csv file of the .db, reads it and stores it into a dict.

        :param kickstage_db_csv_file: path and filename of the database.
        :type kickstage_db_csv_file: str
        """
        with open(kickstage_db_csv_file, 'r') as data:
            self.kickstage_list = list(csv.DictReader(data))

    def get_kickstage_dict(self, kickstage_name):
        """ Retrieves the dictionnary containing all data of a single kickstage.

        :param kickstage_name: name of the kickstage to access
        :type kickstage_name: str
        :return: dictionnary with all data of the specified kickstage
        :rtype: dict
        """
        for kickstage_dict in self.kickstage_list:
            if kickstage_dict["name"] == kickstage_name:
                return kickstage_dict
        return None

    def get_kickstage_height(self, kickstage_name):
        """
        :param kickstage_name: name of the kickstage to access
        :type kickstage_name: str
        :return: height of the kickstage in m
        :rtype: float
        """
        kickstage_dict = self.get_kickstage_dict(kickstage_name)
        if kickstage_dict is not None:
            return float(kickstage_dict["height"]) * u.m
        else: return None

    def get_kickstage_diameter(self, kickstage_name):
        """
        :param kickstage_name: name of the kickstage to access
        :type kickstage_name: str
        :return: diameter of the kickstage in m
        :rtype: float
        """
        kickstage_dict = self.get_kickstage_dict(kickstage_name)
        if kickstage_dict is not None:
            return float(kickstage_dict["diameter"]) * u.m
        else: return None

    def get_kickstage_initial_fuel_mass(self, kickstage_name):
        """
        :param kickstage_name: name of the kickstage to access
        :type kickstage_name: str
        :return: initial fuel mass of the kickstage in kg
        :rtype: float
        """
        kickstage_dict = self.get_kickstage_dict(kickstage_name)
        if kickstage_dict is not None:
            return float(kickstage_dict["initial_fuel_mass"]) * u.kg
        else: return None

    def get_kickstage_prop_thrust(self, kickstage_name):
        """
        :param kickstage_name: name of the kickstage to access
        :type kickstage_name: str
        :return: thrust in N
        :rtype: float
        """
        kickstage_dict = self.get_kickstage_dict(kickstage_name)
        if kickstage_dict is not None:
            return float(kickstage_dict["prop_thrust"]) * u.N
        else: return None

    def get_kickstage_prop_isp(self, kickstage_name):
        """
        :param kickstage_name: name of the kickstage to access
        :type kickstage_name: str
        :return: isp of the kickstage propulsion in s
        :rtype: float
        """
        kickstage_dict = self.get_kickstage_dict(kickstage_name)
        if kickstage_dict is not None:
            return float(kickstage_dict["prop_isp"]) * u.s
        else: return None

    def get_kickstage_prop_dry_mass(self, kickstage_name):
        """
        :param kickstage_name: name of the kickstage to access
        :type kickstage_name: str
        :return: propulsion module's dry mass in kg
        :rtype: float
        """
        kickstage_dict = self.get_kickstage_dict(kickstage_name)
        if kickstage_dict is not None:
            return float(kickstage_dict["prop_dry_mass"]) * u.kg
        else: return None

    def get_kickstage_dispenser_dry_mass(self, kickstage_name):
        """
        :param kickstage_name: name of the kickstage to access
        :type kickstage_name: str
        :return: dispenser's dry mass in kg
        :rtype: float
        """
        kickstage_dict = self.get_kickstage_dict(kickstage_name)
        if kickstage_dict is not None:
            return float(kickstage_dict["dispenser_dry_mass"]) * u.kg
        else: return None

    def get_kickstage_struct_mass(self, kickstage_name):
        """
        :param kickstage_name: name of the kickstage to access
        :type kickstage_name: str
        :return: structure's dry mass of the kickstage in kg
        :rtype: float
        """
        kickstage_dict = self.get_kickstage_dict(kickstage_name)
        if kickstage_dict is not None:
            return float(kickstage_dict["struct_mass"]) * u.kg
        else: return None

    def get_kickstage_prop_type(self, kickstage_name):
        """
        :param kickstage_name: name of the kickstage to access
        :type kickstage_name: str
        :return: propulsion type of the kickstage
        :rtype: str
        """
        kickstage_dict = self.get_kickstage_dict(kickstage_name)
        if kickstage_dict is not None:
            return str(kickstage_dict["prop_type"])
        else: return None