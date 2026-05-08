import time
import numpy as np
import matplotlib.pyplot as plt
from pm.power import PowerMeter
from LabAuto.laser_remote import LaserController

def measure_transient_power(laser, pm, channel, wavelength, power_percentages, duration=5.0, interval=0.5):
    """
    Sweeps through a list of power percentages, recording the power meter reading
    as a function of time immediately after the laser is toggled ON.
    """
    num_points = int(duration / interval)
    results = {}
    
    # 1. Config Meter for FAST measurement (No internal averaging)
    # This ensures we see the true transient response, not the meter's smoothing filter.
    pm.config_meter(wavelength, average_count=1) 
    pm.zero_sensor()
    
    # 2. Pre-set the laser wavelength once
    channel_str = str(channel)
    laser.send_cmd({"channel": channel_str, "wavelength": str(wavelength)}, wait_for_reply=True)
    time.sleep(1)

    for pp in power_percentages:
        print(f"Testing Power Percentage: {pp}%")
        
        # 3. Set the target power slider (while light is currently OFF)
        laser.send_cmd({"channel": channel_str, "power": str(pp)}, wait_for_reply=True)
        time.sleep(1) # Give the GUI a second to register the slider change
        
        # 4. Toggle ON and IMMEDIATELY start the power meter loop
        laser.send_cmd({"channel": channel_str, "on": 1}, wait_for_reply=True)
        t_array, p_array = pm.measure_power(measure_interval=interval, num_points=num_points)
        
        # 5. Toggle OFF
        laser.send_cmd({"channel": channel_str, "on": 1}, wait_for_reply=True)
        
        # 6. Store data (Convert to nW for easier reading later)
        results[pp] = {
            'time': t_array,
            'power_nw': p_array * 1e9 
        }
        
        # Allow the sensor to cool/zero out before the next PP test
        time.sleep(2)
        
    return results

def plot_hardware_characteristics(results):
    """
    Generates a 1x2 subplot showing both the time-domain rise and the steady-state non-linearity.
    """
    plt.figure(figsize=(14, 6))
    
    # --- Plot 1: Transient Response (Power vs Time) ---
    plt.subplot(1, 2, 1)
    saturation_powers = []
    pps = []
    
    for pp, data in results.items():
        t = data['time']
        p = data['power_nw'] 
        
        plt.plot(t, p, marker='o', linestyle='-', label=f'PP = {pp}%')
        
        # Calculate saturation power (mean of the last 3 data points)
        sat_p = np.mean(p[-3:])
        saturation_powers.append(sat_p)
        pps.append(pp)

    plt.xlabel("Time (s)")
    plt.ylabel("Measured Power (nW)")
    plt.title("Transient Power Response (Turn-On Delay)")
    plt.legend()
    plt.grid(True)

    # --- Plot 2: Saturation Power vs Power Percentage ---
    plt.subplot(1, 2, 2)
    plt.plot(pps, saturation_powers, 'r-o', linewidth=2, markersize=8)
    plt.xlabel("AOTF Power Percentage (%)")
    plt.ylabel("Saturation Power (nW)")
    plt.title("Steady-State Power vs. PP Input (Non-Linearity)")
    plt.grid(True)
    
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    LIGHT_IP = "10.0.0.2" 
    
    print("Initializing Hardware...")
    laser = LaserController(LIGHT_IP, 5001)
    pm = PowerMeter()
    
    try:
        # Experiment Parameters
        CHANNEL = 6
        WAVELENGTH = 660
        PP_LIST = [10, 20, 30, 40, 50]
        
        # Run Measurement
        transient_data = measure_transient_power(
            laser=laser, 
            pm=pm, 
            channel=CHANNEL, 
            wavelength=WAVELENGTH, 
            power_percentages=PP_LIST,
            duration=5.0,     # Measure for 5 seconds
            interval=0.5      # Time resolution of 0.5s
        )
        
        # Visualize
        plot_hardware_characteristics(transient_data)
        
    finally:
        print("Closing hardware connections...")
        laser.close()
        pm.close_meter()