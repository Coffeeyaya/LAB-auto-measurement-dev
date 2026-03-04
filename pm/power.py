import pyvisa
import time
import numpy as np
import matplotlib.pyplot as plt

class PowerMeter():
    def __init__(self):
        self.rm = pyvisa.ResourceManager()
        res = self.rm.list_resources('USB?*::0x1313::0x8078::?*::INSTR')

        if not res:
            raise Exception("PM100D not found")

        self.meter = self.rm.open_resource(res[0])
        self.meter.read_termination = '\n'
        self.meter.write_termination = '\n'
        self.meter.timeout = 2000

        self.meter.write('sense:power:unit W')
        self.meter.write('sense:power:range:auto 1')
        
    def config_meter(self, wavelength, average_count):
        """
        wavelength : float, Wavelength in nm
        average_count : int, Averaging count for smoothing
        """
        self.meter.write(f'sense:average:count {average_count}')
        self.meter.write('configure:power')
        self.meter.write(f'sense:correction:wavelength {wavelength}')

    def zero_sensor(self):
        print("Zeroing sensor... Make sure beam is blocked.")
        
        self.meter.write('sense:correction:collect:zero')
        self.meter.query('*opc?')  # wait until operation complete
        print("Zeroing complete.")

    def measure_power(self, measure_interval=0.2, num_points=10):
        time_array = np.zeros(num_points)
        power_array = np.zeros(num_points)

        t0 = time.perf_counter()
        
        for i in range(num_points):
            power = float(self.meter.query('measure:power?'))
            t = time.perf_counter() - t0

            time_array[i] = t
            power_array[i] = power

            if i < num_points - 1:
                time.sleep(measure_interval)

        return time_array, power_array
    
    def close_meter(self):
        self.meter.close()
        self.rm.close()

        


if __name__ == "__main__":

    wavelength=660
    average_count=20

    pm = PowerMeter()
    pm.config_meter(wavelength, average_count)
    pm.zero_sensor()
    t, p = pm.measure_power(measure_interval=0.2, num_points=10)

    try:
        pm.config_meter(wavelength, average_count)
        pm.zero_sensor()
        t, p = pm.measure_power(measure_interval=0.2, num_points=10)

        plt.figure()
        plt.plot(t, p)
        plt.xlabel("Time (s)")
        plt.ylabel("Power (W)")
        plt.title("PM100D Power vs Time")
        plt.grid(True)
        plt.show()

    finally:
        pm.close_meter()