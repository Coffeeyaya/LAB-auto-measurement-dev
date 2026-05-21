import json
import os

def generate_configs(laser_template_path, output_dir, experiment_matrix):
    """
    Generates customized JSON config files for Laser Servo.
    """
    # 1. Load the base template
    try:
        with open(laser_template_path, 'r') as f:
            laser_template = json.load(f)
    except FileNotFoundError as e:
        print(f"Error loading template: {e}")
        return

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # 2. Iterate through the array of inputs and generate files
    for i, run_config in enumerate(experiment_matrix):
        run_str = str(run_config["run_number"])
        ch = run_config["channel"]
        wl = run_config["wavelength"]
        pwr = run_config["power"]

        # Sequential prefix: 01, 02, 03...
        laser_prefix = i + 1

        # --- Generate Laser Measurement Config ---
        laser_data = laser_template.copy()
        laser_data["run_number"] = run_str
        laser_data["channel_arr"] = [ch]
        laser_data["wavelength_arr"] = [wl]
        laser_data["power_arr"] = [float(pwr)] 

        # :02d forces the number to be 2 digits, padding with a zero if necessary
        laser_filename = f"{laser_prefix:02d}_LaserServo_run{run_str}_ch{ch}_{wl}nm.json"
        laser_filepath = os.path.join(output_dir, laser_filename)

        with open(laser_filepath, 'w') as f:
            json.dump(laser_data, f, indent=4)

    print(f"Success: Generated {len(experiment_matrix)} config files in '{output_dir}'.")


if __name__ == "__main__":
    # Define your array of inputs here. 
    # Different wavelengths correspond to different AOTF channels.
    my_experiment_matrix = [
        {"run_number": "1", "channel": 0, "wavelength": 450, "power": 100},
        {"run_number": "2", "channel": 0, "wavelength": 470, "power": 100},
        {"run_number": "3", "channel": 1, "wavelength": 490, "power": 100},
        {"run_number": "4", "channel": 2, "wavelength": 510, "power": 100},
        {"run_number": "5", "channel": 3, "wavelength": 530, "power": 100},
        {"run_number": "6", "channel": 3, "wavelength": 550, "power": 100},
        {"run_number": "7", "channel": 4, "wavelength": 570, "power": 100},
        {"run_number": "8", "channel": 4, "wavelength": 590, "power": 100},
        {"run_number": "9", "channel": 4, "wavelength": 610, "power": 100},
        {"run_number": "10", "channel": 5, "wavelength": 620, "power": 100},
        {"run_number": "11", "channel": 5, "wavelength": 630, "power": 100},
        {"run_number": "12", "channel": 5, "wavelength": 640, "power": 100},
        {"run_number": "13", "channel": 6, "wavelength": 650, "power": 100},
        {"run_number": "14", "channel": 6, "wavelength": 660, "power": 100},
        {"run_number": "15", "channel": 6, "wavelength": 670, "power": 100},
        {"run_number": "16", "channel": 7, "wavelength": 680, "power": 100},
        {"run_number": "17", "channel": 7, "wavelength": 690, "power": 100},
        {"run_number": "18", "channel": 7, "wavelength": 700, "power": 100},
    ]

    # Paths to the template files
    LASER_TEMPLATE = 'config/time_pulse_queue/01_LaserServo_PulsedVgTrain_.json'
    OUTPUT_FOLDER = 'config/generated_configs'

    generate_configs(
        laser_template_path=LASER_TEMPLATE, 
        output_dir=OUTPUT_FOLDER, 
        experiment_matrix=my_experiment_matrix
    )