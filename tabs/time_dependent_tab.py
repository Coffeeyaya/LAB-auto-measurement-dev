import streamlit as st
import json
import time
from pathlib import Path
from tabs.helper import launch_in_terminal

def render_time_dependent_tab():

    ### Initialize default values in session state (stremalit memory)
    default_cfg = {
        "description": "Time-Dep", "device_number": "1-1", "run_number": "1", "time_label": "", "wait_time": 0,
        "current_limit_a": 0.001, "current_limit_b": 0.001, "current_range_a": 1e-06, "current_range_b": 1e-06,
        "nplc_a": 1.0, "nplc_b": 1.0, 
        "vd_const": 1.0, "vg_const": 0.0,
        "vg_on": 1.0, "vg_off": 0.0,
        "duration_1": 1.0, "duration_2": 1.0, "duration_3": 2.0, "duration_4": 2.0,
        "cycle_number": 3, "on_off_number": 1, "servo_time_on": 1.0, "servo_time_off": 1.0,
        
        # Pulse-specific parameters
        "base_vg": 0.0, "pulse_width": 0.001, "rest_time": 0.3,

        # Baseline Reset parameters
        "target_baseline": 1e-11, "timeout": 600,
        
        # The Two-Tiered UI states
        "hardware_mode": "Dark Current", 
        "electrical_mode": "Continuous DC Vg"
    }

    # This loop ensures the keys are ALWAYS in session_state, 
    # which is why Streamlit threw the error when we also passed value=...
    for k, v in default_cfg.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if "wavelength_str" not in st.session_state: st.session_state["wavelength_str"] = "660"
    if "channel_str" not in st.session_state: st.session_state["channel_str"] = "6"
    if "power_str" not in st.session_state: st.session_state["power_str"] = "100"

    ### Load old config files
    st.subheader("📂 Load Existing Configuration (Optional)")
    if "uploader_key" not in st.session_state: 
        st.session_state["uploader_key"] = 0

    uploaded_file = st.file_uploader(
        "Upload a previous JSON config to pre-fill the form", 
        type=["json"], 
        key=f"td_uploader_{st.session_state['uploader_key']}"
    )

    if uploaded_file is not None:
        try:
            uploaded_cfg = json.load(uploaded_file)
            for k, v in uploaded_cfg.items():
                if k in ["wavelength_arr", "channel_arr", "power_arr"]:
                    st.session_state[k.replace("_arr", "_str")] = ", ".join(map(str, v))
                else:
                    st.session_state[k] = v
            st.session_state["uploader_key"] += 1
            st.rerun()
        except Exception as e:
            st.error(f"Failed to read JSON file: {e}")

    st.divider()

    ### Select Mode
    col_mode1, col_mode2 = st.columns(2)
    
    with col_mode1:
        st.subheader("🛠️ Hardware Setup")
        hardware = st.radio(
            "Select physical configuration:",
            ["Dark Current", "Laser Only", "Laser + Servo", "Baseline Reset"],
            key="hardware_mode"
        )
        
    with col_mode2:
        st.subheader("⚡ Electrical Mode")
        electric = st.radio(
            "Select Gate Voltage behavior:",
            ["Continuous DC Vg", "Pulsed Vg Train"],
            key="electrical_mode",
        )

    st.divider()

    ### UI widgets
    st.subheader("📝 General Information")
    col1, col2, col3, col4 = st.columns(4)
    col1.text_input("Description", key="description", help="Take notes here")
    col2.text_input("Device Number", key="device_number")
    col3.text_input("Run Number", key="run_number", help="Change this to prevent overwriting files")
    col4.text_input("Label", key="time_label", help="label that will show on the graph")

    st.divider()

    st.subheader("🔌 Keithley SMU Settings")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.number_input("Current Limit A (A)", format="%.1e", step=1e-4, key="current_limit_a", help="Max current allowed, used to protect hardware and device")
        st.number_input("Current Limit B (A)", format="%.1e", step=1e-4, key="current_limit_b", help="Max current allowed, used to protect hardware and device")
    if hardware != "Baseline Reset":
        with col2:
            st.number_input("Current Range A (A)", format="%.1e", step=1e-6, key="current_range_a", help="Measured current range, modify it lower to detect lower current, if measured value > range, then it is clamped at range")
            st.number_input("Current Range B (A)", format="%.1e", step=1e-6, key="current_range_b", help="Measured current range, modify it lower to detect lower current, if measured value > range, then it is clamped at range")
    else:
        st.text("Auto Range Mode")
        
    with col3:
        st.number_input("NPLC A", step=0.1, key="nplc_a", help="Number of power line cycles")
        st.number_input("NPLC B", step=0.1, key="nplc_b", help="Number of power line cycles")
    

    st.divider()

    st.subheader("⚡ Voltage & Timing Settings")
    col1, col2, col3, col4 = st.columns(4)
    col1.number_input("Vd Const (V)", step=0.1, key="vd_const")

    if hardware == "Baseline Reset":
        col2.number_input("Target Baseline (A)", value=st.session_state.get('target_baseline', 1e-11),
                          format="%.1e", step=1e-11, key="target_baseline", help="Measurement stops when |Id| drops below this value.")
        col3.number_input("Timeout (s)", value=st.session_state.get('timeout', 600),
                          min_value=60, step=60, key="timeout", help="Failsafe timeout if baseline is never reached.")
    else:
        col2.number_input("Vg ON (Target) (V)", step=0.1, key="vg_on")
        col3.number_input("Vg OFF (Target) (V)", step=0.1, key="vg_off")

        if electric == "Pulsed Vg Train":
            # Removed 'value='
            col4.number_input("Base Vg (Resting) (V)", 
                            value=st.session_state.get("base_vg", 0.0), step=0.1, key="base_vg", help="Pulsed mode: rest at base Vg, pulsed at target Vg")
        
        col_list = st.columns(4)
        with col_list[0]:
            st.number_input("Wait Time (s)", min_value=0, step=1, key="wait_time", help="Wait time before measurement")
            st.divider()

        # Conditionally show Optics
        if hardware in ["Laser Only", "Laser + Servo"]:
            st.subheader("🔦 Optics & Arrays (Comma-separated)")
            col1, col2, col3 = st.columns(3)
            # Removed 'value='
            col1.text_input("Wavelength Array (nm)", value=st.session_state.get("wavelength_str", 660), key="wavelength_str")
            col2.text_input("Channel Array", value=st.session_state.get("channel_str", 6), key="channel_str")
            col3.text_input("Power Array (nW)", value=st.session_state.get("power_str", 100), key="power_str")
            st.divider()

        st.subheader("⏱️ Timing & Sequence Durations")
        
        if electric == "Pulsed Vg Train":
            col1, col2 = st.columns(2)
            # Removed 'value='
            col1.number_input("Pulse Width (s)", 
                            value=st.session_state.get("pulse_width", 0.001), step=0.001, format="%f", key="pulse_width")
            col2.number_input("Rest Time between pulses (s)", 
                            value=st.session_state.get("rest_time", 0.3), step=0.01, format="%f", key="rest_time", help='Rest time between two pulses')
            
            st.write("---")

        # Smart Labelling based on Electrical Mode
        lbl_dur1 = "Dur 1 (Pulse Train @ Vg OFF)" if electric == "Pulsed Vg Train" else "Dur 1 (Hold @ Vg OFF)"
        lbl_dur2 = "Dur 2 (Pulse Train @ Vg ON)" if electric == "Pulsed Vg Train" else "Dur 2 (Hold @ Vg ON)"

        # Removed 'value=' from all conditional widgets below
        if hardware == "Dark Current":
            col1, col2, col3 = st.columns(3)
            col1.number_input(lbl_dur1, step=0.5, key="duration_1")
            col2.number_input(lbl_dur2, step=0.5, key="duration_2")
            col3.number_input("Cycle Number", min_value=1, step=1, key="cycle_number")

        elif hardware == "Laser Only":
            col1, col2, col3, col4 = st.columns(4)
            col1.number_input(lbl_dur1, step=0.5, key="duration_1")
            col2.number_input(lbl_dur2, step=0.5, key="duration_2")
            col3.number_input("Dur 3 (Laser ON)", step=0.5, key="duration_3")
            col4.number_input("Dur 4 (Laser OFF)", step=0.5, key="duration_4")
            
            col5, col6 = st.columns(2)
            col5.number_input("Cycle Number", min_value=1, step=1, key="cycle_number")
            col6.number_input("ON/OFF Number", min_value=1, step=1, key="on_off_number")

        elif hardware == "Laser + Servo":
            col1, col2, col3, col4 = st.columns(4)
            col1.number_input(lbl_dur1, step=0.5, key="duration_1")
            col2.number_input(lbl_dur2, step=0.5, key="duration_2")
            
            col5, col6, col7 = st.columns(3)
            col5.number_input("Cycle Number", min_value=1, step=1, key="cycle_number")
            col6.number_input("Servo On/Off #", 
                            value=st.session_state.get("on_off_number", 3), min_value=1, step=1, key="on_off_number")
            col7.number_input("Servo open Time (s)", 
                            value=st.session_state.get("servo_time_on", 1), step=0.5, key="servo_time_on")
            col7.number_input("Servo close Time (s)", 
                            value=st.session_state.get("servo_time_off", 1), step=0.5, key="servo_time_off")

    st.divider()

    ### Actions and Queue
    st.subheader("📋 Queue Preview & Management")

    if electric == "Continuous DC Vg":
        queue_dir = Path("config/time_queue")
        target_script = "run_time.py"
    else:
        queue_dir = Path("config/time_pulse_queue")
        target_script = "run_time_pulse.py"
        
    queue_dir.mkdir(exist_ok=True, parents=True)
    queued_files = sorted(list(queue_dir.glob("*.json")))

    if queued_files:
        col_sel, col_clr = st.columns([3, 1])
        
        # 1. Select a file from the queue to preview
        selected_file = col_sel.selectbox(
            "Select a queued file to preview:", 
            options=queued_files, 
            format_func=lambda x: x.name,
            key="preview_select_time"
        )
        
        # 2. Display the content
        if selected_file:
            with st.expander(f"🔍 Previewing: {selected_file.name}", expanded=True):
                with open(selected_file, "r") as f:
                    preview_data = json.load(f)
                
                # Show as interactive JSON
                st.json(preview_data)

        if col_clr.button("🗑️ Clear Queue", use_container_width=True, key="clear_queue_preview_time"):
            for f in queued_files: f.unlink()
            st.rerun()
    else:
        st.warning("📦 Queue is currently empty.")

    # ACTION BUTTONS
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        st.markdown("**1. Add to Queue**")
        custom_name = st.text_input("Config Name (Optional)", value="", label_visibility="collapsed", key="td_custom_name")
        
        if st.button("➕ Add Configuration", type="primary", use_container_width=True, key="td_save_btn"):
            try:
                # Base config uses session state dynamically
                config_dict = {
                    "hardware_mode": st.session_state["hardware_mode"],
                    "electrical_mode": st.session_state["electrical_mode"],
                    "description": st.session_state["description"],
                    "device_number": st.session_state["device_number"],
                    "run_number": st.session_state["run_number"],
                    "wait_time": st.session_state["wait_time"],
                    "current_limit_a": st.session_state["current_limit_a"],
                    "current_limit_b": st.session_state["current_limit_b"],
                    "current_range_a": st.session_state["current_range_a"],
                    "current_range_b": st.session_state["current_range_b"],
                    "nplc_a": st.session_state["nplc_a"],
                    "nplc_b": st.session_state["nplc_b"],
                    "vd_const": st.session_state["vd_const"],
                }


                # --- Handle Baseline Reset Exclusively ---
                if hardware == "Baseline Reset":
                    config_dict["target_baseline"] = st.session_state["target_baseline"]
                    config_dict["timeout"] = st.session_state["timeout"]
                else:
                    config_dict["vg_on"] = st.session_state.get("vg_on", 1.0)
                    config_dict["vg_off"] = st.session_state.get("vg_off", 0.0)
                    config_dict["cycle_number"] = st.session_state.get("cycle_number", 3)
                    config_dict["duration_1"] = st.session_state.get("duration_1", 5.0)
                    config_dict["duration_2"] = st.session_state.get("duration_2", 1.0)

                    # Electrical Appends
                    if electric == "Pulsed Vg Train":
                        config_dict["base_vg"] = st.session_state.get("base_vg", 0.0)
                        config_dict["pulse_width"] = st.session_state.get("pulse_width", 0.005)
                        config_dict["rest_time"] = st.session_state.get("rest_time", 0.1)

                    # Hardware Appends
                    if hardware == "Laser Only":
                        config_dict["duration_3"] = st.session_state.get("duration_3", 2.0)
                        config_dict["duration_4"] = st.session_state.get("duration_4", 2.0)
                        config_dict["wavelength_arr"] = [int(x.strip()) for x in st.session_state.get("wavelength_str", "660").split(",")]
                        config_dict["channel_arr"] = [int(x.strip()) for x in st.session_state.get("channel_str", "6").split(",")]
                        config_dict["power_arr"] = [float(x.strip()) for x in st.session_state.get("power_str", "100").split(",")]
                        config_dict["on_off_number"] = st.session_state.get("on_off_number", 1)

                    if hardware == "Laser + Servo":
                        config_dict["wavelength_arr"] = [int(x.strip()) for x in st.session_state.get("wavelength_str", "660").split(",")]
                        config_dict["channel_arr"] = [int(x.strip()) for x in st.session_state.get("channel_str", "6").split(",")]
                        config_dict["power_arr"] = [float(x.strip()) for x in st.session_state.get("power_str", "100").split(",")]
                        config_dict["on_off_number"] = st.session_state.get("on_off_number", 1)
                        config_dict["servo_time_on"] = st.session_state.get("servo_time_on", 1.0)
                        config_dict["servo_time_off"] = st.session_state.get("servo_time_off", 1.0)

                # Create sequenced filename
                next_idx = len(queued_files) + 1
                safe_name = custom_name.replace(" ", "_")
                mode_prefix = electric.replace(" ", "")
                hw_prefix = hardware.replace(" ", "").replace("+", "")
                filename = f"{next_idx:02d}_{hw_prefix}_{mode_prefix}_{safe_name}.json"
                
                full_path = queue_dir / filename
                with open(full_path, "w") as f:
                    json.dump(config_dict, f, indent=4)
                
                st.success(f"✅ Added to Queue: {filename}")
                time.sleep(0.5) 
                st.rerun()

            except ValueError:
                st.error("Format Error: Ensure arrays are numbers separated by commas (e.g., '660, 532')")
            except Exception as e:
                st.error(f"Failed to save file: {e}")

    with col_btn2:
        st.markdown("**2. Run Queue**")
        
        # Display which script is cued up to run (for clarity)
        st.info(f"Target Script: `{target_script}`")
        
        dynamic_run_key = f"td_run_{hardware.replace(' ', '_')}_{electric.replace(' ', '_')}"
        
        # Changed button type to "primary" since it's the main action
        if st.button("▶ Run Script in Terminal", type="primary", use_container_width=True, key=dynamic_run_key):
            if not queued_files:
                st.error(f"The {electric} queue is empty! Add a configuration first.")
            else:
                success, msg = launch_in_terminal(target_script)
                if success: st.success(msg)
                else: st.error(msg)

    with col_btn3:
        st.markdown("**3. Hardware Control**")
        st.write("") 
        if st.button("⚙️ Open Servo GUI", type="secondary", use_container_width=True, key="td_servo_btn"):
            success, msg = launch_in_terminal("servo_GUI.py")
            if success: st.success(msg)
            else: st.error(msg)