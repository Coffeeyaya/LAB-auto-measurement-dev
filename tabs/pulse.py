import streamlit as st
import json
from pathlib import Path
from tabs.helper import launch_in_terminal

def render_vg_pulse_tab():
    st.markdown("Configure Time-Dependent sequences using ultra-fast $V_G$ pulses to prevent charge trapping.")

    # 1. Initialize prefixed defaults (pls_)
    default_cfg = {
        "pls_description": "Pulsed Time-Dep", "pls_device_number": "1-1", "pls_run_number": "1", "pls_wait_time": 5,
        "pls_current_limit_a": 1e-3, "pls_current_limit_b": 1e-3, "pls_current_range_a": 1e-5, "pls_current_range_b": 1e-5,
        "pls_nplc_a": 1.0, "pls_nplc_b": 1.0, "pls_vd_const": 2.0, "pls_vg_on": 1.0, "pls_vg_off": -1.0,
        "pls_duration_1": 5.0, "pls_duration_2": 5.0, "pls_duration_3": 5.0, "pls_duration_4": 5.0,
        "pls_cycle_number": 5, "pls_on_off_number": 3, "pls_servo_time": 10.0,
        
        # --- The New Pulse Parameters ---
        "pls_base_vg": 0.0,
        "pls_pulse_width_ms": 5.0, 
        "pls_rest_time_ms": 100.0
    }

    for k, v in default_cfg.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if "pls_wavelength_str" not in st.session_state: st.session_state["pls_wavelength_str"] = "660"
    if "pls_channel_str" not in st.session_state: st.session_state["pls_channel_str"] = "6"
    if "pls_power_str" not in st.session_state: st.session_state["pls_power_str"] = "100"

    st.subheader("📂 Load Existing Configuration")
    
    if "pls_uploader_key" not in st.session_state: st.session_state["pls_uploader_key"] = 0

    uploaded_pls = st.file_uploader(
        "Upload a previous JSON config", 
        type=["json"], 
        key=f"pls_uploader_{st.session_state['pls_uploader_key']}"
    )

    if uploaded_pls is not None:
        try:
            uploaded_cfg = json.load(uploaded_pls)
            for k, v in uploaded_cfg.items():
                if k in ["wavelength_arr", "channel_arr", "power_arr"]:
                    st.session_state[f"pls_{k.replace('_arr', '_str')}"] = ", ".join(map(str, v))
                else:
                    st.session_state[f"pls_{k}"] = v
            
            st.session_state["pls_uploader_key"] += 1
            st.rerun()
        except Exception as e:
            st.error(f"Failed to read JSON file: {e}")

    st.divider()

    # ==========================================
    # UI WIDGETS
    # ==========================================

    st.subheader("📝 General & Keithley")
    col1, col2, col3, col4 = st.columns(4)
    col1.text_input("Description", key="pls_description")
    col2.text_input("Device Number", key="pls_device_number")
    col3.text_input("Run Number", key="pls_run_number")
    col4.number_input("Wait Time (s)", min_value=0, step=1, key="pls_wait_time")

    col5, col6, col7 = st.columns(3)
    with col5:
        st.number_input("Current Limit A (A)", format="%e", step=1e-4, key="pls_current_limit_a")
        st.number_input("Current Limit B (A)", format="%e", step=1e-4, key="pls_current_limit_b")
    with col6:
        st.number_input("Current Range A (A)", format="%e", step=1e-6, key="pls_current_range_a")
        st.number_input("Current Range B (A)", format="%e", step=1e-6, key="pls_current_range_b")
    with col7:
        st.number_input("NPLC A", step=0.1, key="pls_nplc_a")
        st.number_input("NPLC B", step=0.1, key="pls_nplc_b")

    st.divider()

    st.subheader("⚡ Target Voltages & Fast Pulse Settings")
    col1, col2, col3 = st.columns(3)
    col1.number_input("Vd Const (V)", step=0.1, key="pls_vd_const")
    col2.number_input("Target Vg ON (V)", step=0.1, key="pls_vg_on")
    col3.number_input("Target Vg OFF (V)", step=0.1, key="pls_vg_off")

    st.info("At the start of each duration, the hardware will fire ONE pulse to the Target Vg, and then continuously measure relaxation at the Base Vg.")

    col4, col5 = st.columns(2)
    col4.number_input("Base Vg (Resting Voltage)", step=0.1, key="pls_base_vg")
    col5.number_input("Pulse Width (ms)", step=1.0, format="%.1f", key="pls_pulse_width_ms")


    st.divider()

    st.subheader("🔦 Optics & Sequence Durations")
    col1, col2, col3 = st.columns(3)
    col1.text_input("Wavelength Array (nm)", key="pls_wavelength_str")
    col2.text_input("Channel Array", key="pls_channel_str")
    col3.text_input("Power Array (nW)", key="pls_power_str")

    col4, col5, col6, col7 = st.columns(4)
    col4.number_input("Duration 1 (s)", step=0.5, key="pls_duration_1")
    col5.number_input("Duration 2 (s)", step=0.5, key="pls_duration_2")
    col6.number_input("Duration 3 (s)", step=0.5, key="pls_duration_3")
    col7.number_input("Duration 4 (s)", step=0.5, key="pls_duration_4")

    col8, col9, col10 = st.columns(3)
    col8.number_input("Cycle Number", min_value=1, step=1, key="pls_cycle_number")
    col9.number_input("ON/OFF Number", min_value=1, step=1, key="pls_on_off_number")
    col10.number_input("Servo Time (s)", step=0.5, key="pls_servo_time")

    st.divider()

    # ==========================================
    # ACTIONS & SAVING
    # ==========================================
    st.subheader("🚀 Actions")
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        st.markdown("**Save Configuration**")
        if st.button("Update JSON Config", type="primary", use_container_width=True, key="pls_save_btn"):
            try:
                wavelength_arr = [int(x.strip()) for x in st.session_state["pls_wavelength_str"].split(",")]
                channel_arr = [int(x.strip()) for x in st.session_state["pls_channel_str"].split(",")]
                power_arr = [float(x.strip()) for x in st.session_state["pls_power_str"].split(",")]

                config_dict_pls = {
                    "description": st.session_state["pls_description"],
                    "device_number": st.session_state["pls_device_number"],
                    "run_number": st.session_state["pls_run_number"],
                    "wait_time": st.session_state["pls_wait_time"],
                    "current_limit_a": st.session_state["pls_current_limit_a"],
                    "current_limit_b": st.session_state["pls_current_limit_b"],
                    "current_range_a": st.session_state["pls_current_range_a"],
                    "current_range_b": st.session_state["pls_current_range_b"],
                    "nplc_a": st.session_state["pls_nplc_a"],
                    "nplc_b": st.session_state["pls_nplc_b"],
                    "vd_const": st.session_state["pls_vd_const"],
                    "vg_on": st.session_state["pls_vg_on"],
                    "vg_off": st.session_state["pls_vg_off"],
                    "duration_1": st.session_state["pls_duration_1"],
                    "duration_2": st.session_state["pls_duration_2"],
                    "duration_3": st.session_state["pls_duration_3"],
                    "duration_4": st.session_state["pls_duration_4"],
                    "wavelength_arr": wavelength_arr,
                    "channel_arr": channel_arr,
                    "power_arr": power_arr,
                    "cycle_number": st.session_state["pls_cycle_number"],
                    "on_off_number": st.session_state["pls_on_off_number"],
                    "servo_time": st.session_state["pls_servo_time"],
                    
                    # New Pulse parameters added to JSON:
                    "base_vg": st.session_state["pls_base_vg"],
                    "pulse_width_ms": st.session_state["pls_pulse_width_ms"],
                }
                
                save_path = Path("config") / "FORMAL_time_dependent_config_pulse_app.json"
                save_path.parent.mkdir(parents=True, exist_ok=True) 
                
                with open(save_path, "w") as f: 
                    json.dump(config_dict_pls, f, indent=4)
                    
                st.success(f"✅ Saved to: {save_path.name}")
                with st.expander("👀 Preview Saved Configuration", expanded=True):
                    st.json(config_dict_pls)

            except Exception as e: 
                st.error(f"Failed to save: {e}")

    with col_btn2:
        st.markdown("**Run Keithley Measurement**")
        if st.button("▶ Run Pulse Script in Terminal", type="secondary", use_container_width=True, key="pls_run_btn"):
            success, msg = launch_in_terminal("time_dep_servo_pulse_app.py")
            if success: st.success(msg)
            else: st.error(msg)
            
    with col_btn3:
        st.markdown("**Manual Hardware Control**")
        st.write("") 
        if st.button("⚙️ Open Servo GUI", type="secondary", use_container_width=True, key="pls_servo_btn"):
            success, msg = launch_in_terminal("servo_GUI.py")
            if success: st.success(msg)
            else: st.error(msg)