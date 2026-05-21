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
    
    # --- SECTION 2: LASER STATUS ---
    st.subheader("📸 Laser PC Status")
    st.markdown("Take a snapshot of the AOTF Controller GUI running on the Laser PC.")
    
    l_col1, l_col2 = st.columns([1, 3])
    laser_ip = l_col1.text_input("Laser PC IP", value="10.0.0.2", key="func_laser_ip")
    
    if l_col2.button("Take AOTF Snapshot", use_container_width=True, key="func_snapshot_btn"):
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
