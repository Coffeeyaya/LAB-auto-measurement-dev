import json
import os

def generate_optical_config(device_number, vg_on, wavelength=660, power=100.0, output_dir="config/time_pulse_queue", **kwargs):
    """
    Generates a JSON configuration file for Laser + Servo Time-Dependent measurements.
    """
    # 1. Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # 2. Define the baseline template based on your provided JSON
    config = {
        "hardware_mode": "Laser + Servo",
        "electrical_mode": "Pulsed Vg Train",
        "description": "Time-Dep",
        "device_number": str(device_number),
        "run_number": "1",
        "wait_time": 10,
        "current_limit_a": 0.001,
        "current_limit_b": 0.001,
        "current_range_a": 1e-07,
        "current_range_b": 1e-07,
        "nplc_a": 1.0,
        "nplc_b": 1.0,
        "vd_const": 1.0,
        "vg_on": float(vg_on),
        "vg_off": 0.0,
        "cycle_number": 5,
        "duration_1": 2.0,
        "duration_2": 2.0,
        "base_vg": 0.0,
        "pulse_width": 0.001,
        "rest_time": 0.3,
        
        # --- Optical & Servo Specifics ---
        "wavelength_arr": [int(wavelength)],
        "channel_arr": [6], # Defaulting to 6, overwrite via kwargs if needed
        "power_arr": [float(power)],
        "on_off_number": 1,
        "servo_time_on": 1.0,
        "servo_time_off": 3.0
    }
    
    # 3. Overwrite any additional parameters passed via kwargs
    config.update(kwargs)
    
    # 4. Create a clean, sequenced filename
    existing_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
    next_idx = len(existing_files) + 1
    
    # Example: 01_LaserServo_PulsedVgTrain_Dev6-7_Vg0.5V_660nm_100nW.json
    hw_prefix = config["hardware_mode"].replace(" ", "").replace("+", "")
    elec_prefix = config["electrical_mode"].replace(" ", "")
    
    # Extract scalar values from arrays for a clean filename
    wl = config["wavelength_arr"][0]
    pwr = config["power_arr"][0]
    
    filename = f"{next_idx:02d}_{hw_prefix}_{elec_prefix}_Dev{device_number}_Vg{config['vg_on']}V_{wl}nm_{pwr}nW.json"
    full_path = os.path.join(output_dir, filename)
    
    # 5. Save the dictionary as a formatted JSON file
    with open(full_path, 'w') as f:
        json.dump(config, f, indent=4)
        
    print(f"✅ Generated: {filename}")
    return full_path

# ==========================================
# POWERFUL USAGE EXAMPLES
# ==========================================
if __name__ == "__main__":
    
    # print("--- 1. Generating a Single Light Config ---")
    # generate_optical_config(device_number="6-7", vg_on=0.5, wavelength=660, power=100.0)
    
    # print("\n--- 2. Batch Sweeping Laser Power ---")
    power_test_points = [25, 50, 100, 200, 400]
    vg_test_points = [0.2, 0.4 , 0.6, 0.8, 1.0]
    counter = 0
    for i, vg_on in enumerate(vg_test_points):
        for j, pwr in enumerate(power_test_points):
        # Notice we can still use kwargs to alter the cycle number and timings!
            generate_optical_config(
                device_number="6-7", 
                run_number=counter, 
                vg_on=vg_on, 
                power=pwr, 
                cycle_number=5, 
                servo_time_on=1.0,
                servo_time_off=3.0
            )
            counter += 1
        
    # print("\n--- 3. Batch Sweeping Multiple Wavelengths ---")
    # # Say 532nm uses channel 2, and 660nm uses channel 6
    # lasers = [
    #     {"wl": 532, "ch": 2},
    #     {"wl": 660, "ch": 6}
    # ]
    
    # for laser in lasers:
    #     generate_optical_config(
    #         device_number="6-7", 
    #         vg_on=1.0, 
    #         wavelength=laser["wl"], 
    #         channel_arr=[laser["ch"]], # We override the default channel_arr here!
    #         power=50.0
    #     )