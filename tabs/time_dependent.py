import streamlit as st
import json
from pathlib import Path
from tabs.helper import launch_in_terminal

def render_time_dependent_tab():
    st.markdown("Load an existing config, tweak your parameters, and launch the measurement.")

    # 1. Initialize default values directly into Streamlit's memory (session_state)
    # These match your JSON structure exactly.
    default_cfg = {
        "description": "Standard Time-Dep", "device_number": "2-2", "run_number": "0", "wait_time": 5,
        "current_limit_a": 0.001, "current_limit_b": 0.001, "current_range_a": 1e-05, "current_range_b": 1e-05,
        "nplc_a": 1.0, "nplc_b": 1.0, "vd_const": 2.0, "vg_on": 1.0, "vg_off": -1.0,
        "duration_1": 5.0, "duration_2": 5.0, "duration_3": 5.0, "duration_4": 5.0,
        "cycle_number": 5, "on_off_number": 3, "servo_time": 20.0
    }

    # Load standard defaults on the very first run
    for k, v in default_cfg.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Arrays need to be stored as comma-separated strings for the UI text boxes
    if "wavelength_str" not in st.session_state: st.session_state["wavelength_str"] = "660"
    if "channel_str" not in st.session_state: st.session_state["channel_str"] = "6"
    if "power_str" not in st.session_state: st.session_state["power_str"] = "100"

    st.subheader("📂 Load Existing Configuration (Optional)")
    
    # 2. Setup the dynamic uploader key for the "Self-Clearing" trick
    if "uploader_key" not in st.session_state: 
        st.session_state["uploader_key"] = 0

    uploaded_file = st.file_uploader(
        "Upload a previous JSON config to pre-fill the form", 
        type=["json"], 
        key=f"td_uploader_{st.session_state['uploader_key']}"
    )

    # 3. Process the file if uploaded
    if uploaded_file is not None:
        try:
            uploaded_cfg = json.load(uploaded_file)
            
            # Forcefully inject the JSON values directly into the Widget Memory Keys!
            for k, v in uploaded_cfg.items():
                if k in ["wavelength_arr", "channel_arr", "power_arr"]:
                    # Convert arrays (e.g., [660]) back to strings (e.g., "660")
                    st.session_state[k.replace("_arr", "_str")] = ", ".join(map(str, v))
                else:
                    st.session_state[k] = v
            
            # Clear the uploader box by changing its name, then restart the app instantly
            st.session_state["uploader_key"] += 1
            st.rerun()
            
        except Exception as e:
            st.error(f"Failed to read JSON file: {e}")

    st.divider()

    # ==========================================
    # UI WIDGETS (Bound directly to session_state via 'key')
    # Notice we DO NOT use 'value=' anymore!
    # ==========================================

    st.subheader("📝 General Information")
    col1, col2, col3, col4 = st.columns(4)
    col1.text_input("Description", key="description")
    col2.text_input("Device Number", key="device_number")
    col3.text_input("Run Number", key="run_number")
    col4.number_input("Wait Time (s)", min_value=0, step=1, key="wait_time")

    st.divider()

    st.subheader("🔌 Keithley SMU Settings")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.number_input("Current Limit A (A)", format="%e", step=1e-4, key="current_limit_a")
        st.number_input("Current Limit B (A)", format="%e", step=1e-4, key="current_limit_b")
    with col2:
        st.number_input("Current Range A (A)", format="%e", step=1e-6, key="current_range_a")
        st.number_input("Current Range B (A)", format="%e", step=1e-6, key="current_range_b")
    with col3:
        st.number_input("NPLC A", step=0.1, key="nplc_a")
        st.number_input("NPLC B", step=0.1, key="nplc_b")

    st.divider()

    st.subheader("⚡ Voltage Settings")
    col1, col2, col3 = st.columns(3)
    col1.number_input("Vd Const (V)", step=0.1, key="vd_const")
    col2.number_input("Vg ON (V)", step=0.1, key="vg_on")
    col3.number_input("Vg OFF (V)", step=0.1, key="vg_off")

    st.divider()

    st.subheader("🔦 Optics & Arrays (Comma-separated)")
    col1, col2, col3 = st.columns(3)
    col1.text_input("Wavelength Array (nm)", key="wavelength_str")
    col2.text_input("Channel Array", key="channel_str")
    col3.text_input("Power Array (nW)", key="power_str")

    st.divider()

    st.subheader("⏱️ Timing & Sequence Durations")
    col1, col2, col3, col4 = st.columns(4)
    col1.number_input("Duration 1 (s)", step=0.5, key="duration_1")
    col2.number_input("Duration 2 (s)", step=0.5, key="duration_2")
    col3.number_input("Duration 3 (s)", step=0.5, key="duration_3")
    col4.number_input("Duration 4 (s)", step=0.5, key="duration_4")

    col5, col6, col7 = st.columns(3)
    col5.number_input("Cycle Number", min_value=1, step=1, key="cycle_number")
    col6.number_input("ON/OFF Number", min_value=1, step=1, key="on_off_number")
    col7.number_input("Servo Time (s)", step=0.5, key="servo_time")

    st.divider()

    # ==========================================
    # ACTIONS & SAVING
    # ==========================================
    st.subheader("🚀 Actions")
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        st.markdown("**Save Configuration**")
        if st.button("Update JSON Config", type="primary", use_container_width=True, key="td_save"):
            try:
                # Convert the comma-separated strings back into Python arrays
                wavelength_arr = [int(x.strip()) for x in st.session_state["wavelength_str"].split(",")]
                channel_arr = [int(x.strip()) for x in st.session_state["channel_str"].split(",")]
                power_arr = [float(x.strip()) for x in st.session_state["power_str"].split(",")]

                # Construct the final dictionary
                config_dict = {
                    "description": st.session_state["description"],
                    "device_number": st.session_state["device_number"],
                    "run_number": st.session_state["run_number"],
                    "current_limit_a": st.session_state["current_limit_a"],
                    "current_limit_b": st.session_state["current_limit_b"],
                    "current_range_a": st.session_state["current_range_a"],
                    "current_range_b": st.session_state["current_range_b"],
                    "nplc_a": st.session_state["nplc_a"],
                    "nplc_b": st.session_state["nplc_b"],
                    "vd_const": st.session_state["vd_const"],
                    "vg_on": st.session_state["vg_on"],
                    "vg_off": st.session_state["vg_off"],
                    "duration_1": st.session_state["duration_1"],
                    "duration_2": st.session_state["duration_2"],
                    "duration_3": st.session_state["duration_3"],
                    "duration_4": st.session_state["duration_4"],
                    "wavelength_arr": wavelength_arr,
                    "channel_arr": channel_arr,
                    "power_arr": power_arr,
                    "cycle_number": st.session_state["cycle_number"],
                    "on_off_number": st.session_state["on_off_number"],
                    "servo_time": st.session_state["servo_time"],
                    "wait_time": st.session_state["wait_time"]
                }
                
                # Save it to the config folder
                save_path = Path("config")
                save_path.mkdir(parents=True, exist_ok=True) 
                full_path = save_path / "FORMAL_time_dependent_config_app.json"
                with open(full_path, "w") as f:
                    json.dump(config_dict, f, indent=4)
                
                st.success(f"✅ Saved to: {full_path.name}")
                
                # --- JSON PREVIEWER ---
                # This creates a collapsible box that defaults to being open
                with st.expander("👀 Preview Saved Configuration", expanded=True):
                    st.json(config_dict) # This automatically formats the dictionary!

            except ValueError:
                st.error("Format Error: Ensure arrays are numbers separated by commas (e.g., '660, 532')")
            except Exception as e:
                st.error(f"Failed to save file: {e}")

    with col_btn2:
        st.markdown("**Run Keithley Measurement**")
        script_to_run = st.selectbox(
            "Select Measurement Script", 
            ("time_dep_app.py", "time_dep_servo_app.py", "time_dep_dark_app.py", "time_dep_servo_pulse_app.py"), 
            label_visibility="collapsed"
        )
        if st.button("▶ Run Script in Terminal", type="secondary", use_container_width=True, key="td_run"):
            success, msg = launch_in_terminal(script_to_run)
            if success: st.success(msg)
            else: st.error(msg)

    with col_btn3:
        st.markdown("**Manual Hardware Control**")
        st.write("") 
        st.write("")
        if st.button("⚙️ Open Servo GUI", type="secondary", use_container_width=True):
            success, msg = launch_in_terminal("servo_GUI.py")
            if success: st.success(msg)
            else: st.error(msg)