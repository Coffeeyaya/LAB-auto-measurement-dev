import pyvisa
import time
import numpy as np
import matplotlib.pyplot as plt


def zero_sensor(meter):
    print("Zeroing sensor... Make sure beam is blocked.")
    
    meter.write('sense:correction:collect:zero')
    meter.query('*opc?')  # wait until operation complete
    print("Zeroing complete.")

def measure_power(
    wavelength=660,
    average_count=10,
    measure_interval=0.2,
    num_points=10
):
    """
    Continuous power measurement using Thorlabs PM100D.

    Parameters
    ----------
    wavelength : float
        Wavelength in nm.
    average_count : int
        Averaging count for smoothing.
    measure_interval : float
        Delay between measurements (seconds).
    num_points : int
        Number of data points to acquire.

    Returns
    -------
    time_array : np.ndarray
        Relative time array (seconds).
    power_array : np.ndarray
        Measured power array (Watts).
    """

    rm = pyvisa.ResourceManager()
    res = rm.list_resources('USB?*::0x1313::0x8078::?*::INSTR')

    if not res:
        raise Exception("PM100D not found")

    meter = rm.open_resource(res[0])
    meter.read_termination = '\n'
    meter.write_termination = '\n'
    meter.timeout = 2000

    # Configure meter
    meter.write('sense:power:unit W')
    meter.write('sense:power:range:auto 1')
    meter.write(f'sense:average:count {average_count}')
    meter.write('configure:power')
    meter.write(f'sense:correction:wavelength {wavelength}')


    # zero
    zero_sensor(meter)

    print('turn on the light')

    time_array = np.zeros(num_points)
    power_array = np.zeros(num_points)

    t0 = time.perf_counter()

    try:
        for i in range(num_points):
            power = meter.query_ascii_values('read?')[0]
            t = time.perf_counter() - t0

            time_array[i] = t
            power_array[i] = power

            if i < num_points - 1:
                time.sleep(measure_interval)

    finally:
        meter.close()
        rm.close()

    return time_array, power_array


if __name__ == "__main__":
    t, p = measure_power(
    wavelength=660,
    average_count=20,
    measure_interval=0.2,
    num_points=10
    )

    print(t)
    print(p)
    plt.figure()
    plt.plot(t, p)
    plt.xlabel("Time (s)")
    plt.ylabel("Power (W)")
    plt.title("PM100D Power vs Time")
    plt.grid(True)
    plt.show()