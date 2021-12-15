from xlwt import Workbook, XFStyle
# from run_code import *
import subprocess
import os

wb = Workbook()

# Add the number format to make it compatible with excel
decimal_format = XFStyle()
decimal_format.num_format_str = '#,##0'
dec = decimal_format

def print_excel(temp_scenario, arch_no, load_mass):
    """
    This function creates an excel file with the relevant outputs from the computation.
    The file is structured in three sheets: Relevant Orbits, Mass and power for each subsystem,
    total mass and power of each servicer. It will create each of them for several cargo masses that are provided.
    """

    "Select the scenario"

    scenario = temp_scenario

    "-------------------------------"

    "Create the first sheet"

    # ws = wb.add_sheet(f'Arch {arch_no}, {load_mass} kg, Orbits', cell_overwrite_ok=True)
    #
    # row_nbr = 0
    #
    # for orbits in scenario.orbits:
    #     ws.row(row_nbr).write(0, f'{scenario.orbits[row_nbr]}')
    #     row_nbr += 1

    "Create the second sheet"

    ws = wb.add_sheet(f'Arch {arch_no}, {load_mass} kg, SubSys Mass', cell_overwrite_ok=True)

    row_nbr = 1
    for servicers in temp_scenario.fleet.servicers:
        for _, modules in temp_scenario.fleet.servicers[servicers].modules.items():
            ws.row(0).write(0, 'Servicers ID')
            ws.row(row_nbr).write(0, f'{temp_scenario.fleet.servicers[servicers].ID}')

            ws.row(0).write(1, 'Modules ID')
            ws.row(row_nbr).write(1, f'{modules.ID}')

            ws.row(0).write(2, 'Dry mass [kg]')
            ws.row(row_nbr).write(2, modules.get_dry_mass().value, dec)

            ws.row(0).write(3, 'Wet mass [kg]')
            ws.row(row_nbr).write(3, modules.get_wet_mass().value, dec)

            ws.row(0).write(4, 'Propellant mass [kg]')
            ws.row(row_nbr).write(4, (modules.get_wet_mass() - modules.get_dry_mass()).value, dec)

            ws.row(0).write(5, 'Reference power [W]')
            ws.row(row_nbr).write(5, modules.get_reference_power().value, dec)

            row_nbr += 1

    "Create the third sheet"

    ws = wb.add_sheet(f'Arch {arch_no}, {load_mass} kg, TOT Mass', cell_overwrite_ok=True)

    row_nbr = 1
    for servicers in temp_scenario.fleet.servicers:
        # NB: a global contingency is applied
        ws.row(0).write(0, 'Servicers ID')
        ws.row(row_nbr).write(0, f'{temp_scenario.fleet.servicers[servicers].ID}')

        ws.row(0).write(1, 'Dry mass [kg]')
        ws.row(row_nbr).write(1, temp_scenario.fleet.servicers[servicers].get_dry_mass().value, dec)

        ws.row(0).write(2, 'Wet mass [kg]')
        ws.row(row_nbr).write(2, temp_scenario.fleet.servicers[servicers].get_wet_mass().value, dec)

        ws.row(0).write(3, 'Propellant mass [kg]')
        ws.row(row_nbr).write(3, (temp_scenario.fleet.servicers[servicers].get_wet_mass() - temp_scenario.fleet.servicers[servicers].get_dry_mass()).value, dec)

        ws.row(0).write(4, 'Reference power [W]')
        ws.row(row_nbr).write(4, temp_scenario.fleet.servicers[servicers].get_reference_power().value, dec)

        row_nbr += 1


    # TODO: add global contigency and wet, dry , fuel mass

    "Save your spreadsheet"

    wb.save(f'TCAT output.xls')

"Automatically opens your spreadsheet (select the correct path)"
# os.startfile("C:\\Users\\Flavio\\PycharmProjects\\tcat\\Commons\\TCAT Outputs.xls")

# subprocess.call(['open', "/Users/romanjoye/PycharmProjects/tcat/Commons/TCAT Outputs architecture.xls"])