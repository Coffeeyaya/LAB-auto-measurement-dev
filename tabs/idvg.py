import streamlit as st
import json
from pathlib import Path
from tabs.helper import launch_in_terminal

def render_idvg_tab():
    st.markdown("Configure and run your Id-Vg transfer characteristic sweeps.")

    # 1. Initialize prefixed defaults
    default_cfg = {
        "idvg_measurement_mode": "Steady-State Sweep", # <-- New Mode Default
        "idvg_description": "", "idvg_device_number": "", "idvg_run_number": "", "idvg_label": "",
        "idvg_vd_const": 1.0, "idvg_vg_start": -5.0, "idvg_vg_stop": 5.0, 
        "idvg_laser_stable_time": 30,
        "idvg_deplete_voltage": 0.0, "idvg_deplete_time": 0,
        "idvg_current_limit_a": 1e-3, "idvg_current_limit_b": 1e-3, 
        "idvg_nplc_a": 1.0, "idvg_nplc_b": 1.0,
        "idvg_num_points": 51, "idvg_wait_time": 30, 
        
        # Mode-Specific Defaults
        "idvg_source_to_measure_delay": 0.01,
        "idvg_base_vg": 0.0, 
        "idvg_pulse_width": 0.005, 
        "idvg_rest_time": 0.1,
        "idvg_fixed_range_a": 1e-5
    }

    for k, v in default_cfg.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if "idvg_laser_enable" not in st.session_state: st.session_state["idvg_laser_enable"] = False
    if "idvg_laser_channel" not in st.session_state: st.session_state["idvg_laser_channel"] = 6
    if "idvg_laser_wavelength" not in st.session_state: st.session_state["idvg_laser_wavelength"] = 660
    if "idvg_laser_power" not in st.session_state: st.session_state["idvg_laser_power"] = 100.0

    st.subheader("📂 Load Existing Configuration")
    
    if "idvg_uploader_key" not in st.session_state: st.session_state["idvg_uploader_key"] = 0

    uploaded_idvg = st.file_uploader(
        "Upload a previous JSON config", 
        type=["json"], 
        key=f"idvg_uploader_{st.session_state['idvg_uploader_key']}"
    )

    if uploaded_idvg is not None:
        try:
            uploaded_cfg = json.load(uploaded_idvg)
            for k, v in uploaded_cfg.items():
                if k == "laser_settings":
                    if v is None:
                        st.session_state["idvg_laser_enable"] = False
                    else:
                        st.session_state["idvg_laser_enable"] = True
                        st.session_state["idvg_laser_channel"] = v.get("channel", 6)
                        st.session_state["idvg_laser_wavelength"] = v.get("wavelength", 660)
                        st.session_state["idvg_laser_power"] = float(v.get("power", 100.0))
                else:
                    st.session_state[f"idvg_{k}"] = v
            
            st.session_state["idvg_uploader_key"] += 1
            st.rerun()
            
        except Exception as e:
            st.error(f"Failed to read JSON file: {e}")

    st.divider()

    # ==========================================
    # MODE SELECTION
    # ==========================================
    st.subheader("🎛️ Measurement Mode")
    mode = st.radio(
        "Select the Id-Vg sweep method:",
        ["Steady-State Sweep", "Pulsed Sweep"],
        horizontal=True,
        key="idvg_measurement_mode"
    )
    st.divider()

    # ==========================================
    # UI WIDGETS
    # ==========================================

    st.subheader("📝 General & Keithley")
    col1, col2, col3, col4 = st.columns(4)
    col1.text_input("Description", key="idvg_description")
    col2.text_input("Device Number", key="idvg_device_number")
    col3.text_input("Run Number", key="idvg_run_number")
    col4.text_input("Label (e.g., dark)", key="idvg_label")

    col5, col6, col7 = st.columns(3)
    with col5:
        st.number_input("Current Limit A (A)", format="%e", step=1e-4, key="idvg_current_limit_a")
        st.number_input("Current Limit B (A)", format="%e", step=1e-4, key="idvg_current_limit_b")
    with col6:
        st.number_input("NPLC A", step=0.1, key="idvg_nplc_a")
        st.number_input("NPLC B", step=0.1, key="idvg_nplc_b")
    with col7:
        if mode == "Pulsed Sweep":
            st.number_input("Fixed Range A (Max I_ON)", format="%e", step=1e-6, key="idvg_fixed_range_a", help="Required to prevent autorange delays during pulses.")

    st.divider()

    st.subheader("⚡ Sweep & Timing Settings")
    
    # Core sweep settings (Shared)
    col1, col2, col3, col4 = st.columns(4)
    col1.number_input("Vd Const (V)", step=0.1, key="idvg_vd_const")
    col2.number_input("Vg Start (V)", step=0.1, key="idvg_vg_start")
    col3.number_input("Vg Stop (V)", step=0.1, key="idvg_vg_stop")
    col4.number_input("Number of Points", step=1, key="idvg_num_points")

    # Conditional Timing settings based on Mode
    col5, col6, col7, col8 = st.columns(4)
    col5.number_input("Pre-Sweep Wait (s)", step=1, key="idvg_wait_time")
    
    if mode == "Steady-State Sweep":
        col6.number_input("Source-Measure Delay (s)", step=0.01, format="%f", key="idvg_source_to_measure_delay")
    elif mode == "Pulsed Sweep":
        col6.number_input("Base Vg (Resting) (V)", step=0.1, key="idvg_base_vg")
        col7.number_input("Pulse Width (s)", step=0.001, format="%f", key="idvg_pulse_width")
        col8.number_input("Rest Time (s)", step=0.01, format="%f", key="idvg_rest_time")

    # Depletion Settings (Shared)
    st.write("---")
    col9, col10 = st.columns(2)
    col9.number_input("Deplete Voltage (V)", step=0.1, key="idvg_deplete_voltage")
    col10.number_input("Deplete Time (s)", step=1, key="idvg_deplete_time")

    st.divider()

    st.subheader("🔦 Laser Settings")
    st.toggle("Enable Laser Illumination during Sweep", key="idvg_laser_enable")
    is_disabled = not st.session_state["idvg_laser_enable"]
    
    col_l1, col_l2, col_l3, col_l4 = st.columns(4)
    col_l1.number_input("Channel", step=1, key="idvg_laser_channel", disabled=is_disabled)
    col_l2.number_input("Wavelength (nm)", step=1, key="idvg_laser_wavelength", disabled=is_disabled)
    col_l3.number_input("Power (nW)", step=1.0, key="idvg_laser_power", disabled=is_disabled)
    col_l4.number_input("Laser Stable Time (s)", step=1, key="idvg_laser_stable_time", disabled=is_disabled)

    st.divider()

    # ==========================================
    # ACTIONS & SAVING
    # ==========================================
    st.subheader("🚀 Actions")
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        st.markdown("**Save Configuration**")
        if st.button("Update JSON Config", type="primary", use_container_width=True, key="idvg_save_btn"):
            try:
                laser_settings = None
                if st.session_state["idvg_laser_enable"]:
                    laser_settings = {
                        "channel": int(st.session_state["idvg_laser_channel"]),
                        "wavelength": int(st.session_state["idvg_laser_wavelength"]),
                        "power": float(st.session_state["idvg_laser_power"])
                    }

                # Build the Base Dictionary
                config_dict_idvg = {
                    "measurement_mode": st.session_state["idvg_measurement_mode"],
                    "description": st.session_state["idvg_description"],
                    "device_number": st.session_state["idvg_device_number"],
                    "run_number": st.session_state["idvg_run_number"],
                    "label": st.session_state["idvg_label"],
                    "vd_const": st.session_state["idvg_vd_const"],
                    "vg_start": st.session_state["idvg_vg_start"],
                    "vg_stop": st.session_state["idvg_vg_stop"],
                    "num_points": st.session_state["idvg_num_points"],
                    "wait_time": st.session_state["idvg_wait_time"],
                    "deplete_voltage": st.session_state["idvg_deplete_voltage"],
                    "deplete_time": st.session_state["idvg_deplete_time"],
                    "current_limit_a": st.session_state["idvg_current_limit_a"],
                    "current_limit_b": st.session_state["idvg_current_limit_b"],
                    "nplc_a": st.session_state["idvg_nplc_a"],
                    "nplc_b": st.session_state["idvg_nplc_b"],
                    "laser_settings": laser_settings,
                    "laser_stable_time": st.session_state["idvg_laser_stable_time"]
                }
                
                save_path = Path("config")
                save_path.mkdir(parents=True, exist_ok=True) 

                # Mode-Specific Data & Filenames
                if mode == "Steady-State Sweep":
                    config_dict_idvg["source_to_measure_delay"] = st.session_state["idvg_source_to_measure_delay"]
                    full_path = save_path / "FORMAL_idvg_config_app.json"
                elif mode == "Pulsed Sweep":
                    config_dict_idvg["base_vg"] = st.session_state["idvg_base_vg"]
                    config_dict_idvg["pulse_width"] = st.session_state["idvg_pulse_width"]
                    config_dict_idvg["rest_time"] = st.session_state["idvg_rest_time"]
                    config_dict_idvg["fixed_range_a"] = st.session_state["idvg_fixed_range_a"]
                    full_path = save_path / "FORMAL_idvg_pulse_config_app.json"

                with open(full_path, "w") as f: 
                    json.dump(config_dict_idvg, f, indent=4)
                    
                st.success(f"✅ Saved as {mode} to: {full_path.name}")
                with st.expander("👀 Preview Saved Configuration", expanded=True):
                    st.json(config_dict_idvg)

            except Exception as e: 
                st.error(f"Failed to save: {e}")

    with col_btn2:
        st.markdown("**Run Keithley Measurement**")
        
        # Smart pre-selection of the script to run
        default_script_index = 0 if mode == "Steady-State Sweep" else 1

        script_to_run = st.selectbox(
            "Select Measurement Script", 
            ("idvg.py", "idvg_pulse.py"), 
            index=default_script_index,
            label_visibility="collapsed"
        )
        
        dynamic_run_key = f"idvg_run_btn_{mode.replace(' ', '_')}"
        if st.button("▶ Run Script in Terminal", type="secondary", use_container_width=True, key=dynamic_run_key):
            success, msg = launch_in_terminal(script_to_run)
            if success: st.success(msg)
            else: st.error(msg)
            
    with col_btn3:
        st.markdown("**Manual Hardware Control**")
        st.write("") 
        if st.button("⚙️ Open Servo GUI", type="secondary", use_container_width=True, key="idvg_servo_btn"):
            success, msg = launch_in_terminal("servo_GUI.py")
            if success: st.success(msg)
            else: st.error(msg)