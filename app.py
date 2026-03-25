import streamlit as st
import json
from pathlib import Path
import os
import subprocess 

# --- Page Config ---
st.set_page_config(page_title="JSON Config Builder", layout="wide")
st.title("⚡ Measurement Config Builder")
st.markdown("Update your active configuration and launch the measurement.")

# --- 1. General Settings ---
st.subheader("📝 General Information")
col1, col2, col3, col4 = st.columns(4)
description = col1.text_input("Description", value="Standard Time-Dep")
device_number = col2.text_input("Device Number", value="1-1")
run_number = col3.text_input("Run Number", value="0")
wait_time = col4.number_input("Wait Time (s)", value=5, min_value=0, step=1)

st.divider()

# --- 2. Keithley SMU Settings ---
st.subheader("🔌 Keithley SMU Settings")
col1, col2, col3 = st.columns(3)

with col1:
    current_limit_a = st.number_input("Current Limit A (A)", value=1e-3, format="%e")
    current_limit_b = st.number_input("Current Limit B (A)", value=1e-3, format="%e")
with col2:
    current_range_a = st.number_input("Current Range A (A)", value=1e-5, format="%e")
    current_range_b = st.number_input("Current Range B (A)", value=1e-5, format="%e")
with col3:
    nplc_a = st.number_input("NPLC A", value=1.0, step=0.1)
    nplc_b = st.number_input("NPLC B", value=1.0, step=0.1)

st.divider()

# --- 3. Voltage Settings ---
st.subheader("⚡ Voltage Settings")
col1, col2, col3 = st.columns(3)
vd_const = col1.number_input("Vd Const (V)", value=2.0, step=0.1)
vg_on = col2.number_input("Vg ON (V)", value=1.0, step=0.1)
vg_off = col3.number_input("Vg OFF (V)", value=-1.0, step=0.1)

st.divider()

# --- 4. Laser / Array Settings ---
st.subheader("🔦 Optics & Arrays (Comma-separated)")
col1, col2, col3 = st.columns(3)
wavelength_str = col1.text_input("Wavelength Array (nm)", value="660, 660, 660")
channel_str = col2.text_input("Channel Array", value="6, 6, 6")
power_str = col3.text_input("Power Array (nW)", value="100, 100, 100")

st.divider()

# --- 5. Timing & Sequences ---
st.subheader("⏱️ Timing & Sequence Durations")
col1, col2, col3, col4 = st.columns(4)
duration_1 = col1.number_input("Duration 1 (s)", value=5.0, step=0.5)
duration_2 = col2.number_input("Duration 2 (s)", value=5.0, step=0.5)
duration_3 = col3.number_input("Duration 3 (s)", value=5.0, step=0.5)
duration_4 = col4.number_input("Duration 4 (s)", value=5.0, step=0.5)

col5, col6, col7 = st.columns(3)
cycle_number = col5.number_input("Cycle Number", value=3, min_value=1, step=1)
on_off_number = col6.number_input("ON/OFF Number", value=3, min_value=1, step=1)
servo_time = col7.number_input("Servo Time (s)", value=0.1, step=0.05)

st.divider()

# --- ACTION BUTTONS ---
st.subheader("🚀 Actions")

col_btn1, col_btn2 = st.columns(2)

# ACTION 1: Generate JSON Button 
with col_btn1:
    if st.button("Update JSON Config", type="primary", use_container_width=True):
        try:
            wavelength_arr = [int(x.strip()) for x in wavelength_str.split(",")]
            channel_arr = [int(x.strip()) for x in channel_str.split(",")]
            power_arr = [int(x.strip()) for x in power_str.split(",")]

            config_dict = {
                "description": description,
                "device_number": device_number,
                "run_number": run_number,
                "current_limit_a": current_limit_a,
                "current_limit_b": current_limit_b,
                "current_range_a": current_range_a,
                "current_range_b": current_range_b,
                "nplc_a": nplc_a,
                "nplc_b": nplc_b,
                "vd_const": vd_const,
                "vg_on": vg_on,
                "vg_off": vg_off,
                "duration_1": duration_1,
                "duration_2": duration_2,
                "duration_3": duration_3,
                "duration_4": duration_4,
                "wavelength_arr": wavelength_arr,
                "channel_arr": channel_arr,
                "power_arr": power_arr,
                "cycle_number": cycle_number,
                "on_off_number": on_off_number,
                "servo_time": servo_time,
                "wait_time": wait_time
            }

            json_string = json.dumps(config_dict, indent=4)
            
            # --- HARDCODED SAVE LOGIC ---
            save_path = Path("config")
            save_path.mkdir(parents=True, exist_ok=True) 
            full_path = save_path / "time_dependent_config_app.json"
            
            with open(full_path, "w") as f:
                f.write(json_string)

            st.success(f"✅ Success! Overwrote target file at: {full_path.absolute()}")

        except ValueError:
            st.error("Error formatting arrays! Ensure comma-separated numbers only.")
        except Exception as e:
            st.error(f"Failed to save file: {e}")

# ACTION 2: Run External Script Button
with col_btn2:
    # --- NEW: Drop-down menu instead of text input ---
    script_to_run = st.selectbox(
        "Select Measurement Script", 
        ("time_dep_servo.py", "time_dep.py", "time_dep_dark.py")
    )
    
    if st.button("▶ Run Selected Script", type="secondary", use_container_width=True):
        if not os.path.exists(script_to_run):
            st.error(f"Could not find script: {script_to_run}")
        else:
            try:
                import sys
                subprocess.Popen([sys.executable, script_to_run])
                st.success(f"🚀 Successfully launched {script_to_run}!")
            except Exception as e:
                st.error(f"Failed to launch script: {e}")