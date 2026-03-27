import streamlit as st
import json
import pandas as pd
import numpy as np
# import matplotlib.pyplot as plt
import plotly.graph_objects as go
from pathlib import Path
import os
import subprocess 
import sys
import platform

# --- Helper Function: Launch Script in New Terminal ---
def launch_in_terminal(script_name):
    """Launches a given Python script in a new OS-level terminal window."""
    if not os.path.exists(script_name):
        return False, f"Could not find script: {script_name}"
    
    current_dir = os.getcwd()
    try:
        if platform.system() == "Windows":
            command = f'start cmd /K "{sys.executable} {script_name}"'
            subprocess.Popen(command, shell=True)
            return True, f"🚀 Opened {script_name} in a new Command Prompt!"
            
        elif platform.system() == "Darwin":
            apple_script = f'''
            tell application "Terminal"
                do script "cd '{current_dir}' && '{sys.executable}' '{script_name}'"
                activate
            end tell
            '''
            subprocess.Popen(['osascript', '-e', apple_script])
            return True, f"🚀 Opened {script_name} in a new Mac Terminal!"
            
        else:
            return False, "Opening a new terminal is currently only supported on Windows and Mac."
    except Exception as e:
        return False, f"Failed to launch script: {e}"

# --- Page Config ---
st.set_page_config(page_title="Lab Auto", layout="wide")
st.title("🔬 Lab Automation")

# Create Tabs for the different workflows
tab_time_dep, tab_idvg, tab_power, tab_plot, tab_encoder = st.tabs([
    "⚡ Time-Dependent", 
    "📈 Id-Vg Sweep",
    "🔦 Power Calibration", 
    "📊 Data Plotter",
    "📡 Optical Encoder"  # <--- ADD THIS
])
# ==========================================
# TAB 1: TIME-DEPENDENT MEASUREMENT
# ==========================================
with tab_time_dep:
    st.markdown("Load an existing config, tweak your parameters, and launch the measurement.")

    st.subheader("📂 Load Existing Configuration (Optional)")
    uploaded_file = st.file_uploader("Upload a previous JSON config to pre-fill the form", type=["json"], key="time_dep_uploader")

    cfg = {
        "description": "Standard Time-Dep", "device_number": "0-0", "run_number": "0", "wait_time": 5,
        "current_limit_a": 1e-3, "current_limit_b": 1e-3, "current_range_a": 1e-5, "current_range_b": 1e-5,
        "nplc_a": 1.0, "nplc_b": 1.0, "vd_const": 2.0, "vg_on": 1.0, "vg_off": -1.0,
        "wavelength_arr": [660], "channel_arr": [6], "power_arr": [100],
        "duration_1": 5.0, "duration_2": 5.0, "duration_3": 5.0, "duration_4": 5.0,
        "cycle_number": 5, "on_off_number": 3, "servo_time": 10
    }

    if uploaded_file is not None:
        try:
            uploaded_cfg = json.load(uploaded_file)
            cfg.update(uploaded_cfg) 
            st.success(f"✅ Successfully loaded settings from: **{uploaded_file.name}**")
        except Exception as e:
            st.error(f"Failed to read JSON file: {e}")

    st.divider()

    st.subheader("📝 General Information")
    col1, col2, col3, col4 = st.columns(4)
    description = col1.text_input("Description", value=str(cfg["description"]))
    device_number = col2.text_input("Device Number", value=str(cfg["device_number"]))
    run_number = col3.text_input("Run Number", value=str(cfg["run_number"]))
    wait_time = col4.number_input("Wait Time (s)", value=int(cfg["wait_time"]), min_value=0, step=1)

    st.divider()

    st.subheader("🔌 Keithley SMU Settings")
    col1, col2, col3 = st.columns(3)
    with col1:
        current_limit_a = st.number_input("Current Limit A (A)", value=float(cfg["current_limit_a"]), format="%e")
        current_limit_b = st.number_input("Current Limit B (A)", value=float(cfg["current_limit_b"]), format="%e")
    with col2:
        current_range_a = st.number_input("Current Range A (A)", value=float(cfg["current_range_a"]), format="%e")
        current_range_b = st.number_input("Current Range B (A)", value=float(cfg["current_range_b"]), format="%e")
    with col3:
        nplc_a = st.number_input("NPLC A", value=float(cfg["nplc_a"]), step=0.1)
        nplc_b = st.number_input("NPLC B", value=float(cfg["nplc_b"]), step=0.1)

    st.divider()

    st.subheader("⚡ Voltage Settings")
    col1, col2, col3 = st.columns(3)
    vd_const = col1.number_input("Vd Const (V)", value=float(cfg["vd_const"]), step=0.1)
    vg_on = col2.number_input("Vg ON (V)", value=float(cfg["vg_on"]), step=0.1)
    vg_off = col3.number_input("Vg OFF (V)", value=float(cfg["vg_off"]), step=0.1)

    st.divider()

    st.subheader("🔦 Optics & Arrays (Comma-separated)")
    default_wav = ", ".join(map(str, cfg["wavelength_arr"]))
    default_ch = ", ".join(map(str, cfg["channel_arr"]))
    default_pw = ", ".join(map(str, cfg["power_arr"]))

    col1, col2, col3 = st.columns(3)
    wavelength_str = col1.text_input("Wavelength Array (nm)", value=default_wav, key="td_wav")
    channel_str = col2.text_input("Channel Array", value=default_ch, key="td_ch")
    power_str = col3.text_input("Power Array (nW)", value=default_pw, key="td_pw")

    st.divider()

    st.subheader("⏱️ Timing & Sequence Durations")
    col1, col2, col3, col4 = st.columns(4)
    duration_1 = col1.number_input("Duration 1 (s)", value=float(cfg["duration_1"]), step=0.5)
    duration_2 = col2.number_input("Duration 2 (s)", value=float(cfg["duration_2"]), step=0.5)
    duration_3 = col3.number_input("Duration 3 (s)", value=float(cfg["duration_3"]), step=0.5)
    duration_4 = col4.number_input("Duration 4 (s)", value=float(cfg["duration_4"]), step=0.5)

    col5, col6, col7 = st.columns(3)
    cycle_number = col5.number_input("Cycle Number", value=int(cfg["cycle_number"]), min_value=1, step=1)
    on_off_number = col6.number_input("ON/OFF Number", value=int(cfg["on_off_number"]), min_value=1, step=1)
    servo_time = col7.number_input("Servo Time (s)", value=float(cfg["servo_time"]), step=0.05)

    st.divider()

    st.subheader("🚀 Actions")
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        st.markdown("**Save Configuration**")
        if st.button("Update JSON Config", type="primary", use_container_width=True, key="td_save"):
            try:
                wavelength_arr = [int(x.strip()) for x in wavelength_str.split(",")]
                channel_arr = [int(x.strip()) for x in channel_str.split(",")]
                power_arr = [int(x.strip()) for x in power_str.split(",")]

                config_dict = {
                    "description": description, "device_number": device_number, "run_number": run_number,
                    "current_limit_a": current_limit_a, "current_limit_b": current_limit_b,
                    "current_range_a": current_range_a, "current_range_b": current_range_b,
                    "nplc_a": nplc_a, "nplc_b": nplc_b, "vd_const": vd_const, "vg_on": vg_on, "vg_off": vg_off,
                    "duration_1": duration_1, "duration_2": duration_2, "duration_3": duration_3, "duration_4": duration_4,
                    "wavelength_arr": wavelength_arr, "channel_arr": channel_arr, "power_arr": power_arr,
                    "cycle_number": cycle_number, "on_off_number": on_off_number, "servo_time": servo_time,
                    "wait_time": wait_time
                }
                
                save_path = Path("config")
                save_path.mkdir(parents=True, exist_ok=True) 
                full_path = save_path / "time_dependent_config_app.json"
                with open(full_path, "w") as f:
                    json.dump(config_dict, f, indent=4)
                st.success(f"✅ Saved to: {full_path.name}")

            except Exception as e:
                st.error(f"Failed to save file: {e}")

    with col_btn2:
        st.markdown("**Run Keithley Measurement**")
        script_to_run = st.selectbox("Select Measurement Script", ("time_dep_app.py", "time_dep_servo_app.py", "time_dep_dark_app.py"), label_visibility="collapsed")
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


# ==========================================
# TAB 2: ID-VG MEASUREMENT (NEW)
# ==========================================
with tab_idvg:
    st.markdown("Configure and run your Id-Vg transfer characteristic sweeps.")

    st.subheader("📂 Load Existing Configuration")
    uploaded_idvg = st.file_uploader("Upload a previous JSON config", type=["json"], key="idvg_uploader")

    cfg_idvg = {
        "description": "", "device_number": "", "run_number": "", "label": "dark",
        "vd_const": 2.0, "vg_start": -5.0, "vg_stop": 5.0, 
        "laser_settings": None, "laser_stable_time": 30,
        "deplete_voltage": 0.0, "deplete_time": 0,
        "current_limit_a": 1e-3, "current_limit_b": 1e-3, "nplc_a": 1.0, "nplc_b": 1.0,
        "num_points": 51, "wait_time": 30, "source_to_measure_delay": 0.01
    }

    if uploaded_idvg is not None:
            try:
                cfg_idvg.update(json.load(uploaded_idvg))
                
                # --- THE FIX ---
                # Force Streamlit's memory to overwrite the stubborn text box
                new_laser = "null" if cfg_idvg["laser_settings"] is None else json.dumps(cfg_idvg["laser_settings"])
                st.session_state["idvg_laser"] = new_laser
                
                st.success(f"✅ Loaded: **{uploaded_idvg.name}**")
            except Exception as e:
                st.error(f"Failed to read JSON: {e}")

    st.divider()

    st.subheader("📝 General & Keithley")
    col1, col2, col3, col4 = st.columns(4)
    idvg_desc = col1.text_input("Description", value=str(cfg_idvg["description"]), key="idvg_desc")
    idvg_dev = col2.text_input("Device Number", value=str(cfg_idvg["device_number"]), key="idvg_dev")
    idvg_run = col3.text_input("Run Number", value=str(cfg_idvg["run_number"]), key="idvg_run")
    idvg_label = col4.text_input("Label (e.g., dark)", value=str(cfg_idvg["label"]), key="idvg_lbl")

    col5, col6, col7, col8 = st.columns(4)
    idvg_clim = col5.number_input("Current Limit (A)", value=float(cfg_idvg["current_limit_a"]), format="%e", key="idvg_clim")
    idvg_nplc = col6.number_input("NPLC", value=float(cfg_idvg["nplc_a"]), step=0.1, key="idvg_nplc")
    idvg_num_pts = col7.number_input("Number of Points", value=int(cfg_idvg["num_points"]), step=1, key="idvg_num_pts")
    idvg_s2m = col8.number_input("Source-Measure Delay (s)", value=float(cfg_idvg["source_to_measure_delay"]), step=0.01, format="%f", key="idvg_s2m")

    st.divider()

    st.subheader("⚡ Sweep & Laser Settings")
    col1, col2, col3, col4 = st.columns(4)
    idvg_vd = col1.number_input("Vd Const (V)", value=float(cfg_idvg["vd_const"]), step=0.1, key="idvg_vd")
    idvg_vstart = col2.number_input("Vg Start (V)", value=float(cfg_idvg["vg_start"]), step=0.1, key="idvg_vstart")
    idvg_vstop = col3.number_input("Vg Stop (V)", value=float(cfg_idvg["vg_stop"]), step=0.1, key="idvg_vstop")
    idvg_vdep = col4.number_input("Deplete Voltage (V)", value=float(cfg_idvg["deplete_voltage"]), step=0.1, key="idvg_vdep")

    col5, col6, col7 = st.columns(3)
    idvg_wait = col5.number_input("Pre-Sweep Wait (s)", value=int(cfg_idvg["wait_time"]), step=1, key="idvg_wait")
    idvg_tdep = col6.number_input("Deplete Time (s)", value=int(cfg_idvg["deplete_time"]), step=1, key="idvg_tdep")
    
    # laser_val = "null" if cfg_idvg["laser_settings"] is None else json.dumps(cfg_idvg["laser_settings"])
    # idvg_laser = col7.text_input("Laser Settings (JSON or 'null')", value=laser_val, key="idvg_laser")

    # 1. Initialize the memory on the very first page load
    if "idvg_laser" not in st.session_state:
        st.session_state["idvg_laser"] = "null" if cfg_idvg["laser_settings"] is None else json.dumps(cfg_idvg["laser_settings"])
        
    # 2. Create the box WITHOUT the `value=` parameter! 
    # Streamlit will automatically pull the text directly from the session_state memory.
    idvg_laser = col4.text_input("Laser Settings (JSON or 'null')", key="idvg_laser")
    st.divider()


    st.subheader("🚀 Actions")
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        st.markdown("**Save Configuration**")
        if st.button("Update Id-Vg Config", type="primary", use_container_width=True, key="idvg_save_btn"):
            try:
                parsed_laser = None if idvg_laser.strip().lower() in ["null", "none", ""] else json.loads(idvg_laser)
                config_dict_idvg = {
                    "description": idvg_desc, "device_number": idvg_dev, "run_number": idvg_run, "label": idvg_label,
                    "vd_const": idvg_vd, "vg_start": idvg_vstart, "vg_stop": idvg_vstop,
                    "laser_settings": parsed_laser, "laser_stable_time": int(cfg_idvg["laser_stable_time"]),
                    "deplete_voltage": idvg_vdep, "deplete_time": idvg_tdep,
                    "current_limit_a": idvg_clim, "current_limit_b": idvg_clim,
                    "nplc_a": idvg_nplc, "nplc_b": idvg_nplc,
                    "num_points": idvg_num_pts, "wait_time": idvg_wait, "source_to_measure_delay": idvg_s2m
                }
                save_path = Path("config") / "idvg_config_app.json"
                with open(save_path, "w") as f: json.dump(config_dict_idvg, f, indent=4)
                st.success(f"✅ Saved to: {save_path.name}")
            except json.JSONDecodeError: st.error("Invalid JSON format in Laser Settings.")
            except Exception as e: st.error(f"Failed to save: {e}")

    with col_btn2:
        st.markdown("**Run Keithley Measurement**")
        if st.button("▶ Run idvg.py in Terminal", type="secondary", use_container_width=True, key="idvg_run_btn"):
            success, msg = launch_in_terminal("idvg.py")
            if success: st.success(msg)
            else: st.error(msg)
            
    with col_btn3:
        st.markdown("**Manual Hardware Control**")
        if st.button("⚙️ Open Servo GUI", type="secondary", use_container_width=True, key="idvg_servo"):
            success, msg = launch_in_terminal("servo_GUI.py")
            if success: st.success(msg)
            else: st.error(msg)


# ==========================================
# TAB 3: POWER CALIBRATION & VERIFICATION
# ==========================================
with tab_power:
    st.markdown("Set your target powers, run the calibration script, and verify the resulting tables.")

    st.subheader("1. Calibration Parameters")
    
    p_wav_def, p_ch_def, p_pow_def = "450, 532, 660", "0, 3, 6", "100, 200, 300"
    power_cfg_path = Path("config") / "power_config.json"
    if power_cfg_path.exists():
        with open(power_cfg_path, "r") as f:
            p_params = json.load(f)
            p_wav_def = ", ".join(map(str, p_params.get("wavelength_arr", [])))
            p_ch_def = ", ".join(map(str, p_params.get("channel_arr", [])))
            p_pow_def = ", ".join(map(str, p_params.get("power_arr", [])))

    col1, col2, col3 = st.columns(3)
    p_wavelength_str = col1.text_input("Wavelength Array (nm)", value=p_wav_def, key="p_wav")
    p_channel_str = col2.text_input("Channel Array", value=p_ch_def, key="p_ch")
    p_power_str = col3.text_input("Target Power Array (nW)", value=p_pow_def, key="p_pow")

    st.subheader("2. Run Scripts")
    p_col1, p_col2, p_col3 = st.columns(3)
    
    with p_col1:
        if st.button("💾 Save Power Config", type="primary", use_container_width=True):
            try:
                p_config_dict = {
                    "wavelength_arr": [int(x.strip()) for x in p_wavelength_str.split(",")],
                    "channel_arr": [int(x.strip()) for x in p_channel_str.split(",")],
                    "power_arr": [int(x.strip()) for x in p_power_str.split(",")]
                }
                power_cfg_path.parent.mkdir(parents=True, exist_ok=True)
                with open(power_cfg_path, "w") as f:
                    json.dump(p_config_dict, f, indent=4)
                st.success("✅ Saved to config/power_config.json")
            except Exception as e:
                st.error(f"Error saving: {e}")

    with p_col2:
        if st.button("▶ 1. Run power.py", type="secondary", use_container_width=True):
            success, msg = launch_in_terminal("power.py")
            if success: st.success(msg)
            else: st.error(msg)

    with p_col3:
        if st.button("▶ 2. Run verify_power.py", type="secondary", use_container_width=True):
            success, msg = launch_in_terminal("verify_power.py")
            if success: st.success(msg)
            else: st.error(msg)

    st.divider()

    st.subheader("3. Verification Results")
    st.markdown("Click **Refresh** after your terminal scripts finish to view the updated tables.")
    
    if st.button("🔄 Refresh Data Tables"):
        pass 

    data_col1, data_col2, data_col3 = st.columns(3)
    
    with data_col1:
        st.markdown("**1. `pp_df.csv` (Percent Power)**")
        pp_file = Path("calibration") / "pp_df.csv"
        if pp_file.exists():
            st.dataframe(pd.read_csv(pp_file, index_col=0), use_container_width=True)
        else:
            st.warning("File not found.")

    with data_col2:
        st.markdown("**2. `measured_power_df.csv` (Calibration)**")
        mp_file = Path("calibration") / "measured_power_df.csv"
        if mp_file.exists():
            st.dataframe(pd.read_csv(mp_file, index_col=0), use_container_width=True)
        else:
            st.warning("File not found.")

    with data_col3:
        st.markdown("**3. `verified_power_df.csv` (Verification)**")
        vp_file = Path("calibration") / "verified_power_df.csv"
        if vp_file.exists():
            st.dataframe(pd.read_csv(vp_file, index_col=0), use_container_width=True)
        else:
            st.warning("File not found.")
# ==========================================
# TAB 4: DATA PLOTTER & COMBINER (Interactive Plotly Upgrade)
# ==========================================
with tab_plot:
    st.markdown("Upload multiple `.csv` data files to overlay them on an interactive graph and merge them into one file.")
    
    # Drag-and-drop box for multiple files
    uploaded_data_files = st.file_uploader(
        "Select CSV Data Files", 
        type=["csv"], 
        accept_multiple_files=True, 
        key="data_uploader"
    )

    if uploaded_data_files:
        # Initialize an Interactive Plotly Figure
        fig = go.Figure()
        plot_type = None
        combined_dfs = []

        # Process each uploaded file
        for file in uploaded_data_files:
            try:
                df = pd.read_csv(file)
                df["Source_File"] = file.name
                combined_dfs.append(df)
                
                label = Path(file.name).stem

                # Auto-detect measurement type and add interactive traces
                if "idvg" in file.name.lower():
                    plot_type = "Id-Vg"
                    fig.add_trace(go.Scatter(
                        x=df["V_G"], y=df["I_D"].abs(), 
                        mode='lines+markers', name=label
                    ))
                    fig.update_yaxes(type="log", title_text="Drain Current |Id| (A)")
                    fig.update_xaxes(title_text="Gate Voltage Vg (V)")
                    
                elif "idvd" in file.name.lower():
                    plot_type = "Id-Vd"
                    fig.add_trace(go.Scatter(
                        x=df["V_D"], y=np.abs(df["I_D"]), 
                        mode='lines+markers', name=label
                    ))
                    fig.update_yaxes(type="log", title_text="Drain Current Id (A)")
                    fig.update_xaxes(title_text="Drain Voltage Vd (V)")
                    
                elif "time" in file.name.lower():
                    plot_type = "Time-Dependent"
                    fig.add_trace(go.Scatter(
                        x=df["Time"], y=df["I_D"], 
                        mode='lines+markers', name=label
                    ))
                    fig.update_yaxes(title_text="Drain Current Id (A)")
                    fig.update_xaxes(title_text="Time (s)")
                    
                else:
                    st.warning(f"Unknown measurement type for {file.name}. Plotting skipped.")

            except Exception as e:
                st.error(f"Error reading {file.name}: {e}")

        # Render the Interactive Plot in Streamlit
        if plot_type:
            # Add a title and a unified hover tooltip (compares all lines at the same X value)
            fig.update_layout(
                title=f"<b>Overlay Plot: {plot_type} Characteristics</b>",
                hovermode="x unified",
                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
                margin=dict(l=20, r=20, t=50, b=20)
            )
            
            # This is the magic Streamlit command for interactive plots!
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No valid data recognized for plotting.")

        # Merge and Download Section
        if combined_dfs:
            st.divider()
            st.subheader("💾 Combined Data Export")
            st.markdown("All selected files have been merged into a single dataframe. The column `Source_File` indicates where each row originated.")
            
            final_df = pd.concat(combined_dfs, ignore_index=True)
            st.dataframe(final_df.head(), use_container_width=True)
            
            csv_data = final_df.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="📥 Download Combined CSV",
                data=csv_data,
                file_name="combined_data.csv",
                mime="text/csv",
                type="primary"
            )


# ==========================================
# TAB 5: OPTICAL ENCODER & MEMORY
# ==========================================
with tab_encoder:
    st.markdown("Transmit custom ASCII messages or binary sequences using your laser and Keithley to test optical communication.")

    st.subheader("📂 Load Existing Configuration")
    uploaded_enc = st.file_uploader("Upload a previous JSON config", type=["json"], key="enc_uploader")

    cfg_enc = {
        "description": "Optical ASCII Test", "device_number": "1-1", "run_number": "1", "label": "encoder",
        "wait_time": 5, "current_limit_a": 1e-3, "current_limit_b": 1e-3, "current_range_a": 1e-5, "current_range_b": 1e-5,
        "nplc_a": 1.0, "nplc_b": 1.0, "vd_const": 1.0, "vg_on": 1.0, "vg_off": -1.0,
        "wavelength_arr": [660], "channel_arr": [6], "power_arr": [100],
        "binary_string": "01001000", "bit_duration": 1.0
    }

    if uploaded_enc is not None:
        if st.session_state.get("last_uploaded_enc") != uploaded_enc.name:
            try:
                cfg_enc.update(json.load(uploaded_enc))
                st.session_state["enc_desc"] = str(cfg_enc.get("description", ""))
                st.session_state["enc_dev"] = str(cfg_enc.get("device_number", ""))
                st.session_state["enc_run"] = str(cfg_enc.get("run_number", ""))
                st.session_state["enc_lbl"] = str(cfg_enc.get("label", ""))
                st.session_state["enc_wait"] = int(cfg_enc.get("wait_time", 5))
                st.session_state["enc_clim_a"] = float(cfg_enc.get("current_limit_a", 1e-3))
                st.session_state["enc_clim_b"] = float(cfg_enc.get("current_limit_b", 1e-3))
                st.session_state["enc_crng_a"] = float(cfg_enc.get("current_range_a", 1e-5))
                st.session_state["enc_crng_b"] = float(cfg_enc.get("current_range_b", 1e-5))
                st.session_state["enc_nplc_a"] = float(cfg_enc.get("nplc_a", 1.0))
                st.session_state["enc_nplc_b"] = float(cfg_enc.get("nplc_b", 1.0))
                st.session_state["enc_vd"] = float(cfg_enc.get("vd_const", 1.0))
                st.session_state["enc_vgon"] = float(cfg_enc.get("vg_on", 1.0))
                st.session_state["enc_vgoff"] = float(cfg_enc.get("vg_off", -1.0))
                st.session_state["enc_wav"] = ", ".join(map(str, cfg_enc.get("wavelength_arr", [660])))
                st.session_state["enc_ch"] = ", ".join(map(str, cfg_enc.get("channel_arr", [6])))
                st.session_state["enc_pw"] = ", ".join(map(str, cfg_enc.get("power_arr", [100])))
                st.session_state["enc_bitdur"] = float(cfg_enc.get("bit_duration", 1.0))
                
                # Load the raw binary string from the file
                st.session_state["enc_raw_bin"] = str(cfg_enc.get("binary_string", "01001000"))
                
                st.session_state["last_uploaded_enc"] = uploaded_enc.name
                st.success(f"✅ Loaded: **{uploaded_enc.name}** - You can now make manual edits!")
            except Exception as e:
                st.error(f"Failed to read JSON: {e}")
    else:
        st.session_state["last_uploaded_enc"] = None

    st.divider()

    # --- THE NEW ASCII ENCODER SECTION ---
    st.subheader("📡 Encoding Sequence")
    
    enc_mode = st.radio("Encoding Mode", ["ASCII Text", "Raw Binary"], horizontal=True, key="enc_mode")
    
    col_e1, col_e2 = st.columns([3, 1])
    
    final_bin = ""
    if enc_mode == "ASCII Text":
        raw_msg = col_e1.text_input("Message to Transmit", value="Hi", key="enc_ascii_msg")
        # Python magic to convert text to 8-bit binary strings
        final_bin = "".join([format(ord(c), '08b') for c in raw_msg])
        st.caption(f"📠 **Live Translation ({len(final_bin)} bits):** `{final_bin}`")
    else:
        raw_bin = col_e1.text_input("Binary String (1s and 0s)", value=str(cfg_enc.get("binary_string", "01001000")), key="enc_raw_bin")
        final_bin = "".join([c for c in raw_bin if c in ['0', '1']])
        if raw_bin != final_bin:
            st.caption(f"⚠️ *Filtered invalid characters. Transmitting:* `{final_bin}`")
            
    enc_bitdur = col_e2.number_input("Bit Duration (s)", value=float(cfg_enc["bit_duration"]), step=0.1, key="enc_bitdur")
    
    # Calculate Total Expected Time
    total_time = len(final_bin) * (enc_bitdur * 1.5) + 10 # 1.5 multiplier accounts for the Return-to-Zero rest period
    st.info(f"⏱️ **Estimated Transmission Time:** ~{total_time:.1f} seconds")

    st.divider()

    st.subheader("📝 General & Keithley")
    col1, col2, col3, col4 = st.columns(4)
    enc_desc = col1.text_input("Description", value=str(cfg_enc["description"]), key="enc_desc")
    enc_dev = col2.text_input("Device Number", value=str(cfg_enc["device_number"]), key="enc_dev")
    enc_run = col3.text_input("Run Number", value=str(cfg_enc["run_number"]), key="enc_run")
    enc_wait = col4.number_input("Wait Time (s)", value=int(cfg_enc["wait_time"]), min_value=0, step=1, key="enc_wait")

    col5, col6, col7 = st.columns(3)
    with col5:
        enc_clim_a = st.number_input("Current Limit A (A)", value=float(cfg_enc["current_limit_a"]), format="%e", key="enc_clim_a")
        enc_clim_b = st.number_input("Current Limit B (A)", value=float(cfg_enc["current_limit_b"]), format="%e", key="enc_clim_b")
    with col6:
        enc_crng_a = st.number_input("Current Range A (A)", value=float(cfg_enc["current_range_a"]), format="%e", key="enc_crng_a")
        enc_crng_b = st.number_input("Current Range B (A)", value=float(cfg_enc["current_range_b"]), format="%e", key="enc_crng_b")
    with col7:
        enc_nplc_a = st.number_input("NPLC A", value=float(cfg_enc["nplc_a"]), step=0.1, key="enc_nplc_a")
        enc_nplc_b = st.number_input("NPLC B", value=float(cfg_enc["nplc_b"]), step=0.1, key="enc_nplc_b")

    st.divider()

    st.subheader("⚡ Optics & Voltages")
    col1, col2, col3 = st.columns(3)
    enc_vd = col1.number_input("Vd Const (V)", value=float(cfg_enc["vd_const"]), step=0.1, key="enc_vd")
    enc_vgon = col2.number_input("Vg ON (1 State)", value=float(cfg_enc["vg_on"]), step=0.1, key="enc_vgon")
    enc_vgoff = col3.number_input("Vg OFF (0 State)", value=float(cfg_enc["vg_off"]), step=0.1, key="enc_vgoff")

    st.caption("Note: The Encoder script only uses the FIRST value in these arrays.")
    col4, col5, col6 = st.columns(3)
    enc_wav = col4.text_input("Wavelength (nm)", value=", ".join(map(str, cfg_enc["wavelength_arr"])), key="enc_wav")
    enc_ch = col5.text_input("Channel", value=", ".join(map(str, cfg_enc["channel_arr"])), key="enc_ch")
    enc_pw = col6.text_input("Power (nW)", value=", ".join(map(str, cfg_enc["power_arr"])), key="enc_pw")

    st.divider()

    st.subheader("🚀 Actions")
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        st.markdown("**Save Configuration**")
        if st.button("Update Encoder Config", type="primary", use_container_width=True, key="enc_save"):
            try:
                wav_arr = [int(x.strip()) for x in enc_wav.split(",")]
                ch_arr = [int(x.strip()) for x in enc_ch.split(",")]
                pw_arr = [int(x.strip()) for x in enc_pw.split(",")]

                config_dict_enc = {
                    "description": enc_desc, "device_number": enc_dev, "run_number": enc_run, "label": st.session_state.get("enc_lbl", "encoder"),
                    "current_limit_a": enc_clim_a, "current_limit_b": enc_clim_b,
                    "current_range_a": enc_crng_a, "current_range_b": enc_crng_b,
                    "nplc_a": enc_nplc_a, "nplc_b": enc_nplc_b,
                    "vd_const": enc_vd, "vg_on": enc_vgon, "vg_off": enc_vgoff,
                    "wavelength_arr": wav_arr, "channel_arr": ch_arr, "power_arr": pw_arr,
                    "binary_string": final_bin, "bit_duration": enc_bitdur, "wait_time": enc_wait
                }
                
                save_path = Path("config") / "time_dependent_config_encode_app.json"
                save_path.parent.mkdir(parents=True, exist_ok=True) 
                with open(save_path, "w") as f:
                    json.dump(config_dict_enc, f, indent=4)
                st.success("✅ Saved Config!")

            except Exception as e:
                st.error(f"Failed to save file: {e}")

    with col_btn2:
        st.markdown("**Run Keithley Measurement**")
        if st.button("▶ Run Encoder in Terminal", type="secondary", use_container_width=True, key="enc_run_btn"):
            success, msg = launch_in_terminal("time_dep_servo_encode_app.py")
            if success: st.success(msg)
            else: st.error(msg)
            
    with col_btn3:
        st.markdown("**Manual Hardware Control**")
        if st.button("⚙️ Open Servo GUI", type="secondary", use_container_width=True, key="enc_servo"):
            success, msg = launch_in_terminal("servo_GUI.py")
            if success: st.success(msg)
            else: st.error(msg)