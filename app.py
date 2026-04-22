import streamlit as st
from tabs.servo_tab import render_servo_tab
from tabs.time_dependent_tab import render_time_dependent_tab
from tabs.idvg_tab import render_idvg_tab
from tabs.idvd_tab import render_idvd_tab
from tabs.power_tab import render_power_tab
from tabs.plotter_tab import render_plotter_tab
from tabs.batch_tab import render_batch_generator_tab
from tabs.encoder import render_encoder_tab
from tabs.pulse_tab import render_vg_pulse_tab
from tabs.build_block_tab import render_build_block_tab


import atexit
import shutil
import os

# --- CLEANUP ON SERVER SHUTDOWN ---
def cleanup_temp_files():
    if os.path.exists("temp_data"):
        shutil.rmtree("temp_data")
    if os.path.exists("plot_config.json"):
        os.remove("plot_config.json")
    print("🧹 Server shutting down. Temporary files deleted.")

# Register the cleanup function to run when the script exits
atexit.register(cleanup_temp_files)

st.set_page_config(page_title="Lab Auto", layout="wide")
st.title("Lab Automation")

tab_servo, tab_time_dep, tab_idvg, tab_idvd, tab_power, tab_plot, tab_batch_generator, tab_block, tab_encoder, tab_vg_pulse  = st.tabs([
    "Servo motor control", 
    "⚡ Time-Dependent", 
    "📈 Id-Vg Sweep",
    "📈 Id-Vd Sweep",
    "🔦 Power Calibration", 
    "📊 Data Plotter",
    "Batch Generator",
    "Build block",
    "📡 Optical Encoder",
    "VG pulse"
])

with tab_servo:
    render_servo_tab()

with tab_time_dep:
    render_time_dependent_tab()

with tab_idvg:
    render_idvg_tab()

with tab_idvd:
    render_idvd_tab()

with tab_power:
    render_power_tab()

with tab_plot:
    render_plotter_tab()

with tab_batch_generator:
    render_batch_generator_tab()

with tab_block:
    render_build_block_tab()

with tab_encoder:
    render_encoder_tab()

# with tab_vg_pulse:
#     render_vg_pulse_tab()

