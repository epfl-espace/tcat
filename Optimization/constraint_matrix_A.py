import numpy as np


def dimensions(m, n, steps):
    """Input:
    m: number of motherships
    n: number of debris considered in the linear programming problem
    steps: number of steps considered in the linear programming problem

    Return:
    tuple with a length equal to the number of indices characterizing
    the linear programming problem, the first element has a value equal
    to the number of motherships, all the other elements have a value
    equal to the number of debris considered
    """
    return (m,) + (n,) * steps


def filter_indices(m, n, steps, p):
    """Input:
    m: number of motherships
    n: number of debris considered in the linear programming problem
    steps: number of steps considered in the linear programming problem
    p: index of one of the n debris

    Return:
    list (with a length equal to the number of steps considered in the
    linear programming problem)
    of tuples (with a length equal to the number of indices
    characterizing the linear programming problem):
    [(:, p, :, :, :, ...), (:, :, p, :, :, ...),
    (:, :, :, p, :, ...), ..., (:, :, :, :, :, ..., p)]
    """

    l = len(dimensions(m, n, steps))
    a = []
    for i in range(1, l):
        t = l * [slice(None)]
        t[i] = p
        a.append(tuple(t))

    return a


def array_constraint_one_debris(F, a):
    """Input:
    F: array with a number of indices equal to the number of indices
    characterizing the linear programming problem
    a: list (with a length equal to the number of steps considered in
    the linear programming problem)
    of tuples (with a length equal to the number of indices
    characterizing the linear programming problem):
    [(:, p, :, :, :, ...), (:, :, p, :, :, ...),
    (:, :, :, p, :, ...), ..., (:, :, :, :, :, ..., p)]

    Return:
    array F modified
    """
    for i in range(0, F.ndim - 1):
        F[a[i]] += 1
    return F


def constraint_debris(m, n, steps):
    """Input:
    m: number of motherships
    n: number of debris considered in the linear programming problem
    steps: number of steps considered in the linear programming problem

    Return:
    array with two indices expressing the constraint that each debris
    can be captured once and only once
    """

    D = np.zeros((n, m * n ** steps))
    for p in range(n):
        F = np.zeros(dimensions(m, n, steps))
        a = filter_indices(m, n, steps, p)
        F = array_constraint_one_debris(F, a)
        b = F.flatten()
        D[p, :] = b

    return D


def constraint_mothership(m, n, steps):
    """Input:
    m: number of motherships
    n: number of debris considered in the linear programming problem
    steps: number of steps considered in the linear programming problem

    Return:
    array with two indices expressing the constraint that from each
    mothership one and only one path can leave
    """

    M = np.zeros((m, m * n ** steps))
    for i in range(m):
        E = np.zeros(dimensions(m, n, steps))
        E[i, ...] = 1
        b = E.flatten()
        M[i, :] = b
    return M


def lin_prog_matrix(m, n, steps):
    """Input:
    m: number of motherships
    n: number of debris considered in the linear programming problem
    steps: number of steps considered in the linear programming problem

    Return:
    array (with two indices) for the linear programming problem
    """

    D = constraint_debris(m, n, steps)
    M = constraint_mothership(m, n, steps)
    A = np.vstack([D, M])
    return A