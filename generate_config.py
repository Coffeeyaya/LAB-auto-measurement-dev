import json
import os

def generate_time_dep_config(device_number, vg_on, output_dir="config/time_pulse_queue", **kwargs):
    """
    Generates a JSON configuration file for Time-Dependent measurements.
    """
    # 1. Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # 2. Define the baseline template (using your provided JSON)
    config = {
        "hardware_mode": "Dark Current",
        "electrical_mode": "Pulsed Vg Train",
        "description": "Time-Dep",
        "device_number": str(device_number), # Ensured as string
        "run_number": "1",
        "wait_time": 0,
        "current_limit_a": 0.001,
        "current_limit_b": 0.001,
        "current_range_a": 1e-07,
        "current_range_b": 1e-07,
        "nplc_a": 1.0,
        "nplc_b": 1.0,
        "vd_const": 1.0,
        "vg_on": float(vg_on),               # Ensured as float
        "vg_off": 0.0,
        "cycle_number": 5,
        "duration_1": 2.0,
        "duration_2": 2.0,
        "base_vg": 0.0,
        "pulse_width": 0.001,
        "rest_time": 0.3
    }
    
    # 3. Overwrite any additional parameters passed via kwargs
    config.update(kwargs)
    
    # 4. Create a clean, sequenced filename
    # Count existing files to automatically increment the prefix index
    existing_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
    next_idx = len(existing_files) + 1
    
    # Example filename: 01_DarkCurrent_PulsedVgTrain_Dev1-1_Vg1.0V.json
    hw_prefix = config["hardware_mode"].replace(" ", "")
    elec_prefix = config["electrical_mode"].replace(" ", "")
    filename = f"{next_idx:02d}_{hw_prefix}_{elec_prefix}_Dev{device_number}_Vg{vg_on}V.json"
    
    full_path = os.path.join(output_dir, filename)
    
    # 5. Save the dictionary as a formatted JSON file
    with open(full_path, 'w') as f:
        json.dump(config, f, indent=4)
        
    print(f"✅ Generated: {filename}")
    return full_path

# ==========================================
# USAGE EXAMPLES
# ==========================================
if __name__ == "__main__":
    
    # Example 1: Generate a single file
    # generate_time_dep_config(device_number="6-7", vg_on=1.5)
    
    # Example 2: Use kwargs to override other defaults (like run_number or cycle_number)
    # generate_time_dep_config(device_number="1-2", vg_on=2.0, run_number="2", cycle_number=10)
    
    # Example 3: Batch generate a sequence of Vg_ON voltages!
    print("\n--- Generating Batch Sequence ---")
    vg_test_points = [0.2, 0.4, 0.6, 0.8, 1.0]
    
    for idx, vg in enumerate(vg_test_points):
        generate_time_dep_config(device_number="6-7", vg_on=vg, run_number=idx)