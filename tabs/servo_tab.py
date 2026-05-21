import streamlit as st
from tabs.helper import launch_in_terminal

def render_servo_tab():
    st.write("") 
    if st.button("⚙️ Open Servo GUI", type="secondary", use_container_width=True, key="td_servo_btn_outside"):
        success, msg = launch_in_terminal("servo_GUI.py")
        if success: st.success(msg)
        else: st.error(msg)