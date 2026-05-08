import json
import os

def generate_configs(laser_template_path, reset_template_path, output_dir, experiment_matrix, target_baseline, reset=True):
    """
    Generates customized JSON config files for Laser Servo and Baseline Reset.
    Modifies servo_time_on and auto-calculates servo_time_off.
    """
    # 1. Load the base templates conditionally
    try:
        with open(laser_template_path, 'r') as f:
            laser_template = json.load(f)
            
        # FIX 1: Only load the reset template if reset is actually True!
        if reset:
            with open(reset_template_path, 'r') as f:
                reset_template = json.load(f)
    except FileNotFoundError as e:
        print(f"Error loading templates: {e}")
        return

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # FIX 2: Create a counter to track actual files generated
    files_generated = 0

    # 2. Iterate through the array of inputs and generate files
    for i, run_config in enumerate(experiment_matrix):
        run_str = str(run_config["run_number"])
        servo_on = run_config["servo_time_on"]
        power = run_config['power']
        
        # Calculate servo_time_off dynamically (always 2x servo_time_on)
        servo_off = servo_on * 2.0
        
        # FIX 3: Dynamic Prefix Calculation to prevent numbering gaps
        if reset:
            reset_prefix = (2 * i) + 1
            laser_prefix = (2 * i) + 2
        else:
            laser_prefix = i + 1  # Numbers them 1, 2, 3, 4 smoothly if no reset
        
        # --- Generate Baseline Reset Config (If Enabled) ---
        if reset:
            reset_data = reset_template.copy()
            reset_data["run_number"] = run_str
            reset_data['target_baseline'] = target_baseline
            
            reset_filename = f"{reset_prefix:02d}_BaselineReset_run{run_str}.json"
            reset_filepath = os.path.join(output_dir, reset_filename)
            
            with open(reset_filepath, 'w') as f:
                json.dump(reset_data, f, indent=4)
            files_generated += 1

        # --- Generate Laser Measurement Config ---
        laser_data = laser_template.copy()
        laser_data["run_number"] = run_str
        laser_data["servo_time_on"] = servo_on
        laser_data["servo_time_off"] = servo_off
        laser_data['power_arr'] = [power]
        
        laser_filename = f"{laser_prefix:02d}_LaserServo_run{run_str}_servoOn_{servo_on}s.json"
        laser_filepath = os.path.join(output_dir, laser_filename)
        
        with open(laser_filepath, 'w') as f:
            json.dump(laser_data, f, indent=4)
        files_generated += 1
            
    # FIX 4: Accurate success reporting
    print(f"Success: Generated {files_generated} config files in '{output_dir}'.")


if __name__ == "__main__":
    # Define your specific servo pulse times here
    def build_matrix(run_number_start, servo_on_list, pwr_list):
        run_number = run_number_start
        matrix = []
        for pwr in pwr_list:
            for servo_on in servo_on_list:
                matrix.append({"run_number": str(run_number), "servo_time_on": servo_on, 'power': pwr})
                run_number += 1
            
        return matrix
        
    my_experiment_matrix = build_matrix(run_number_start=1, servo_on_list=[0.5, 1, 5, 10, 30], pwr_list=[25, 50, 100, 200, 400])
    
    # Paths to the template files
    RESET_TEMPLATE = 'config/time_pulse_queue/01_BaselineReset_PulsedVgTrain_.json'
    LASER_TEMPLATE = 'config/time_pulse_queue/02_LaserServo_PulsedVgTrain_.json'
    OUTPUT_FOLDER = 'config/time_pulse_queue_batch'
    
    generate_configs(
        laser_template_path=LASER_TEMPLATE, 
        reset_template_path=RESET_TEMPLATE, 
        output_dir=OUTPUT_FOLDER, 
        experiment_matrix=my_experiment_matrix,
        target_baseline='5e-11',
        reset=False # It will now neatly generate files 01 to 25 without any gaps!
    )