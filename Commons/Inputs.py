from xlrd import open_workbook
from pathlib import Path


# from poliastro.twobody import Orbit
# from astropy.time import Time
# from astropy import units as u


class Inputs:
    def __init__(self, file_path=Path.cwd()/'Inputs.xls'):
        """
        Class containing all relevant inputs for the simulation

        :param file_path: full path of the input file (default is at same level as script)


        """
        self.file_path = file_path
        self.dict_list = list()

    def read_excel_sheet(self, sheet_name):
        """
        This function reads an excel file taking all the rows and columns available in a specific sheet.

        :return: A list of dictionaries that contains all the data relative to a specific row,
                keeping the correct header
        """

        book = open_workbook(self.file_path)
        sheet = book.sheet_by_name(sheet_name)

        # read header values into the list
        keys = [sheet.cell(1, col_index).value for col_index in range(sheet.ncols)]

        for row_index in range(2, sheet.nrows):
            d = {keys[col_index]: sheet.cell(row_index, col_index).value for col_index in range(sheet.ncols)}
            self.dict_list.append(d)

        return self.dict_list

    def call_item_from_reference(self, sheet_name, reference_header, reference_value, requested_data, verbose=False):
        """
        This function allows to call a specific cell of the excel file, knowing one of the related element in the
        input set.
        It takes only the first result.
        E.g. if I want to call a specific orbit in the sheet called "Orbits" and I know how that is called "low_orbit",
        I should use:

        call_item_from_reference("Orbits", "Name", "low_orbit", "Eccentricity")

        :param verbose: If True, print the whole selected row (bool)
        :param sheet_name: Name of the sheet in the excel input file
        :param reference_header: Name of the header relative to the known element
        :param reference_value: value of the known element
        :param requested_data: header of the requested data, relative to the known element
        :return: the requested data
        """
        self.read_excel_sheet(sheet_name)

        called_row = next((row for row in self.dict_list if row[reference_header] == reference_value))

        if verbose:
            print(f"The called row is: {called_row}")

        return called_row.get(requested_data)

    def call_set_from_reference(self, sheet_name, reference_header, reference_value, reference_header2=None, reference_value2=None):
        """
        This function allows to call a specific set of data from the excel file, knowing one of the related element
        in the input set.
        It takes only the first result.
        E.g. if I want to call a specific orbit in the sheet called "Orbits" and I know that is called "low_orbit",
        I should use:

        call_item_from_reference("Orbits", "Name", "low_orbit")

        :param sheet_name: Name of the sheet in the excel input file
        :param reference_header: Name of the header relative to the known element
        :param reference_value: value of the known element
        :return: the requested set data
        """
        self.read_excel_sheet(sheet_name)
        if reference_header2 is None and reference_value2 is None:
            called_row = next((row for row in self.dict_list if row[reference_header] == reference_value))
        else:
            called_row = next((row for row in self.dict_list if row[reference_header] == reference_value and row[reference_header2] == reference_value2 ))

        return called_row

    def list_element_in_a_row(self, sheet_name, reference_header):

        self.read_excel_sheet(sheet_name)

        elements = []
        for i in range(len(self.dict_list)):
            elements.append(self.dict_list[i].get(reference_header))

        return elements

    def list_element_in_a_row_if_attribute_is_present(self, sheet_name, reference_header, attribute, second_reference_header):

        self.read_excel_sheet(sheet_name)

        elements = []
        for i in range(len(self.dict_list)):
            if attribute in self.dict_list[i].get(second_reference_header):
                elements.append(self.dict_list[i].get(reference_header))

        return elements


# print(Inputs().list_element_in_a_row("Orbits", "Name"))
# In = Inputs().call_set_from_reference("Orbits", "Name", "lunar_transfer_orbit")
# print(In)
# orbit = [In[x] for x in (
#     "Main body", "Semi major axis [km]", "Eccentricity", "Inclination [deg]", "RAAN [deg]", "Arg. of perigee [deg]",
#     "True anomaly [deg]", "Epoch [YYYY-MM-DD hh:mm:ss]")]
# orbit[1] = orbit[1] * u.km
# orbit[2] = orbit[2] * u.one
# orbit[3] = orbit[3] * u.deg
# orbit[4] = orbit[4] * u.deg
# orbit[5] = orbit[5] * u.deg
# orbit[6] = orbit[6] * u.deg
# orbit[7] = Time(orbit[7], scale="tdb")
#
# print(orbit)

# print(Inputs().read_excel_sheet("Orbits"))
