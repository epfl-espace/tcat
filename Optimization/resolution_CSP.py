from shuttle import *
import time
start_time = time.time()

# Load the pandas DataFrame containing the complete list of debris:
debris_df = load_dataframe("oneweb.txt", computed=True)

indices = np.array([0,1,2,3,4,5,6,7,8,9])
sd = selected_debris(debris_df, indices)

pop = population(sd, 2)

ts = np.linspace(0, 90 * 24 * 60 * 60, 18 * 10 * 60 + 1)

COE = COE_function_of_time(debris_df, indices, ts)
print("--- The COE took %s seconds ---" % (time.time() - start_time))
start_time = time.time()
print(COE)
times_pop_cost = time_optimization_of_deltaV_population(pop, COE)
print(times_pop_cost)
np.save('initial_population', times_pop_cost)

print("--- The initial population setting took %s seconds ---" % (time.time() - start_time))
solution = inver_over(times_pop_cost, COE, 0.08, generations=5)

print("--- The optimization setting took %s seconds ---" % (time.time() - start_time))
# print(solution)