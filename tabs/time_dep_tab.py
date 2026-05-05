import streamlit as st
import json
import time
from pathlib import Path
from tabs.helper import launch_in_terminal

def move_block(index, direction):
    """Helper function to interchange custom sequence blocks in the session state."""
    blocks = st.session_state["sequence_blocks"]
    if direction == "up" and index > 0:
        blocks.insert(index - 1, blocks.pop(index))
    elif direction == "down" and index < len(blocks) - 1:
        blocks.insert(index + 1, blocks.pop(index))

def render_new_time_dependent_tab():

    ### Initialize default values in session state (streamlit memory)
    default_cfg = {
        "description": "Time-Dep", "device_number": "1-1", "run_number": "1", "time_label": "", "wait_time": 0,
        "current_limit_a": 0.001, "current_limit_b": 0.001, "current_range_a": 1e-06, "current_range_b": 1e-06,
        "nplc_a": 1.0, "nplc_b": 1.0, 
        "vd_const": 1.0, "vg_const": 0.0,
        "vg_on": 1.0, "vg_off": 0.0,
        "duration_1": 1.0, "duration_2": 1.0, "duration_3": 2.0, "duration_4": 2.0,
        "cycle_number": 3, "on_off_number": 1, "servo_time_on": 1.0, "servo_time_off": 1.0,
        
        # Pulse-specific parameters
        "base_vg": 0.0, "pulse_width": 0.001, "rest_time": 0.3,

        # Baseline Reset parameters
        "target_baseline": 1e-11, "timeout": 600,
        
        # Custom Blocks parameters
        "sequence_blocks": [
            {"type": "Dark Bias", "duration": 1.0, "vg": 0.0},
            {"type": "Dark Bias", "duration": 1.0, "vg": 1.0}
        ],
        "bb_def_channel": 6, "bb_def_wavelength": 660, "bb_def_power": 100.0,
        
        # The Two-Tiered UI states
        "hardware_mode": "Dark Current", 
        "electrical_mode": "Continuous DC Vg"
    }

    # Ensure keys are ALWAYS in session_state
    for k, v in default_cfg.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if "wavelength_str" not in st.session_state: st.session_state["wavelength_str"] = "660"
    if "channel_str" not in st.session_state: st.session_state["channel_str"] = "6"
    if "power_str" not in st.session_state: st.session_state["power_str"] = "100"

    ### Load old config files (Handles standard AND custom block JSONs)
    st.subheader("📂 Load Existing Configuration (Optional)")
    if "new_td_uploader_key" not in st.session_state: 
        st.session_state["new_td_uploader_key"] = 0

    uploaded_file = st.file_uploader(
        "Upload a previous JSON config to pre-fill the form", 
        type=["json"], 
        key=f"new_td_uploader_key_{st.session_state['new_td_uploader_key']}"
    )

    if uploaded_file is not None:
        uploaded_config = json.load(uploaded_file)
        
        # Loop through the uploaded JSON and push it to session_state
        for key, value in uploaded_config.items():
            if key in ["run_number", "device_number", "description", "time_label"]:
                st.session_state[key] = str(value)
            elif key == "sequence_blocks":
                st.session_state["sequence_blocks"] = value
            else:
                st.session_state[key] = value
                
        # --- THE AUTO-DELETE TRICK ---
        st.session_state["new_td_uploader_key"] += 1
        st.toast(f"✅ Loaded config: {uploaded_file.name}")
        st.rerun()

    st.divider()

    ### Select Mode
    col_mode1, col_mode2 = st.columns(2)
    
    with col_mode1:
        st.subheader("🛠️ Hardware Setup")
        hardware = st.radio(
            "Select physical configuration:",
            ["Dark Current", "Laser Only", "Laser + Servo", "Baseline Reset", "Baseline Reset @ Vg", "Custom Blocks"], 
            key="hardware_mode"
        )
        
    with col_mode2:
        st.subheader("⚡ Electrical Mode")
        electric = st.radio(
            "Select Gate Voltage behavior:",
            ["Continuous DC Vg", "Pulsed Vg Train"],
            key="electrical_mode",
        )

    st.divider()

    ### UI widgets
    st.subheader("📝 General Information")
    col1, col2, col3, col4 = st.columns(4)
    col1.text_input("Description", key="description", help="Take notes here")
    col2.text_input("Device Number", key="device_number")
    col3.text_input("Run Number", key="run_number", help="Change this to prevent overwriting files")
    col4.text_input("Label", key="time_label", help="label that will show on the graph")

    st.divider()

    st.subheader("🔌 Keithley SMU Settings")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.number_input("Current Limit A (A)", format="%.1e", step=1e-4, key="current_limit_a", help="Max current allowed")
        st.number_input("Current Limit B (A)", format="%.1e", step=1e-4, key="current_limit_b")
    if hardware != "Baseline Reset":
        with col2:
            st.number_input("Current Range A (A)", format="%.1e", step=1e-6, key="current_range_a")
            st.number_input("Current Range B (A)", format="%.1e", step=1e-6, key="current_range_b")
    else:
        st.text("Auto Range Mode")
        
    with col3:
        st.number_input("NPLC A", step=0.1, key="nplc_a")
        st.number_input("NPLC B", step=0.1, key="nplc_b")
        
    st.divider()

    # =========================================================
    # DYNAMIC RENDER: Custom Blocks vs Standard Timing
    # =========================================================
    if hardware == "Custom Blocks":
        st.subheader("⚡ Global Voltage Settings")
        col_v1, col_v2, col_v3 = st.columns(3)
        col_v1.number_input("Vd Const (V)", step=0.1, key="vd_const")
        if electric == "Pulsed Vg Train":
            col_v2.number_input("Pulse Width (s)", step=0.001, format="%f", key="pulse_width")
            col_v3.number_input("Rest Time (s)", step=0.01, format="%f", key="rest_time")

        st.subheader("🔦 Default Laser Settings (For newly added blocks)")
        col_opt1, col_opt2, col_opt3 = st.columns(3)
        def_channel = col_opt1.number_input("Default Channel", value=st.session_state["bb_def_channel"], step=1, key="bb_def_channel")
        def_wavelength = col_opt2.number_input("Default Wavelength (nm)", value=st.session_state["bb_def_wavelength"], step=1, key="bb_def_wavelength")
        def_power = col_opt3.number_input("Default Power (nW)", value=st.session_state["bb_def_power"], step=10.0, key="bb_def_power")

        st.subheader("🧱 Build Custom Sequence")
        col_cyc, col_wait = st.columns(2)
        col_cyc.number_input("Sequence Cycle Number", min_value=1, step=1, key="cycle_number")
        col_wait.number_input("Initial Wait Time (s)", min_value=0, step=1, key="wait_time")

        for i, block in enumerate(st.session_state["sequence_blocks"]):
            with st.container():
                col_type, col_dur, col_vg, col_opt, col_order, col_del = st.columns([1.5, 1, 1, 3.5, 0.8, 0.5])
                
                with col_type:
                    st.info(f"**Step {i+1}:** {block['type']}")
                    
                with col_dur:
                    min_dur = 5.0 if block["type"] in ["Laser Power", "Laser Wavelength", "Laser Toggle"] else 0.1
                    block["duration"] = st.number_input("Duration (s)", value=max(float(block["duration"]), min_dur), min_value=min_dur, key=f"dur_{i}")
                    
                with col_vg:
                    block["vg"] = st.number_input("Target Vg (V)", value=float(block.get("vg", 0.0)), step=0.1, key=f"vg_{i}")
                    
                with col_opt:
                    if block["type"] == "Laser Wavelength":
                        sub_1, sub_2 = st.columns(2)
                        block["channel"] = sub_1.number_input("Channel", value=int(block.get("channel", def_channel)), step=1, key=f"ch_wl_{i}")
                        block["wavelength"] = sub_2.number_input("Wavelength (nm)", value=int(block.get("wavelength", def_wavelength)), step=1, key=f"wl_{i}")
                    elif block["type"] == "Laser Power":
                        sub_1, sub_2, sub_3 = st.columns(3)
                        block["channel"] = sub_1.number_input("Ch", value=int(block.get("channel", def_channel)), step=1, key=f"ch_pw_{i}")
                        block["wavelength"] = sub_2.number_input("WL (nm)", value=int(block.get("wavelength", def_wavelength)), step=1, key=f"wl_pw_{i}")
                        block["power"] = sub_3.number_input("Pwr (nW)", value=float(block.get("power", def_power)), step=10.0, key=f"pw_{i}")
                    elif block["type"] == "Laser Toggle":
                        block["channel"] = st.number_input("Channel", value=int(block.get("channel", def_channel)), step=1, key=f"ch_tog_{i}")
                    elif block["type"] == "Servo Shutter":
                        st.caption("Toggles physical shutter state")
                    else:
                        st.caption("Standard Dark Measurement")

                with col_order:
                    sub_u, sub_d = st.columns(2)
                    if sub_u.button("↑", key=f"up_{i}", disabled=(i == 0)):
                        move_block(i, "up")
                        st.rerun()
                    if sub_d.button("↓", key=f"down_{i}", disabled=(i == len(st.session_state["sequence_blocks"]) - 1)):
                        move_block(i, "down")
                        st.rerun()

                with col_del:
                    st.write("") 
                    if st.button("❌", key=f"del_{i}"):
                        st.session_state["sequence_blocks"].pop(i)
                        st.rerun()

        st.write("---")
        col_sel, col_add, col_clr = st.columns([2, 1, 1])
        with col_sel:
            new_block_type = st.selectbox("Select Block to Add:", ["Dark Bias", "Laser Wavelength", "Laser Power", "Laser Toggle", "Servo Shutter"])
        with col_add:
            st.write("") 
            if st.button("➕ Add Block", use_container_width=True):
                default_dur = 5.0 if new_block_type in ["Laser Power", "Laser Wavelength", "Laser Toggle"] else 0.1
                new_block = {"type": new_block_type, "duration": default_dur, "vg": 1.0}
                if new_block_type == "Laser Wavelength": new_block.update({"channel": def_channel, "wavelength": def_wavelength})
                elif new_block_type == "Laser Power": new_block.update({"channel": def_channel, "wavelength": def_wavelength, "power": def_power})
                elif new_block_type == "Laser Toggle": new_block.update({"channel": def_channel, "on": 1})
                st.session_state["sequence_blocks"].append(new_block)
                st.rerun()
        with col_clr:
            st.write("")
            if st.button("🗑️ Clear All", use_container_width=True):
                st.session_state["sequence_blocks"] = []
                st.rerun()

    else:
        # --- Standard Rendering for Array-Based & Simple Modes ---
        st.subheader("⚡ Voltage & Timing Settings")
        col1, col2, col3, col4 = st.columns(4)
        col1.number_input("Vd Const (V)", step=0.1, key="vd_const")

        if hardware == "Baseline Reset":
            col2.number_input("Target Baseline (A)", format="%.1e", step=1e-11, key="target_baseline")
            col3.number_input("Timeout (s)", min_value=60, step=60, key="timeout")
        elif hardware == "Baseline Reset @ Vg":
            col2.number_input("Target Baseline (A)", format="%.1e", step=1e-11, key="target_baseline")
            col3.number_input("Timeout (s)", min_value=60, step=60, key="timeout")
            col4.number_input("Target Vg [Pulse] (V)", step=0.1, key="vg_on")
            
            col_b1, col_b2, col_b3, col_b4 = st.columns(4)
            col_b1.number_input("Base Vg [Resting] (V)", step=0.1, key="base_vg")
            col_b2.number_input("Pulse Width (s)", step=0.001, format="%f", key="pulse_width")
            col_b3.number_input("Rest Time (s)", step=0.01, format="%f", key="rest_time")
        else:
            col2.number_input("Vg ON (Target) (V)", step=0.1, key="vg_on")
            col3.number_input("Vg OFF (Target) (V)", step=0.1, key="vg_off")

            if electric == "Pulsed Vg Train":
                col4.number_input("Base Vg (Resting) (V)", step=0.1, key="base_vg")
            
            col_list = st.columns(4)
            with col_list[0]:
                st.number_input("Wait Time (s)", min_value=0, step=1, key="wait_time")
                st.divider()

            if hardware in ["Laser Only", "Laser + Servo"]:
                st.subheader("🔦 Optics & Arrays (Comma-separated)")
                col1, col2, col3 = st.columns(3)
                col1.text_input("Wavelength Array (nm)", key="wavelength_str")
                col2.text_input("Channel Array", key="channel_str")
                col3.text_input("Power Array (nW)", key="power_str")
                st.divider()

            st.subheader("⏱️ Timing & Sequence Durations")
            
            if electric == "Pulsed Vg Train":
                col1, col2 = st.columns(2)
                col1.number_input("Pulse Width (s)", step=0.001, format="%f", key="pulse_width")
                col2.number_input("Rest Time between pulses (s)", step=0.01, format="%f", key="rest_time")
                st.write("---")

            lbl_dur1 = "Dur 1 (Pulse Train @ Vg OFF)" if electric == "Pulsed Vg Train" else "Dur 1 (Hold @ Vg OFF)"
            lbl_dur2 = "Dur 2 (Pulse Train @ Vg ON)" if electric == "Pulsed Vg Train" else "Dur 2 (Hold @ Vg ON)"

            if hardware == "Dark Current":
                col1, col2, col3 = st.columns(3)
                col1.number_input(lbl_dur1, step=0.5, key="duration_1")
                col2.number_input(lbl_dur2, step=0.5, key="duration_2")
                col3.number_input("Cycle Number", min_value=1, step=1, key="cycle_number")

            elif hardware == "Laser Only":
                col1, col2, col3, col4 = st.columns(4)
                col1.number_input(lbl_dur1, step=0.5, key="duration_1")
                col2.number_input(lbl_dur2, step=0.5, key="duration_2")
                col3.number_input("Dur 3 (Laser ON)", step=0.5, key="duration_3")
                col4.number_input("Dur 4 (Laser OFF)", step=0.5, key="duration_4")
                
                col5, col6 = st.columns(2)
                col5.number_input("Cycle Number", min_value=1, step=1, key="cycle_number")
                col6.number_input("ON/OFF Number", min_value=1, step=1, key="on_off_number")

            elif hardware == "Laser + Servo":
                col1, col2, col3, col4 = st.columns(4)
                col1.number_input(lbl_dur1, step=0.5, key="duration_1")
                col2.number_input(lbl_dur2, step=0.5, key="duration_2")
                
                col5, col6, col7 = st.columns(3)
                col5.number_input("Cycle Number", min_value=1, step=1, key="cycle_number")
                col6.number_input("Servo On/Off #", min_value=1, step=1, key="on_off_number")
                col7.number_input("Servo open/close Time (s)", step=0.5, key="servo_time_on")

    st.divider()

    ### Actions and Queue
    st.subheader("📋 Queue Preview & Management")

    if electric == "Continuous DC Vg":
        queue_dir = Path("config/time_queue")
        target_script = "run_time.py"
    else:
        queue_dir = Path("config/time_pulse_queue")
        target_script = "run_time_pulse.py"
        
    queue_dir.mkdir(exist_ok=True, parents=True)
    queued_files = sorted(list(queue_dir.glob("*.json")))

    if queued_files:
        col_sel, col_clr = st.columns([3, 1])
        selected_file = col_sel.selectbox("Select a queued file to preview:", options=queued_files, format_func=lambda x: x.name, key="preview_select_time")
        if selected_file:
            with st.expander(f"🔍 Previewing: {selected_file.name}", expanded=True):
                with open(selected_file, "r") as f:
                    st.json(json.load(f))

        if col_clr.button("🗑️ Clear Queue", use_container_width=True, key="clear_queue_preview_time"):
            for f in queued_files: f.unlink()
            st.rerun()
    else:
        st.warning("📦 Queue is currently empty.")

    # ACTION BUTTONS
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        st.markdown("**1. Add to Queue**")
        custom_name = st.text_input("Config Name (Optional)", value="", label_visibility="collapsed", key="td_custom_name")
        
        if st.button("➕ Add Configuration", type="primary", use_container_width=True, key="td_save_btn"):
            if hardware == "Custom Blocks" and not st.session_state["sequence_blocks"]:
                st.error("Your sequence is empty! Add some blocks first.")
            else:
                try:
                    # Base config elements
                    config_dict = {
                        "hardware_mode": st.session_state["hardware_mode"],
                        "electrical_mode": st.session_state["electrical_mode"],
                        "description": st.session_state["description"],
                        "device_number": st.session_state["device_number"],
                        "run_number": st.session_state["run_number"],
                        "wait_time": st.session_state["wait_time"],
                        "current_limit_a": st.session_state["current_limit_a"],
                        "current_limit_b": st.session_state["current_limit_b"],
                        "current_range_a": st.session_state["current_range_a"],
                        "current_range_b": st.session_state["current_range_b"],
                        "nplc_a": st.session_state["nplc_a"],
                        "nplc_b": st.session_state["nplc_b"],
                        "vd_const": st.session_state["vd_const"],
                    }

                    # Mode Routing
                    if hardware == "Custom Blocks":
                        config_dict["cycle_number"] = st.session_state["cycle_number"]
                        config_dict["sequence_blocks"] = st.session_state["sequence_blocks"]
                        if electric == "Pulsed Vg Train":
                            config_dict["pulse_width"] = st.session_state["pulse_width"]
                            config_dict["rest_time"] = st.session_state["rest_time"]

                    elif hardware in ["Baseline Reset", "Baseline Reset @ Vg"]:
                        config_dict["target_baseline"] = st.session_state["target_baseline"]
                        config_dict["timeout"] = st.session_state["timeout"]
                        if hardware == "Baseline Reset @ Vg":
                            config_dict["vg_on"] = st.session_state.get("vg_on", 1.0)
                            config_dict["base_vg"] = st.session_state.get("base_vg", 0.0)
                            config_dict["pulse_width"] = st.session_state.get("pulse_width", 0.001)
                            config_dict["rest_time"] = st.session_state.get("rest_time", 0.3)
                    else:
                        config_dict["vg_on"] = st.session_state.get("vg_on", 1.0)
                        config_dict["vg_off"] = st.session_state.get("vg_off", 0.0)
                        config_dict["cycle_number"] = st.session_state.get("cycle_number", 3)
                        config_dict["duration_1"] = st.session_state.get("duration_1", 5.0)
                        config_dict["duration_2"] = st.session_state.get("duration_2", 1.0)

                        if electric == "Pulsed Vg Train":
                            config_dict["base_vg"] = st.session_state.get("base_vg", 0.0)
                            config_dict["pulse_width"] = st.session_state.get("pulse_width", 0.005)
                            config_dict["rest_time"] = st.session_state.get("rest_time", 0.1)

                        if hardware == "Laser Only":
                            config_dict["duration_3"] = st.session_state.get("duration_3", 2.0)
                            config_dict["duration_4"] = st.session_state.get("duration_4", 2.0)
                            config_dict["wavelength_arr"] = [int(x.strip()) for x in st.session_state.get("wavelength_str", "660").split(",")]
                            config_dict["channel_arr"] = [int(x.strip()) for x in st.session_state.get("channel_str", "6").split(",")]
                            config_dict["power_arr"] = [float(x.strip()) for x in st.session_state.get("power_str", "100").split(",")]
                            config_dict["on_off_number"] = st.session_state.get("on_off_number", 1)

                        if hardware == "Laser + Servo":
                            config_dict["wavelength_arr"] = [int(x.strip()) for x in st.session_state.get("wavelength_str", "660").split(",")]
                            config_dict["channel_arr"] = [int(x.strip()) for x in st.session_state.get("channel_str", "6").split(",")]
                            config_dict["power_arr"] = [float(x.strip()) for x in st.session_state.get("power_str", "100").split(",")]
                            config_dict["on_off_number"] = st.session_state.get("on_off_number", 1)
                            config_dict["servo_time_on"] = st.session_state.get("servo_time_on", 1.0)
                            config_dict["servo_time_off"] = st.session_state.get("servo_time_off", 1.0)

                    next_idx = len(queued_files) + 1
                    safe_name = custom_name.replace(" ", "_")
                    mode_prefix = electric.replace(" ", "")
                    hw_prefix = hardware.replace(" ", "").replace("+", "")
                    filename = f"{next_idx:02d}_{hw_prefix}_{mode_prefix}_{safe_name}.json"
                    
                    with open(queue_dir / filename, "w") as f:
                        json.dump(config_dict, f, indent=4)
                    
                    st.success(f"✅ Added to Queue: {filename}")
                    time.sleep(0.5) 
                    st.rerun()

                except ValueError:
                    st.error("Format Error: Ensure arrays are numbers separated by commas (e.g., '660, 532')")
                except Exception as e:
                    st.error(f"Failed to save file: {e}")

    with col_btn2:
        st.markdown("**2. Run Queue**")
        st.info(f"Target Script: `{target_script}`")
        dynamic_run_key = f"td_run_{hardware.replace(' ', '_')}_{electric.replace(' ', '_')}"
        
        if st.button("▶ Run Script in Terminal", type="primary", use_container_width=True, key=dynamic_run_key):
            if not queued_files:
                st.error(f"The {electric} queue is empty! Add a configuration first.")
            else:
                success, msg = launch_in_terminal(target_script)
                if success: st.success(msg)
                else: st.error(msg)

    with col_btn3:
        st.markdown("**3. Hardware Control**")
        st.write("") 
        if st.button("⚙️ Open Servo GUI", type="secondary", use_container_width=True, key="td_servo_btn"):
            success, msg = launch_in_terminal("servo_GUI.py")
            if success: st.success(msg)
            else: st.error(msg)