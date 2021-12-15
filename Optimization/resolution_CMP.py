from constraint_matrix_A import *
from orbital_manoeuvres import *
from cost_vector import *
from cylp.cy import CyClpSimplex
from cylp.py.modeling.CyLPModel import CyLPModel, CyLPArray

n = int(4)
m = int(2)
steps = int(n / m)

# Load the pandas DataFrame of the debris to be removed:
debris_df = load_dataframe("starlink.txt", computed=True)

A = lin_prog_matrix(m, n, steps)
b = np.ones((n+m, 1))
c = cost_vector(debris_df, m, n, steps)

# Resolution of the CMP:
model = CyLPModel()

A = np.matrix(A)
b = CyLPArray(b)
c = CyLPArray(c)

x = model.addVariable('x', m * n ** steps, isInt=True)

model.objective = c * x

model.addConstraint(A * x == b)
model.addConstraint(x >= 0)

s = CyClpSimplex(model)
cbcModel = s.getCbcModel()
# cbcModel.branchAndBound()

solution = cbcModel.primalVariableSolution['x']
opt_value = cbcModel.objectiveValue
print(solution)
print(opt_value)

def extract_solution(m, n, steps, sol):
    T_sol = sol.reshape(dimensions(m, n, steps))
    w = np.where(T_sol == 1)
    return [[w[j][i] for j in range(steps + 1)] for i in range(m)]


extr_sol = extract_solution(m, n, steps, solution)