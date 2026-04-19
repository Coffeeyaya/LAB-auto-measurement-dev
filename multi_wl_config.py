import json
import os

def generate_configs(laser_template_path, reset_template_path, output_dir, experiment_matrix):
    """
    Generates customized JSON config files for Laser Servo and Baseline Reset.
    
    experiment_matrix: List of dictionaries defining the variables for each run.
    """
    # 1. Load the base templates
    try:
        with open(laser_template_path, 'r') as f:
            laser_template = json.load(f)
            
        with open(reset_template_path, 'r') as f:
            reset_template = json.load(f)
    except FileNotFoundError as e:
        print(f"Error loading templates: {e}")
        return

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # 2. Iterate through the array of inputs and generate files
    for run_config in experiment_matrix:
        run_str = str(run_config["run_number"])
        ch = run_config["channel"]
        wl = run_config["wavelength"]
        pwr = run_config["power"]
        
        # --- Generate Laser Measurement Config ---
        laser_data = laser_template.copy()
        
        # Update run number and array parameters
        laser_data["run_number"] = run_str
        laser_data["channel_arr"] = [ch]
        laser_data["wavelength_arr"] = [wl]
        
        # Convert power to float just to match your 100.0 format in the template
        laser_data["power_arr"] = [float(pwr)] 
        
        # Name the file descriptively
        laser_filename = f"0{run_str}_LaserServo_run{run_str}_ch{ch}_{wl}nm.json"
        laser_filepath = os.path.join(output_dir, laser_filename)
        
        with open(laser_filepath, 'w') as f:
            json.dump(laser_data, f, indent=4)
            
        # --- Generate Baseline Reset Config ---
        reset_data = reset_template.copy()
        
        # Update run number (baseline reset doesn't need optical params)
        reset_data["run_number"] = run_str
        
        reset_filename = f"0{run_str}_BaselineReset_run{run_str}.json"
        reset_filepath = os.path.join(output_dir, reset_filename)
        
        with open(reset_filepath, 'w') as f:
            json.dump(reset_data, f, indent=4)
            
    print(f"Success: Generated {len(experiment_matrix) * 2} config files in '{output_dir}'.")

if __name__ == "__main__":
    # Define your array of inputs here. 
    # Different wavelengths correspond to different AOTF channels.
    my_experiment_matrix = [
        {"run_number": "1", "channel": 0, "wavelength": 450, "power": 100},
        {"run_number": "2", "channel": 2, "wavelength": 532, "power": 100},
        {"run_number": "3", "channel": 4, "wavelength": 600, "power": 100},
        {"run_number": "4", "channel": 6, "wavelength": 660, "power": 100},
    ]
    
    # Paths to the template files you uploaded
    LASER_TEMPLATE = '/Users/tsaiyunchen/Desktop/lab/master/measurement_dev/measure/config/time_pulse_queue/01_LaserServo_PulsedVgTrain_.json'
    RESET_TEMPLATE = '/Users/tsaiyunchen/Desktop/lab/master/measurement_dev/measure/config/time_pulse_queue/02_BaselineReset_PulsedVgTrain_.json'
    OUTPUT_FOLDER = 'config/generated_configs'
    
    generate_configs(
        laser_template_path=LASER_TEMPLATE, 
        reset_template_path=RESET_TEMPLATE, 
        output_dir=OUTPUT_FOLDER, 
        experiment_matrix=my_experiment_matrix
    )