import numpy as np
import matplotlib.pyplot as plt

def log_spaced_powers(P_min, P_max, N_points):
    powers = P_min * (P_max / P_min) ** (np.arange(N_points) / (N_points - 1))
    return powers
def test_function(string):
    print(string)

# Example usage:
# powers = log_spaced_powers(10, 300, 7)
# print(powers)
# plt.scatter(powers, powers)
# plt.xscale('log')
# plt.yscale('log')
# plt.show()
test_function("str")

