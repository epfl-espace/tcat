from constraint_matrix_A import *
from orbital_manoeuvres import *
from tletools import load_dataframe
from itertools import product
import pandas as pd
import numpy as np


def debris_table(*args):
    """Input:
    *args: any number of dataframe of this type:
    df1 = load_dataframe(filename of a file containing multiple
    TLEs, computed=True)
    df2 = load_dataframe(filename of a file containing multiple
    TLEs, computed=True)
    ...
    
    Return:
    dataframe (sorted by 'norad') containing all uploaded data
    """

    df = pd.concat(args)
    # Sort dataframes by norads:
    df.sort_values('norad', inplace=True)
    # Create new indices for the updated dataframe:
    df.reset_index(drop=True, inplace=True)
    return df


def debris_parameters(df):
    """Input:
    df: dataframe
    
    Return:
    dataframe containing only some parameters
    """

    return df[[
        'norad', 'name', 'a', 'ecc', 'inc', 'raan', 'argp', 'nu',
        'epoch'
    ]]


def orbits(df):
    """Input:
    df: dataframe
    
    Return:
    list (with a length equal to the number of indices in the dataframe)
    of dictionaries containing the orbital parameters, name and norad
    associated to a certain index in the dataframe
    """

    return [
        {
            'norad': df.loc[i, 'norad'],
            'name': df.loc[i, 'name'],
            'a': df.loc[i, 'a'],
            'ecc': df.loc[i, 'ecc'],
            'epoch': df.loc[i, 'epoch'],
            'inc': np.deg2rad(df.loc[i, 'inc']),
            'raan': np.deg2rad(df.loc[i, 'raan']),
            'argp': np.deg2rad(df.loc[i, 'argp']),
            'nu': np.deg2rad(df.loc[i, 'nu']),
            'Index': i
        } for i in df.index
    ]


def delta_V(o1, o2):
    """Input:
    o1: dictionary containing the orbital parameters of a first
    circular orbit
    o2: dictionary containing the orbital parameters of a second
    circular orbit
    
    Return:
    delta-V necessary for the transfer beetween the circular departure
    orbit (o1) and the circular arrival orbit (o2) with a
    Generalized Bielliptical Transfer plus
    delta-V necessary for the rephasing rendez-vous in km/s
    """

    theta = theta_angle(o1["raan"], o1["inc"], o2["raan"], o2["inc"])
    return delta_V_tot_GBT_optimal(o1["a"], o2["a"], theta
                                   )[0] + delta_V_same_orbit_optimal(
        o2["a"],
        lambda_angle=np.pi,
        trv_max=45 * 24 * 60 * 60,
        h_min=200
    )[0]


def delta_V_matrix(df):
    """Input:
    df: dataframe
    
    Return:
    array (matrix) containing all the delta-Vs between each couple of
    elements (with certain indices in the dataframe)
    """
    # it doesn't take in account the evolution of the orbit parameters during time. It is not dynamic.
    os = orbits(df)
    C = np.empty((len(df.index), len(df.index)))
    for i in df.index:
        for j in df.index:
            C[os[i]['Index'], os[j]['Index']] = delta_V(os[i], os[j])
    return C


def delta_V_matrix_motherships_debris(m, df):
    os = orbits(df)
    B = np.zeros(m, len(df.index))
    for i in range(m):
        for j in df.index:
            B[i, os[j]['Index']] = delta_V_tot_HT(R_earth, os[j]['a'])
    return B


def delta_V_motherships_debris(df, park_orb=300):
    """Input:
    df: dataframe
    park_orb: altitude of the parking orbit in km

    Return:
    array (vector) containing the delta-Vs necessary for a mothership
    leaving from the parking orbit to reach each element with a certain
    index in the dataframe
    """

    os = orbits(df)
    departure_dv = np.empty(len(df.index))
    for j in df.index:
        departure_dv[os[j]['Index']
        ] = delta_V_tot_HT(R_earth + park_orb, os[j]['a'])
    return departure_dv


def cost_vector(df, m, n, steps, park_orb=300):
    """Input:
    df: dataframe
    m: number of motherships
    n: number of debris considered in the linear programming problem
    steps: number of steps considered in the linear programming problem
    park_orb: altitude of the parking orbit in km

    Return:
    cost vector for the linear programming problem
    """

    # Array (matrix) containing all the delta-Vs between each couple
    # of debris:
    C = delta_V_matrix(df)
    # Array (vector) containing the delta-Vs necessary for a mothership
    # leaving from the parking orbit to reach each debris:
    departure_dv = delta_V_motherships_debris(df, park_orb=park_orb)
    G = np.empty(dimensions(m, n, steps))
    t = (range(m),) + (range(n),) * steps
    for i in product(*t):
        G[i] = departure_dv[i[1]] + sum(
            C[i[j], i[j + 1]] for j in range(1, len(i) - 1)
        )
    return G.flatten()
