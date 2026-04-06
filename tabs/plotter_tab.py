import streamlit as st
from tabs.helper import launch_in_terminal

def render_plotter_tab():
    st.markdown("Visualize your Keithley measurement results using the interactive plotting application.")
    
    st.divider()

    st.subheader("📊 Interactive Data Plotter")
    st.write("Launch the standalone `plot_data.py` script in a new window to load, analyze, and save figures of your measurement data.")
    
    st.write("") # Add a little vertical spacing
    
    # Use columns to center the button and make it look visually balanced
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("▶ Launch Data Plotter", type="primary", use_container_width=True, key="plot_run_btn"):
            success, msg = launch_in_terminal("plot_data.py")
            if success: 
                st.success(msg)
            else: 
                st.error(msg)