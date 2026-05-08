import json
import os

def generate_configs(laser_template_path, reset_template_path, output_dir, experiment_matrix):
    """
    Generates customized JSON config files for Laser Servo and Baseline Reset.
    Modifies servo_time_on and auto-calculates servo_time_off.
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
    for i, run_config in enumerate(experiment_matrix):
        run_str = str(run_config["run_number"])
        servo_on = run_config["servo_time_on"]
        power = run_config['power']
        
        # Calculate servo_time_off dynamically (always 2x servo_time_on)
        servo_off = servo_on * 2.0
        
        # Calculate alternating prefixes to ensure correct queue order
        # i=0 -> reset=01, laser=02
        # i=1 -> reset=03, laser=04
        reset_prefix = (2 * i) + 1
        laser_prefix = (2 * i) + 2
        
        # --- Generate Baseline Reset Config (Comes First) ---
        reset_data = reset_template.copy()
        reset_data["run_number"] = run_str
        
        reset_filename = f"{reset_prefix:02d}_BaselineReset_run{run_str}.json"
        reset_filepath = os.path.join(output_dir, reset_filename)
        
        with open(reset_filepath, 'w') as f:
            json.dump(reset_data, f, indent=4)

        # --- Generate Laser Measurement Config (Comes Second) ---
        laser_data = laser_template.copy()
        laser_data["run_number"] = run_str
        laser_data["servo_time_on"] = servo_on
        laser_data["servo_time_off"] = servo_off
        laser_data['power_arr'] = [power]
        
        laser_filename = f"{laser_prefix:02d}_LaserServo_run{run_str}_servoOn_{servo_on}s.json"
        laser_filepath = os.path.join(output_dir, laser_filename)
        
        with open(laser_filepath, 'w') as f:
            json.dump(laser_data, f, indent=4)
            
    print(f"Success: Generated {len(experiment_matrix) * 2} config files in '{output_dir}'.")


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
    my_experiment_matrix = build_matrix(run_number_start=1, servo_on_list=[0.3, 3, 30], pwr_list=[25, 50, 100, 200, 400])
    
    # Paths to the template files
    # Make sure to save the JSON you provided as the "01_LaserServo..." template!
    RESET_TEMPLATE = 'config/time_pulse_queue/01_BaselineReset_PulsedVgTrain_.json'
    LASER_TEMPLATE = 'config/time_pulse_queue/02_LaserServo_PulsedVgTrain_.json'
    
    
    OUTPUT_FOLDER = 'config/time_pulse_queue_batch'
    
    generate_configs(
        laser_template_path=LASER_TEMPLATE, 
        reset_template_path=RESET_TEMPLATE, 
        output_dir=OUTPUT_FOLDER, 
        experiment_matrix=my_experiment_matrix
    )