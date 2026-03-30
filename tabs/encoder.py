import streamlit as st
import json
from pathlib import Path
from tabs.helper import launch_in_terminal

def render_encoder_tab():
    st.markdown("Transmit custom ASCII messages or binary sequences using your laser and Keithley to test optical communication.")

    # 1. Initialize prefixed defaults
    default_cfg = {
        "enc_description": "Optical ASCII Test", "enc_device_number": "1-1", "enc_run_number": "1", "enc_label": "encoder",
        "enc_wait_time": 5, "enc_current_limit_a": 1e-3, "enc_current_limit_b": 1e-3, 
        "enc_current_range_a": 1e-5, "enc_current_range_b": 1e-5,
        "enc_nplc_a": 1.0, "enc_nplc_b": 1.0, "enc_vd_const": 1.0, "enc_vg_on": 1.0, "enc_vg_off": -1.0,
        "enc_binary_string": "01001000", "enc_bit_duration": 1.0,
        "enc_raw_message": "Hi"  # <--- NEW: Add this line!
    }

    for k, v in default_cfg.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Arrays need to be stored as comma-separated strings for the UI text boxes
    if "enc_wavelength_str" not in st.session_state: st.session_state["enc_wavelength_str"] = "660"
    if "enc_channel_str" not in st.session_state: st.session_state["enc_channel_str"] = "6"
    if "enc_power_str" not in st.session_state: st.session_state["enc_power_str"] = "100"

    st.subheader("📂 Load Existing Configuration")
    
    # 2. Setup the dynamic uploader key for the "Self-Clearing" trick
    if "enc_uploader_key" not in st.session_state: 
        st.session_state["enc_uploader_key"] = 0

    uploaded_enc = st.file_uploader(
        "Upload a previous JSON config", 
        type=["json"], 
        key=f"enc_uploader_{st.session_state['enc_uploader_key']}"
    )

    if uploaded_enc is not None:
        try:
            uploaded_cfg = json.load(uploaded_enc)
            
            # Forcefully inject JSON values directly into the Widget Memory Keys
            for k, v in uploaded_cfg.items():
                if k in ["wavelength_arr", "channel_arr", "power_arr"]:
                    st.session_state[f"enc_{k.split('_')[0]}_str"] = ", ".join(map(str, v))
                else:
                    st.session_state[f"enc_{k}"] = v
            
            # Clear the uploader box and restart instantly
            st.session_state["enc_uploader_key"] += 1
            st.rerun()
            
        except Exception as e:
            st.error(f"Failed to read JSON file: {e}")

    st.divider()

    # ==========================================
    # ENCODING ENGINE
    # ==========================================
    st.subheader("📡 Encoding Sequence")
    
    # Select mode
    enc_mode = st.radio("Encoding Mode", ["ASCII Text", "Raw Binary"], horizontal=True, key="enc_mode")
    
    col_e1, col_e2 = st.columns([3, 1])
    
    final_bin = ""
    if enc_mode == "ASCII Text":
        # --- NEW: Added the key parameter so it saves to memory ---
        raw_msg = col_e1.text_input("Message to Transmit", key="enc_raw_message")
        
        # Python magic to convert text to 8-bit binary strings
        final_bin = "".join([format(ord(c), '08b') for c in raw_msg])
        st.caption(f"📠 **Live Translation ({len(final_bin)} bits):** `{final_bin}`")
    else:
        # Directly edit the memory-backed raw binary string
        raw_bin = col_e1.text_input("Binary String (1s and 0s)", key="enc_binary_string")
        # Filter out accidental characters
        final_bin = "".join([c for c in str(raw_bin) if c in ['0', '1']])
        if str(raw_bin) != final_bin:
            st.caption(f"⚠️ *Filtered invalid characters. Actually transmitting:* `{final_bin}`")
            
    col_e2.number_input("Bit Duration (s)", step=0.1, key="enc_bit_duration")
    
    # Calculate Total Expected Time
    # 1.5 multiplier accounts for the Return-to-Zero rest period
    total_time = len(final_bin) * (st.session_state["enc_bit_duration"] * 1.5) + 10 
    st.info(f"⏱️ **Estimated Transmission Time:** ~{total_time:.1f} seconds")

    st.divider()

    # ==========================================
    # UI WIDGETS (All keys prefixed with enc_)
    # ==========================================
    st.subheader("📝 General & Keithley")
    col1, col2, col3, col4 = st.columns(4)
    col1.text_input("Description", key="enc_description")
    col2.text_input("Device Number", key="enc_device_number")
    col3.text_input("Run Number", key="enc_run_number")
    col4.number_input("Wait Time (s)", min_value=0, step=1, key="enc_wait_time")

    col5, col6, col7 = st.columns(3)
    with col5:
        st.number_input("Current Limit A (A)", format="%e", step=1e-4, key="enc_current_limit_a")
        st.number_input("Current Limit B (A)", format="%e", step=1e-4, key="enc_current_limit_b")
    with col6:
        st.number_input("Current Range A (A)", format="%e", step=1e-6, key="enc_current_range_a")
        st.number_input("Current Range B (A)", format="%e", step=1e-6, key="enc_current_range_b")
    with col7:
        st.number_input("NPLC A", step=0.1, key="enc_nplc_a")
        st.number_input("NPLC B", step=0.1, key="enc_nplc_b")

    st.divider()

    st.subheader("⚡ Optics & Voltages")
    col1, col2, col3 = st.columns(3)
    col1.number_input("Vd Const (V)", step=0.1, key="enc_vd_const")
    col2.number_input("Vg ON (1 State)", step=0.1, key="enc_vg_on")
    col3.number_input("Vg OFF (0 State)", step=0.1, key="enc_vg_off")

    st.caption("Note: The Encoder script only uses the FIRST value in these arrays.")
    col4, col5, col6 = st.columns(3)
    col4.text_input("Wavelength (nm)", key="enc_wavelength_str")
    col5.text_input("Channel", key="enc_channel_str")
    col6.text_input("Power (nW)", key="enc_power_str")

    st.divider()

    # ==========================================
    # ACTIONS & SAVING
    # ==========================================
    st.subheader("🚀 Actions")
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        st.markdown("**Save Configuration**")
        if st.button("Update Encoder Config", type="primary", use_container_width=True, key="enc_save"):
            try:
                # Convert the comma-separated strings back into arrays
                wav_arr = [int(x.strip()) for x in st.session_state["enc_wavelength_str"].split(",")]
                ch_arr = [int(x.strip()) for x in st.session_state["enc_channel_str"].split(",")]
                pw_arr = [float(x.strip()) for x in st.session_state["enc_power_str"].split(",")]

                # Construct the final dictionary by stripping the "enc_" prefix
                config_dict_enc = {
                    "description": st.session_state["enc_description"], 
                    "device_number": st.session_state["enc_device_number"], 
                    "run_number": st.session_state["enc_run_number"], 
                    "label": st.session_state.get("enc_label", "encoder"),
                    "current_limit_a": st.session_state["enc_current_limit_a"], 
                    "current_limit_b": st.session_state["enc_current_limit_b"],
                    "current_range_a": st.session_state["enc_current_range_a"], 
                    "current_range_b": st.session_state["enc_current_range_b"],
                    "nplc_a": st.session_state["enc_nplc_a"], 
                    "nplc_b": st.session_state["enc_nplc_b"],
                    "vd_const": st.session_state["enc_vd_const"], 
                    "vg_on": st.session_state["enc_vg_on"], 
                    "vg_off": st.session_state["enc_vg_off"],
                    "wavelength_arr": wav_arr, 
                    "channel_arr": ch_arr, 
                    "power_arr": pw_arr,
                    "raw_message": st.session_state.get("enc_raw_message", ""),
                    "binary_string": final_bin, # Write the active binary string!
                    "bit_duration": st.session_state["enc_bit_duration"], 
                    "wait_time": st.session_state["enc_wait_time"]
                }
                
                # Save it to the config folder
                save_path = Path("config") / "FORMAL_time_dependent_config_encode_app.json"
                save_path.parent.mkdir(parents=True, exist_ok=True) 
                
                with open(save_path, "w") as f:
                    json.dump(config_dict_enc, f, indent=4)
                    
                st.success(f"✅ Saved to: {save_path.name}")
                
                # Render the expandable JSON Preview
                with st.expander("👀 Preview Saved Configuration", expanded=True):
                    st.json(config_dict_enc)

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