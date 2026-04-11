import json
import os
import copy

def generate_from_base(base_dict, output_dir="config/time_pulse_queue", **kwargs):
    """
    Safely clones a base dictionary, updates parameters (including nested ones), 
    and saves it sequentially.
    """
    config = copy.deepcopy(base_dict)
    os.makedirs(output_dir, exist_ok=True)
    
    # --- THE MAGIC NESTED INTERCEPTOR ---
    for key, value in kwargs.items():
        # If the user wants to change the laser power...
        if key == "laser_power":
            # Ensure laser_settings exists in the base config first
            if "laser_settings" in config and config["laser_settings"] is not None:
                config["laser_settings"]["power"] = value
            else:
                print("Warning: Tried to update laser power, but no laser_settings found in base config!")
        
        # If the user wants to change the laser wavelength...
        elif key == "laser_wavelength":
            if "laser_settings" in config and config["laser_settings"] is not None:
                config["laser_settings"]["wavelength"] = value
                
        # Normal top-level variables (vd_const, vg_on, wait_time, etc.)
        else:
            config[key] = value
    # ------------------------------------
    
    # Count existing files to increment prefix
    existing_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
    next_idx = len(existing_files) + 1
    
    # Build a dynamic filename
    hw_prefix = config.get("hardware_mode", "Device").replace(" ", "").replace("+", "")
    elec_prefix = config.get("electrical_mode", "Mode").replace(" ", "")
    device = config.get("device_number", "X")
    
    changed_params_str = "_".join([f"{k}-{str(v).replace('.', 'p')}" for k, v in kwargs.items()])
    if not changed_params_str: changed_params_str = "base_copy"
        
    filename = f"{next_idx:02d}_{hw_prefix}_{elec_prefix}_Dev{device}_{changed_params_str}.json"
    full_path = os.path.join(output_dir, filename)
    
    with open(full_path, 'w') as f:
        json.dump(config, f, indent=4)
        
    print(f"✅ Generated: {filename}")
    return full_path

# ==========================================
# HOW TO USE IT
# ==========================================
if __name__ == "__main__":
    
    # BASE_TEMPLATE_PATH = "config/base_file/02_pulse_.json"
    BASE_TEMPLATE_PATH = "/Users/tsaiyunchen/Desktop/lab/master/measurement_dev/measure/config/base_file/01_LaserServo_PulsedVgTrain_.json"

    try:
        with open(BASE_TEMPLATE_PATH, 'r') as f:
            base_config = json.load(f)
    except FileNotFoundError:
        print(f"❌ Could not find {BASE_TEMPLATE_PATH}.")
        exit()
    
    # power_test_points = [25, 50, 100, 200, 400]
    
    # for i,pwr in enumerate(power_test_points):
    #     generate_from_base(
    #         base_dict=base_config, 
    #         output_dir="config/idvg_pulse_queue",
    #         run_number=i + 2,
    #         # Use our custom keyword to trigger the interceptor!
    #         laser_power=pwr, 
    #     )

    
    power_test_points = [25, 50, 100, 200, 400]
    
    for i,pwr in enumerate(power_test_points):
        generate_from_base(
            base_dict=base_config, 
            output_dir="config/time_pulse_queue",
            run_number=i + 2,
            # Use our custom keyword to trigger the interceptor!
            power_arr=pwr, 
        )