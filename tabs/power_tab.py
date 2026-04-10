import streamlit as st
import json
import pandas as pd
import numpy as np
# import matplotlib.pyplot as plt
from pathlib import Path
from tabs.helper import launch_in_terminal

def render_power_tab():
    st.markdown("Set your target powers, run the calibration script, and verify the resulting tables.")

    st.subheader("1. Calibration Parameters")
    
    p_wav_def, p_ch_def, p_pow_def = "660", "6", "100"
    power_cfg_path = Path("config") / "power_config.json"
    if power_cfg_path.exists():
        with open(power_cfg_path, "r") as f:
            p_params = json.load(f)
            p_wav_def = ", ".join(map(str, p_params.get("wavelength_arr", [])))
            p_ch_def = ", ".join(map(str, p_params.get("channel_arr", [])))
            p_pow_def = ", ".join(map(str, p_params.get("power_arr", [])))

    col1, col2, col3 = st.columns(3)
    p_wavelength_str = col1.text_input("Wavelength Array (nm)", value=p_wav_def, key="p_wav", help='comma separated')
    p_channel_str = col2.text_input("Channel Array", value=p_ch_def, key="p_ch", help='comma separated')
    p_power_str = col3.text_input("Target Power Array (nW)", value=p_pow_def, key="p_pow", help='comma separated')

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