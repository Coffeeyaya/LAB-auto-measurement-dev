import streamlit as st
import json
import time
from pathlib import Path
from tabs.helper import launch_in_terminal

def render_encoder_tab():
    st.title("📡 Optical Encoder")
    st.markdown("Transmit custom ASCII messages or binary sequences by pulsing the device at `Vg ON` and toggling the laser for `1`s and `0`s.")

    # 1. Initialize defaults
    default_cfg = {
        "enc_description": "Optical ASCII Test", "enc_device_number": "1-1", "enc_run_number": "1", "enc_label": "encoder",
        "enc_wait_time": 5, "enc_current_limit_a": 1e-3, "enc_current_limit_b": 1e-3, 
        "enc_current_range_a": 1e-5, "enc_current_range_b": 1e-5,
        "enc_nplc_a": 1.0, "enc_nplc_b": 1.0, "enc_vd_const": 1.0, 
        
        # Voltages for pulsing
        "enc_vg_on": 1.0, "enc_base_vg": 0.0, "enc_pulse_width": 0.005, "enc_rest_time": 0.1,
        
        "enc_binary_string": "01001000", "enc_bit_duration": 2.0,
        "enc_raw_message": "Hi",
        "enc_wavelength": 660, "enc_channel": 6, "enc_power": 100.0
    }

    for k, v in default_cfg.items():
        if k not in st.session_state:
            st.session_state[k] = v

    st.subheader("📂 Load Existing Configuration")
    if "enc_uploader_key" not in st.session_state: st.session_state["enc_uploader_key"] = 0
    uploaded_enc = st.file_uploader("Upload a previous JSON config", type=["json"], key=f"enc_uploader_{st.session_state['enc_uploader_key']}")

    if uploaded_enc is not None:
        try:
            uploaded_cfg = json.load(uploaded_enc)
            for k, v in uploaded_cfg.items():
                st.session_state[f"enc_{k}"] = str(v) if k in ["run_number", "device_number", "description", "label"] else v
            st.session_state["enc_uploader_key"] += 1
            st.rerun()
        except Exception as e:
            st.error(f"Failed to read JSON file: {e}")

    st.divider()

    # ==========================================
    # ENCODING ENGINE
    # ==========================================
    st.subheader("1. Message Payload")
    enc_mode = st.radio("Encoding Mode", ["ASCII Text", "Raw Binary"], horizontal=True, key="enc_mode")
    col_e1, col_e2 = st.columns([3, 1])
    
    final_bin = ""
    if enc_mode == "ASCII Text":
        raw_msg = col_e1.text_input("Message to Transmit", key="enc_raw_message")
        final_bin = "".join([format(ord(c), '08b') for c in raw_msg])
        st.caption(f"📠 **Live Translation ({len(final_bin)} bits):** `{final_bin}`")
    else:
        raw_bin = col_e1.text_input("Binary String (1s and 0s)", key="enc_binary_string")
        final_bin = "".join([c for c in str(raw_bin) if c in ['0', '1']])
        if str(raw_bin) != final_bin: st.caption(f"⚠️ *Filtered invalid characters. Transmitting:* `{final_bin}`")
            
    col_e2.number_input("Bit Duration (s)", step=0.1, key="enc_bit_duration", help="How long each bit holds the Vg state before moving to the next bit")
    total_time = len(final_bin) * st.session_state["enc_bit_duration"] + 16 
    st.info(f"⏱️ **Estimated Transmission Time:** ~{total_time:.1f} seconds")

    st.divider()

    # ==========================================
    # UI WIDGETS
    # ==========================================
    st.subheader("2. Measurement Settings")
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

    st.subheader("⚡ Electrical Pulse Settings")
    col_v1, col_v2, col_v3, col_v4, col_v5 = st.columns(5)
    col_v1.number_input("Vd Const (V)", step=0.1, key="enc_vd_const")
    col_v2.number_input("Target Vg [Pulse] (V)", step=0.1, key="enc_vg_on")
    col_v3.number_input("Base Vg [Rest] (V)", step=0.1, key="enc_base_vg")
    col_v4.number_input("Pulse Width (s)", step=0.001, format="%f", key="enc_pulse_width")
    col_v5.number_input("Rest Time (s)", step=0.01, format="%f", key="enc_rest_time")

    st.subheader("🔦 Laser Configuration (For Binary '1' State)")
    col_o1, col_o2, col_o3 = st.columns(3)
    col_o1.number_input("Wavelength (nm)", step=1, key="enc_wavelength")
    col_o2.number_input("Channel", step=1, key="enc_channel")
    col_o3.number_input("Power (nW)", step=10.0, key="enc_power")

    st.divider()

    # ==========================================
    # ACTIONS & SAVING
    # ==========================================
    st.subheader("🚀 Add to Time-Pulse Queue")
    
    queue_dir = Path("config/time_pulse_queue")
    queue_dir.mkdir(exist_ok=True, parents=True)
    queued_files = sorted(list(queue_dir.glob("*.json")))

    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        if st.button("➕ Add Encoder Config to Queue", type="primary", use_container_width=True, key="enc_save"):
            if not final_bin:
                st.error("No message or binary string provided!")
            else:
                config_dict_enc = {
                    "hardware_mode": "Optical Encoder",  # Signals the backend parser!
                    "electrical_mode": "Pulsed Vg Train",
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
                    "base_vg": st.session_state["enc_base_vg"],
                    "pulse_width": st.session_state["enc_pulse_width"],
                    "rest_time": st.session_state["enc_rest_time"],
                    "wavelength": st.session_state["enc_wavelength"], 
                    "channel": st.session_state["enc_channel"], 
                    "power": st.session_state["enc_power"],
                    "binary_string": final_bin, 
                    "bit_duration": st.session_state["enc_bit_duration"], 
                    "wait_time": st.session_state["enc_wait_time"]
                }
                
                next_idx = len(queued_files) + 1
                filename = f"{next_idx:02d}_Encoder_{st.session_state['enc_device_number']}.json"
                
                with open(queue_dir / filename, "w") as f:
                    json.dump(config_dict_enc, f, indent=4)
                    
                st.success(f"✅ Saved to: {filename}")
                time.sleep(0.5)
                st.rerun()

    with col_btn2:
        if st.button("▶ Run Script in Terminal", type="secondary", use_container_width=True, key="enc_run_btn"):
            if not queued_files:
                st.error("The queue is empty! Add a configuration first.")
            else:
                success, msg = launch_in_terminal("run_time_pulse.py")
                if success: st.success(msg)
                else: st.error(msg)