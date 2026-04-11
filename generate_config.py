import json
import os
import copy

def generate_from_base(base_dict, output_dir="config/time_pulse_queue", **kwargs):
    """
    Safely clones a base dictionary, updates parameters using kwargs, 
    and saves it sequentially to the output directory.
    """
    # 1. PREVENT THE COPY ISSUE: Create an isolated clone of the base dictionary
    config = copy.deepcopy(base_dict)
    
    # 2. Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # 3. Overwrite parameters with whatever you passed in the loop (e.g., vg_on=0.5)
    config.update(kwargs)
    
    # 4. Count existing files to automatically increment the prefix index
    existing_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
    next_idx = len(existing_files) + 1
    
    # 5. Build a dynamic filename based on what was changed
    hw_prefix = config.get("hardware_mode", "Device").replace(" ", "").replace("+", "")
    elec_prefix = config.get("electrical_mode", "Mode").replace(" ", "")
    device = config.get("device_number", "X")
    
    # Create a suffix out of the kwargs you changed so the filename tells you exactly what is inside
    # e.g., "vg_on-0.5_pulse_width-0.01"
    changed_params_str = "_".join([f"{k}-{str(v).replace('.', 'p')}" for k, v in kwargs.items()])
    if not changed_params_str:
        changed_params_str = "base_copy"
        
    filename = f"{next_idx:02d}_{hw_prefix}_{elec_prefix}_Dev{device}_{changed_params_str}.json"
    full_path = os.path.join(output_dir, filename)
    
    # 6. Save the dictionary as a formatted JSON file
    with open(full_path, 'w') as f:
        json.dump(config, f, indent=4)
        
    print(f"✅ Generated: {filename}")
    return full_path

# ==========================================
# USAGE EXAMPLES (YOUR CUSTOM FOR-LOOPS)
# ==========================================
if __name__ == "__main__":
    
    # A. Define where your base template is located
    BASE_TEMPLATE_PATH = "/Users/tsaiyunchen/Desktop/lab/master/measurement_dev/measure/config/base_file/01_LaserServo_PulsedVgTrain_.json"
    
    # B. Load it ONCE before the loops start
    try:
        with open(BASE_TEMPLATE_PATH, 'r') as f:
            base_config = json.load(f)
    except FileNotFoundError:
        print(f"❌ Could not find {BASE_TEMPLATE_PATH}. Please check the path.")
        exit()

    # ---------------------------------------------------------
    # Example 1: A simple 1D sweep you write yourself
    # ---------------------------------------------------------
    print("\n--- Generating 1D Sweep ---")
    # vg_test_points = [0.2, 0.4, 0.6, 0.8, 1.0]
    powers = [25, 50, 100, 200, 400]
    for idx, p in enumerate(powers):
        # Notice we pass 'base_config', and then any parameters we want to change!
        generate_from_base(
            base_dict=base_config, 
            output_dir="config/time_pulse_queue",
            power_arr=[p], 
            run_number=idx+1,
        )

    # ---------------------------------------------------------
    # Example 2: A nested 2D loop you write yourself
    # ---------------------------------------------------------
    # print("\n--- Generating 2D Grid Sweep ---")
    # voltages = [1.0, 2.0]
    # pulse_widths = [0.001, 0.010]
    
    # for vg in voltages:
    #     for pw in pulse_widths:
    #         generate_from_base(
    #             base_dict=base_config,
    #             output_dir="config/time_pulse_queue",
    #             vg_on=vg,
    #             pulse_width=pw,
    #             time_label=f"Vg={vg}V | PW={pw}s"
    #         )