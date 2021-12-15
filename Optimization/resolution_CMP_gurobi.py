from constraint_matrix_A import *
from orbital_manoeuvres import *
from cost_vector import *
import gurobipy as gp
from gurobipy import *
import scipy.sparse as sp
import time
start_time = time.time()


def resolve_CMP(n, m, parking_orbit, debris_df):
    steps = int(n / m)
    A = lin_prog_matrix(m, n, steps)
    b = np.ones(n+m)
    c = cost_vector(debris_df, m, n, steps, park_orb=parking_orbit)


    # Resolution of the CMP:
    model = Model("CMP")

    A = np.matrix(A)

    x = model.addMVar(shape=m*n**steps, name='x', vtype="B")
    model.setObjective(c @ x, GRB.MINIMIZE)

    model.addConstr(A @ x == b, "cons1")
    model.addConstr(x >= 0, "cons2")

    print("--- The optimization setting took %s seconds ---" % (time.time() - start_time))

    model.optimize()

    print(x.X)
    print(model.objVal)
    # print(model.getVars())


    def extract_solution(m, n, steps, sol):
        T_sol = sol.reshape(dimensions(m, n, steps))
        w = np.where(T_sol == 1)
        return [[w[j][i] for j in range(steps + 1)] for i in range(m)]

    def extract_solutionVal(m, n, steps, sol):
        sol = sol.reshape(m*n**steps)
        v = np.where(sol == 1)
        return np.take(c, v).tolist()[0]


    extr_sol = extract_solution(m, n, steps, x.X)
    extr_solVal = extract_solutionVal(m, n, steps, x.X)
    return print(extr_sol, extr_solVal)


n = 18
m = 3
parking_orbit = 300


# Load the pandas DataFrame of the debris to be removed:
debris_df = load_dataframe("oneweb.txt", computed=True)
resolve_CMP(n, m, parking_orbit, debris_df)