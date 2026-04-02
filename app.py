import streamlit as st
from tabs.time_dependent import render_time_dependent_tab
from tabs.idvg import render_idvg_tab
from tabs.idvd import render_idvd_tab
from tabs.power import render_power_tab
from tabs.plotter import render_plotter_tab
from tabs.encoder import render_encoder_tab
from tabs.pulse import render_vg_pulse_tab

st.set_page_config(page_title="Lab Auto", layout="wide")
st.title("🔬 Lab Automation")

tab_time_dep, tab_idvg, tab_idvd, tab_power, tab_plot, tab_encoder, tab_vg_pulse = st.tabs([
    "⚡ Time-Dependent", 
    "📈 Id-Vg Sweep",
    "📈 Id-Vd Sweep",
    "🔦 Power Calibration", 
    "📊 Data Plotter",
    "📡 Optical Encoder",
    "VG pulse"
])

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

with tab_encoder:
    render_encoder_tab()

with tab_vg_pulse:
    render_vg_pulse_tab()