import streamlit as st
import base64
import time
from pathlib import Path
from tabs.helper import launch_in_terminal
from LabAuto.laser_remote import LaserController

def render_functionalities_tab():
    st.header("🛠️ Extra Functionalities")
    st.markdown("Centralized control for hardware utilities and status monitoring.")
    
    st.divider()
    
    # --- SECTION 1: SERVO CONTROL ---
    st.subheader("⚙️ Servo Motor Control")
    st.write("Launch the standalone GUI to manually control the physical shutter.")
    if st.button("Open Servo GUI", type="primary", use_container_width=True, key="func_servo_btn"):
        success, msg = launch_in_terminal("servo_GUI.py")
        if success: st.success(msg)
        else: st.error(msg)
        
    st.divider()
    
    # --- SECTION 2: LASER CONTROL ---
    st.subheader("🔦 Remote Laser Control")
    st.markdown("Quickly toggle laser channels or take a status snapshot.")
    
    l_col1, l_col2, l_col3 = st.columns([1, 1, 2])
    laser_ip = l_col1.text_input("Laser PC IP", value="10.0.0.2", key="func_laser_ip")
    selected_ch = l_col2.selectbox("Select Channel", options=list(range(8)), index=6, key="func_laser_ch")
    
    if l_col3.button("Toggle Channel ON/OFF", type="secondary", use_container_width=True, key="func_toggle_btn"):
        try:
            with st.spinner(f"Toggling Channel {selected_ch}..."):
                laser = LaserController(laser_ip, 5001)
                # 'on': 1 triggers the press_on_button in the backend
                response = laser.send_cmd({"channel": selected_ch, "on": 1}, wait_for_reply=True)
                laser.close()
            
            if response and response.get("response") == "ACK":
                st.success(f"✅ Channel {selected_ch} toggled.")
            else:
                st.error(f"Failed to toggle: {response}")
        except Exception as e:
            st.error(f"Connection Error: {e}")

    st.write("")
    if st.button("Take AOTF Snapshot", use_container_width=True, key="func_snapshot_btn"):
        try:
            with st.spinner("Connecting to Laser PC..."):
                laser = LaserController(laser_ip, 5001)
                response = laser.send_cmd({"command": "snapshot"}, wait_for_reply=True)
                laser.close()
            
            if response and response.get("response") == "SUCCESS":
                img_data = base64.b64decode(response.get("image"))
                st.image(img_data, caption=f"AOTF Controller Snapshot ({time.strftime('%H:%M:%S')})")
            else:
                st.error(f"Failed to get snapshot: {response.get('message', 'Unknown error')}")
        except Exception as e:
            st.error(f"Connection Error: {e}")
