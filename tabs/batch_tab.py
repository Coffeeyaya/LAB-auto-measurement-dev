import streamlit as st
import json
import os
import copy
from pathlib import Path

# ==========================================
# 1. CORE GENERATOR FUNCTION
# ==========================================
def generate_batch_files(base_dict, target_dir, param_key, param_values, run_number_start):
    generated_files = []
    
    # Ensure the target directory exists
    Path(target_dir).mkdir(parents=True, exist_ok=True)
    
    # Count existing files in the target directory to continue the numbering sequence
    existing_files = [f for f in os.listdir(target_dir) if f.endswith('.json')]
    start_idx = len(existing_files) + 1
    
    hw_prefix = base_dict.get("hardware_mode", "Sweep").replace(" ", "").replace("+", "")
    elec_prefix = base_dict.get("electrical_mode", base_dict.get("measurement_mode", "Mode")).replace(" ", "")
    device = base_dict.get("device_number", "Dev")
    
    for i, val in enumerate(param_values):
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
        new_config["run_number"] = f"{int(run_number_start) + i}"
        existing_label = new_config.get("time_label", new_config.get("label", ""))
        new_label = f"{existing_label} | {param_key}={val}".strip(" |")
        if "time_label" in new_config: new_config["time_label"] = new_label
        if "label" in new_config: new_config["label"] = new_label
        
        # Safe filename formatting (e.g. 1.5 -> 1p5)
        # safe_val = str(val).replace(".", "p")
        filename = f"{start_idx + i:02d}.json"
        
        full_path = Path(target_dir) / filename
        with open(full_path, 'w') as f:
            json.dump(new_config, f, indent=4)
            
        generated_files.append(filename)
        
    return generated_files

def render_batch_generator_tab():
    # ==========================================
    # 2. STREAMLIT UI
    # ==========================================
    st.title("🗄️ Batch Generator")
    st.markdown("Easily generate a batch of configuration files by selecting a base template from your input folder.")

    col1, col2 = st.columns(2)
    base_config = None 

    with col1:
        st.subheader("1. Input Directory (Source)")
        
        # Let the user define the input folder (defaults to "input")
        in_dir_str = st.text_input("Look for templates in:", value="config/input")
        input_dir = Path(in_dir_str)
        input_dir.mkdir(exist_ok=True) # Auto-create if it doesn't exist
        
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
        
        # Let the user define the output folder (defaults to "output")
        out_dir_str = st.text_input("Save batch files to:", value="config/output")
        output_dir = Path(out_dir_str)
        
        

    st.divider()

    # --- Sweep Generation UI ---
    if base_config is not None:
        st.subheader("3. Define Parameter Sweep")
        
        # Extract keys dynamically
        available_keys = list(base_config.keys())
        if base_config.get("laser_settings") is not None:
            available_keys.extend(["laser_power", "laser_wavelength", "laser_channel"])
        available_keys.sort()

        col3, col4 = st.columns(2)
        
        with col3:
            param_to_sweep = st.selectbox("Select Parameter to Change:", options=available_keys)
            
            # Display current value
            if param_to_sweep.startswith("laser_"):
                nested_key = param_to_sweep.replace("laser_", "")
                current_val = base_config["laser_settings"].get(nested_key, "N/A")
            else:
                current_val = base_config.get(param_to_sweep, "N/A")
                
            st.caption(f"Current base value: `{current_val}`")

        with col4:
            val_str = st.text_input("Enter Sweep Values (comma-separated):", placeholder="e.g., 1.0, 2.0, 3.0")
            run_number_start = st.number_input("Enter starting run_number: ", min_value=1, value=1, step=1)
            
        if st.button("🚀 Generate Batch Queue", type="primary", use_container_width=True):
            if not val_str.strip():
                st.error("Please enter at least one value to sweep.")
            else:
                try:
                    # Safely parse the comma-separated string
                    parsed_values = []
                    for v in val_str.split(','):
                        v_clean = v.strip()
                        if '.' in v_clean or 'e' in v_clean.lower():
                            parsed_values.append(float(v_clean))
                        else:
                            parsed_values.append(int(v_clean))
                    
                    # Execute generation using the user's defined output directory
                    generated_files = generate_batch_files(
                        base_dict=base_config, 
                        target_dir=output_dir, 
                        param_key=param_to_sweep, 
                        param_values=parsed_values,
                        run_number_start=run_number_start
                    )
                    
                    st.success(f"✅ Successfully generated {len(generated_files)} files in the `{output_dir.name}` folder!")
                    with st.expander("Show Generated Files"):
                        for file in generated_files:
                            st.write(f"📄 `{file}`")
                            
                except ValueError:
                    st.error("❌ Format Error: Ensure your sweep values only contain numbers separated by commas!")
                except Exception as e:
                    st.error(f"❌ An error occurred: {e}")