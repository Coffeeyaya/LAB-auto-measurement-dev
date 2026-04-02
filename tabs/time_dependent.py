import streamlit as st
import json
from pathlib import Path
from tabs.helper import launch_in_terminal

def render_time_dependent_tab():
    st.markdown("Select your measurement mode, tweak your parameters, and launch the experiment.")

    # 1. Initialize default values
    default_cfg = {
        "description": "Standard Time-Dep", "device_number": "1-1", "run_number": "1", "wait_time": 0,
        "current_limit_a": 0.001, "current_limit_b": 0.001, "current_range_a": 1e-05, "current_range_b": 1e-05,
        "nplc_a": 1.0, "nplc_b": 1.0, 
        "vd_const": 1.0, "vg_const": 0.0,
        "vg_on": 1.0, "vg_off": 0.0,
        "duration_1": 5.0, "duration_2": 1.0, "duration_3": 2.0, "duration_4": 2.0,
        "cycle_number": 3, "on_off_number": 1, "servo_time": 1.0,
        "measurement_mode": "Dark Current (Steady Vg)" 
    }

    for k, v in default_cfg.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if "wavelength_str" not in st.session_state: st.session_state["wavelength_str"] = "660"
    if "channel_str" not in st.session_state: st.session_state["channel_str"] = "6"
    if "power_str" not in st.session_state: st.session_state["power_str"] = "100"

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

    # ==========================================
    # MODE SELECTION
    # ==========================================
    st.subheader("🎛️ Measurement Mode")
    mode = st.radio(
        "Select the hardware configuration for this run:",
        ["Dark Current (Steady Vg)", "Laser Only", "Laser + Servo"],
        horizontal=True,
        key="measurement_mode"
    )

    st.divider()

    # ==========================================
    # UI WIDGETS
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
        st.number_input("Current Limit A (A)", format="%.1e", step=1e-4, key="current_limit_a")
        st.number_input("Current Limit B (A)", format="%.1e", step=1e-4, key="current_limit_b")
    with col2:
        st.number_input("Current Range A (A)", format="%.1e", step=1e-6, key="current_range_a")
        st.number_input("Current Range B (A)", format="%.1e", step=1e-6, key="current_range_b")
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

    # conditionally show Optics
    if mode in ["Laser Only", "Laser + Servo"]:
        st.subheader("🔦 Optics & Arrays (Comma-separated)")
        col1, col2, col3 = st.columns(3)
        col1.text_input("Wavelength Array (nm)", value=st.session_state.get("wavelength_str", "660"), key="wavelength_str")
        col2.text_input("Channel Array", value=st.session_state.get("channel_str", "6"), key="channel_str")
        col3.text_input("Power Array (nW)", value=st.session_state.get("power_str", "100"), key="power_str")
        st.divider()

    st.subheader("⏱️ Timing & Sequence Durations")
    
    # --- CONDITIONAL TIMING UI (Safeguarded with .get) ---
    if mode == "Dark Current (Steady Vg)":
        col1, col2, col3 = st.columns(3)
        col1.number_input("Dur 1 (Dark Relax)", value=st.session_state.get("duration_1", 5.0), step=0.5, key="duration_1")
        col2.number_input("Dur 2 (Vg on)", value=st.session_state.get("duration_2", 1.0), step=0.5, key="duration_2")
        col3.number_input("Cycle Number", value=st.session_state.get("cycle_number", 3), min_value=1, step=1, key="cycle_number")

    elif mode == "Laser Only":
        col1, col2, col3, col4 = st.columns(4)
        col1.number_input("Dur 1 (Dark Relax)", value=st.session_state.get("duration_1", 5.0), step=0.5, key="duration_1")
        col2.number_input("Dur 2 (Vg on)", value=st.session_state.get("duration_2", 1.0), step=0.5, key="duration_2")
        col3.number_input("Dur 3 (Laser ON)", value=st.session_state.get("duration_3", 2.0), step=0.5, key="duration_3")
        col4.number_input("Dur 4 (Laser OFF)", value=st.session_state.get("duration_4", 2.0), step=0.5, key="duration_4")
        
        col5, col6 = st.columns(2)
        col5.number_input("Cycle Number", value=st.session_state.get("cycle_number", 3), min_value=1, step=1, key="cycle_number")
        col6.number_input("ON/OFF Number", value=st.session_state.get("on_off_number", 1), min_value=1, step=1, key="on_off_number")

    elif mode == "Laser + Servo":
        col1, col2, col3, col4 = st.columns(4)
        col1.number_input("Dur 1 (Dark Relax)", value=st.session_state.get("duration_1", 5.0), step=0.5, key="duration_1")
        col2.number_input("Dur 2 (Vg on)", value=st.session_state.get("duration_2", 1.0), step=0.5, key="duration_2")
        col3.number_input("Dur 3 (Pre-Servo Wait)", value=st.session_state.get("duration_3", 2.0), step=0.5, key="duration_3")
        col4.number_input("Dur 4 (Post-Servo Wait)", value=st.session_state.get("duration_4", 2.0), step=0.5, key="duration_4")
        
        col5, col6, col7 = st.columns(3)
        col5.number_input("Cycle Number", value=st.session_state.get("cycle_number", 3), min_value=1, step=1, key="cycle_number")
        col6.number_input("Servo Swings (On/Off #)", value=st.session_state.get("on_off_number", 1), min_value=1, step=1, key="on_off_number")
        col7.number_input("Servo Block Time (s)", value=st.session_state.get("servo_time", 1.0), step=0.5, key="servo_time")

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
                # Base config shared by all modes
                config_dict = {
                    "measurement_mode": st.session_state["measurement_mode"],
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
                    "vd_const": st.session_state["vd_const"]
                }

                # Mode-specific JSON building with .get() to prevent KeyErrors
                if mode == "Dark Current (Steady Vg)":
                    config_dict["vg_on"] = st.session_state.get("vg_on", 1.0)
                    config_dict["vg_off"] = st.session_state.get("vg_off", 0.0)
                    config_dict["cycle_number"] = st.session_state.get("cycle_number", 3)
                    config_dict["duration_1"] = st.session_state.get("duration_1", 5.0)
                    config_dict["duration_2"] = st.session_state.get("duration_2", 1.0)
                    config_dict["duration_3"] = st.session_state.get("duration_3", 2.0)
                    config_dict["duration_4"] = st.session_state.get("duration_4", 2.0)
                else:
                    config_dict["vg_on"] = st.session_state.get("vg_on", 1.0)
                    config_dict["vg_off"] = st.session_state.get("vg_off", 0.0)
                    config_dict["cycle_number"] = st.session_state.get("cycle_number", 3)
                    config_dict["duration_1"] = st.session_state.get("duration_1", 5.0)
                    config_dict["duration_2"] = st.session_state.get("duration_2", 1.0)
                    config_dict["duration_3"] = st.session_state.get("duration_3", 2.0)
                    config_dict["duration_4"] = st.session_state.get("duration_4", 2.0)
                    config_dict["wavelength_arr"] = [int(x.strip()) for x in st.session_state.get("wavelength_str", "660").split(",")]
                    config_dict["channel_arr"] = [int(x.strip()) for x in st.session_state.get("channel_str", "6").split(",")]
                    config_dict["power_arr"] = [float(x.strip()) for x in st.session_state.get("power_str", "100").split(",")]
                    config_dict["on_off_number"] = st.session_state.get("on_off_number", 1)

                if mode == "Laser + Servo":
                    config_dict["servo_time"] = st.session_state.get("servo_time", 1.0)

                # Save it (using the same file name as requested)
                save_path = Path("config")
                save_path.mkdir(parents=True, exist_ok=True) 
                
                full_path = save_path / "FORMAL_time_dependent_config.json"
                
                with open(full_path, "w") as f:
                    json.dump(config_dict, f, indent=4)
                
                st.success(f"✅ Saved as {mode} to: {full_path.name}")
                with st.expander("👀 Preview Saved Configuration", expanded=True):
                    st.json(config_dict)

            except ValueError:
                st.error("Format Error: Ensure arrays are numbers separated by commas (e.g., '660, 532')")
            except Exception as e:
                st.error(f"Failed to save file: {e}")

    with col_btn2:
        st.markdown("**Run Keithley Measurement**")
        
        if mode == "Dark Current (Steady Vg)": 
            default_script_index = 1  
        else: 
            default_script_index = 0  

        script_to_run = st.selectbox(
            "Select Measurement Script", 
            ("time_dep_servo.py", "time_dep_dark.py"), 
            index=default_script_index,
            label_visibility="collapsed"
        )
        
        dynamic_run_key = f"td_run_{mode.replace(' ', '_')}"
        if st.button("▶ Run Script in Terminal", type="secondary", use_container_width=True, key=dynamic_run_key):
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