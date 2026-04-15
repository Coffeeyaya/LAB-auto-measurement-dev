import streamlit as st
import json
import os
import copy
from pathlib import Path

# ==========================================
# 1. CORE GENERATOR FUNCTION
# ==========================================
def generate_batch_files(base_dict, target_dir, param_key, param_values, run_number_start, 
                         baseline_mode="None", target_baseline=1e-11, timeout=600,
                         baseline_vg_on=1.0, baseline_base_vg=0.0, 
                         baseline_pulse_width=0.001, baseline_rest_time=0.3):
    generated_files = []
    
    # Ensure the target directory exists
    Path(target_dir).mkdir(parents=True, exist_ok=True)
    
    # Count existing files in the target directory to continue the numbering sequence
    existing_files = [f for f in os.listdir(target_dir) if f.endswith('.json')]
    file_idx = len(existing_files) + 1
    
    device = base_dict.get("device_number", "Dev")
    
    for i, val in enumerate(param_values):
        current_run_number = int(run_number_start) + i
        
        # ---------------------------------------------------------
        # STEP A: GENERATE BASELINE RESET CONFIG (If enabled)
        # ---------------------------------------------------------
        if baseline_mode != "None":
            # Map the UI selection to the exact hardware_mode string the backend expects
            hw_mode_str = "Baseline Reset" if baseline_mode == "Baseline Reset (DC)" else "Baseline Reset @ Vg"
            
            baseline_config = {
                "hardware_mode": hw_mode_str,
                "device_number": device,
                "run_number": str(current_run_number), # Share run number so CSVs pair up perfectly
                "target_baseline": target_baseline,
                "timeout": timeout,
                "vd_const": base_dict.get("vd_const", 1.0),
                "label": f"Reset before Run {current_run_number} ({param_key}={val})"
            }
            
            # Append the specific pulsed variables if that mode was chosen
            if hw_mode_str == "Baseline Reset @ Vg":
                baseline_config["vg_on"] = baseline_vg_on
                baseline_config["base_vg"] = baseline_base_vg
                baseline_config["pulse_width"] = baseline_pulse_width
                baseline_config["rest_time"] = baseline_rest_time
            
            baseline_filename = f"{file_idx:02d}_BaselineReset.json"
            full_path = Path(target_dir) / baseline_filename
            with open(full_path, 'w') as f:
                json.dump(baseline_config, f, indent=4)
                
            generated_files.append(baseline_filename)
            file_idx += 1 # Increment index for the formal measurement

        # ---------------------------------------------------------
        # STEP B: GENERATE FORMAL MEASUREMENT CONFIG
        # ---------------------------------------------------------
        new_config = copy.deepcopy(base_dict)
        
        # Nested Interceptor for optical settings
        if param_key == "laser_power" and "laser_settings" in new_config and new_config["laser_settings"]:
            new_config["laser_settings"]["power"] = val
        elif param_key == "laser_wavelength" and "laser_settings" in new_config and new_config["laser_settings"]:
            new_config["laser_settings"]["wavelength"] = val
        elif param_key == "power_arr":
            new_config[param_key] = [val]
        else:
            new_config[param_key] = val
        
        # Update labels and run numbers
        new_config["run_number"] = str(current_run_number)
        existing_label = new_config.get("time_label", new_config.get("label", ""))
        new_label = f"{existing_label} | {param_key}={val}".strip(" |")
        
        if "time_label" in new_config: new_config["time_label"] = new_label
        if "label" in new_config: new_config["label"] = new_label
        
        # Clean sequential filename
        hw_prefix = new_config.get("hardware_mode", "Sweep").replace(" ", "").replace("+", "")
        meas_filename = f"{file_idx:02d}_{hw_prefix}_Measure.json"
        
        full_path = Path(target_dir) / meas_filename
        with open(full_path, 'w') as f:
            json.dump(new_config, f, indent=4)
            
        generated_files.append(meas_filename)
        file_idx += 1 # Increment index for the next cycle
        
    return generated_files


# ==========================================
# 2. STREAMLIT TAB UI
# ==========================================
def render_batch_generator_tab():
    st.title("🗄️ Batch Generator")
    st.markdown("Easily generate a batch of configuration files by selecting a base template and an output queue.")

    # --- FOLDER DISCOVERY LOGIC ---
    config_base_path = Path("config")
    config_base_path.mkdir(exist_ok=True)
    
    (config_base_path / "templates").mkdir(exist_ok=True)
    (config_base_path / "time_pulse_queue").mkdir(exist_ok=True)
    
    available_dirs = [d for d in config_base_path.iterdir() if d.is_dir()]
    available_dirs.sort(key=lambda x: x.name) 

    col1, col2 = st.columns(2)
    base_config = None 

    with col1:
        st.subheader("1. Input Directory (Source)")
        
        input_dir = st.selectbox(
            "Look for templates in:", 
            options=available_dirs, 
            format_func=lambda x: x.name, 
            key="input_dir_select"
        )
        
        json_files = sorted(list(input_dir.glob("*.json")))
        
        if not json_files:
            st.info(f"📂 No JSON files found in `{input_dir.name}`. Please drop a base configuration in there!")
        else:
            base_file = st.selectbox("Select Base Configuration:", json_files, format_func=lambda x: x.name)
            with open(base_file, "r") as f:
                base_config = json.load(f)
            if base_config is not None:
                with st.expander(f"🔍 Previewing Base Config: {base_file.name}", expanded=False):
                    st.json(base_config)
            
    with col2:
        st.subheader("2. Output Directory (Destination)")
        
        default_out_idx = 1 if len(available_dirs) > 1 else 0
        
        output_dir = st.selectbox(
            "Save batch files to:", 
            options=available_dirs, 
            format_func=lambda x: x.name, 
            index=default_out_idx,
            key="output_dir_select"
        )
        
    st.divider()

    # --- Sweep Generation UI ---
    if base_config is not None:
        st.subheader("3. Define Parameter Sweep")
        
        available_keys = list(base_config.keys())
        if base_config.get("laser_settings") is not None:
            available_keys.extend(["laser_power", "laser_wavelength", "laser_channel"])
        available_keys.sort()

        col3, col4 = st.columns(2)
        
        with col3:
            param_to_sweep = st.selectbox("Select Parameter to Change:", options=available_keys)
            
            if param_to_sweep.startswith("laser_"):
                nested_key = param_to_sweep.replace("laser_", "")
                current_val = base_config["laser_settings"].get(nested_key, "N/A")
            else:
                current_val = base_config.get(param_to_sweep, "N/A")
                
            st.caption(f"Current base value: `{current_val}`")

        with col4:
            val_str = st.text_input("Enter Sweep Values (comma-separated):", placeholder="e.g., 1.0, 2.0, 3.0")
            run_number_start = st.number_input("Enter starting run_number: ", min_value=1, value=1, step=1)
        
        st.divider()
        
        # --- NEW: Baseline Reset Interleaving Logic ---
        st.subheader("4. Baseline Reset Injection")
        
        baseline_mode = st.radio(
            "Insert a recovery step before each formal measurement:",
            ["None", "Baseline Reset (DC)", "Baseline Reset @ Vg (Pulsed)"],
            horizontal=True
        )
        
        # Default initialization
        target_baseline = 1e-11
        timeout = 600
        baseline_vg_on = 1.0
        baseline_base_vg = 0.0
        baseline_pulse_width = 0.001
        baseline_rest_time = 0.3
        
        if baseline_mode != "None":
            col_b1, col_b2 = st.columns(2)
            target_baseline = col_b1.number_input("Target Baseline (A)", format="%.1e", step=1e-11, value=1e-11)
            timeout = col_b2.number_input("Timeout (s)", min_value=60, step=60, value=600)
            
            if baseline_mode == "Baseline Reset @ Vg (Pulsed)":
                col_b3, col_b4, col_b5, col_b6 = st.columns(4)
                baseline_vg_on = col_b3.number_input("Target Vg [Pulse] (V)", value=1.0, step=0.1, key="bat_vg_on")
                baseline_base_vg = col_b4.number_input("Base Vg [Resting] (V)", value=0.0, step=0.1, key="bat_base_vg")
                baseline_pulse_width = col_b5.number_input("Pulse Width (s)", value=0.001, step=0.001, format="%f", key="bat_pw")
                baseline_rest_time = col_b6.number_input("Rest Time (s)", value=0.3, step=0.01, format="%f", key="bat_rt")

        st.write("") # spacing
        
        if st.button("🚀 Generate Batch Queue", type="primary", use_container_width=True):
            if not val_str.strip():
                st.error("Please enter at least one value to sweep.")
            else:
                try:
                    parsed_values = []
                    for v in val_str.split(','):
                        v_clean = v.strip()
                        if '.' in v_clean or 'e' in v_clean.lower():
                            parsed_values.append(float(v_clean))
                        else:
                            parsed_values.append(int(v_clean))
                    
                    # Execute generation 
                    generated_files = generate_batch_files(
                        base_dict=base_config, 
                        target_dir=output_dir, 
                        param_key=param_to_sweep, 
                        param_values=parsed_values,
                        run_number_start=run_number_start,
                        baseline_mode=baseline_mode,
                        target_baseline=target_baseline,
                        timeout=timeout,
                        baseline_vg_on=baseline_vg_on,
                        baseline_base_vg=baseline_base_vg,
                        baseline_pulse_width=baseline_pulse_width,
                        baseline_rest_time=baseline_rest_time
                    )
                    
                    st.success(f"✅ Successfully generated {len(generated_files)} files in the `{output_dir.name}` folder!")
                    with st.expander("Show Generated Files"):
                        for file in generated_files:
                            st.write(f"📄 `{file}`")
                            
                except ValueError:
                    st.error("❌ Format Error: Ensure your sweep values only contain numbers separated by commas!")
                except Exception as e:
                    st.error(f"❌ An error occurred: {e}")