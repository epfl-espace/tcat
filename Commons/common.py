import os  # used to interact with system files
import pickle  # used to save and load large amount of data to binary files
from astropy import units as u

""" This file contains a few generic functions used to:
    - display a progress bar
    - make conversion of monetary units (not available in otherwise astropy units package)
    - load binary files"""


def print_progress_bar(current_iteration, total_iterations, prefix='', suffix='', decimals=1, length=100, fill='█'):
    """ Call in a loop to create terminal progress bar.

    Args:
        current_iteration (int): current iteration
        total_iterations (int): total iterations
        prefix (str): (optional) prefix string
        suffix (str): (optional) suffix string
        decimals (int): (optional) positive number of decimals in percent complete
        length (int): (optional) character length of bar
        fill (str): (optional) bar fill character
    """
    # prepare line to print
    percent = ("{0:." + str(decimals) + "f}").format(100 * (current_iteration / float(total_iterations)))
    filledlength = int(length * current_iteration // total_iterations)
    bar = fill * filledlength + '-' * (length - filledlength)

    # print line
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end='')
    if current_iteration == total_iterations:
        print()


def usd_to_euro(usd_amount):
    """ Return usd ($) amount converted from euro amount."""
    # TODO: implement monetary units as astropy.units custom units instead
    return usd_amount * 0.89


def load_file(folder_name, file_name):
    """ Return data loaded from file saved in binary form (pickled).

    Args:
        folder_name (str): name of folder containing file (relative to execution path)
        file_name (str): name of the file as a string
    """
    os.chdir(folder_name)
    dbfile = open(file_name, 'rb')
    data = pickle.load(dbfile)
    dbfile.close()
    print('Loaded : ' + file_name + ' in ' + folder_name)
    os.chdir('..')

    return data


def load_latest_file(folder_name, file_name_start):
    """ Return data loaded from latest file saved in binary form (pickled).
    Get latest version of a file based on start of file name.

    Args:
        folder_name (str): name of folder containing file (relatively from execution path)
        file_name_start (str): string used to filter files by the start of their name
    """
    # Find newest file with name matching file name start
    os.chdir(folder_name)
    filtered_files = [fn for fn in os.listdir(os.getcwd()) if fn[:len(file_name_start)] == file_name_start]
    ordered_files = sorted(filtered_files, key=os.path.getmtime)
    newest_file_name = ordered_files[-1]
    os.chdir('..')

    # load file
    data = load_file(folder_name, newest_file_name)

    return data

def convert_time_for_print(dt):
    """ Returns the time in the lowest unit with decimal > 0.
    Typ:    dt = 135s --> returns: 2.25 minute
            dt = 3600s --> returns: 1 hour
    Args:
        dt (u.sec, u.minute, u.day, etc...): duration to covert in a printable unit
    """
    if dt > 30. * u.day:
        dt = dt.to(u.year)
    elif dt > 1. * u.day:
        dt = dt.to(u.day)
    elif dt > 1 * u.minute:
        dt = dt.to(u.minute)
    elif dt > 1 * u.s:
        dt = dt.to(u.s)
    else:
        dt = dt.to(u.ms)
    return dt