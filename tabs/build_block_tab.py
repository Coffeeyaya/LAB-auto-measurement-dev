import streamlit as st
import json
import os
from pathlib import Path

def render_build_block_tab():
    st.header("🧱 Custom Sequence Builder")
    st.markdown("Build your measurement timeline block by block. The entire sequence will repeat based on the Cycle Number.")

    # --- 0. Initialize Session States & Default Blocks ---
    if "sequence_blocks" not in st.session_state or len(st.session_state["sequence_blocks"]) == 0:
        st.session_state["sequence_blocks"] = [
            {"type": "Dark Bias", "duration": 1.0, "vg": 0.0},
            {"type": "Dark Bias", "duration": 1.0, "vg": 1.0} 
        ]

    # --- 1. General & Hardware Settings ---
    st.subheader("📝 General Information")
    col1, col2, col3, col4 = st.columns(4)
    description = col1.text_input("Description", value="Custom Sequence", key="bb_desc")
    device_number = col2.text_input("Device Number", value=st.session_state.get("device_number", "1-1"), key="bb_dev")
    run_number = col3.text_input("Run Number", value=st.session_state.get("run_number", "1"), key="bb_run")
    time_label = col4.text_input("Label", value="Custom", key="bb_label")

    st.divider()

    # --- 2. Advanced SMU Settings ---
    st.subheader("🔌 Keithley SMU Limits & NPLC")
    col_smu1, col_smu2, col_smu3, col_smu4 = st.columns(4)
    with col_smu1:
        i_lim_a = st.number_input("Current Limit A (A)", value=0.001, format="%.1e", step=1e-4, key="bb_ila")
        i_lim_b = st.number_input("Current Limit B (A)", value=0.001, format="%.1e", step=1e-4, key="bb_ilb")
    with col_smu2:
        i_rng_a = st.number_input("Current Range A (A)", value=1e-6, format="%.1e", step=1e-6, key="bb_ira")
        i_rng_b = st.number_input("Current Range B (A)", value=1e-6, format="%.1e", step=1e-6, key="bb_irb")
    with col_smu3:
        nplc_a = st.number_input("NPLC A", value=1.0, step=0.1, key="bb_na")
        nplc_b = st.number_input("NPLC B", value=1.0, step=0.1, key="bb_nb")
    with col_smu4:
        wait_time = st.number_input("Initial Wait Time (s)", value=0, min_value=0, step=1, key="bb_wait")

    st.divider()

    # --- 3. Electrical / Timing Globals ---
    st.subheader("⚡ Global Electrical Settings")
    col_v1, col_v2, col_v3, col_v4, col_v5 = st.columns(5)
    vd_const = col_v1.number_input("Vd Const (V)", value=1.0, step=0.1, key="bb_vd")
    base_vg = col_v2.number_input("Base Vg (Resting) (V)", value=0.0, step=0.1, key="bb_bvg")
    pulse_width = col_v3.number_input("Pulse Width (s)", value=0.001, step=0.001, format="%f", key="bb_pw")
    rest_time = col_v4.number_input("Rest Time (s)", value=0.3, step=0.01, format="%f", key="bb_rt")
    cycle_number = col_v5.number_input("Cycle Number", value=3, min_value=1, step=1, key="bb_cycles")

    st.subheader("🔦 Default Laser Settings")
    col_opt1, col_opt2, col_opt3 = st.columns(3)
    def_channel = col_opt1.number_input("Default Channel", value=6, step=1, key="bb_def_ch")
    def_wavelength = col_opt2.number_input("Default Wavelength (nm)", value=660, step=1, key="bb_def_wl")
    def_power = col_opt3.number_input("Default Power (nW)", value=100.0, step=1.0, key="bb_def_pw")

    st.divider()

    # --- 4. The Block Builder ---
    st.subheader("2. Build Your Sequence")
    
    for i, block in enumerate(st.session_state["sequence_blocks"]):
        with st.container():
            col_type, col_dur, col_vg, col_opt, col_del = st.columns([1.5, 1, 1, 3.5, 0.5])
            
            with col_type:
                st.info(f"**Step {i+1}:** {block['type']}")
                
            with col_dur:
                # Set specific minimum durations based on block type
                if block["type"] in ["Laser Power", "Laser Wavelength"]:
                    min_dur = 5.0
                elif block["type"] == "Laser Toggle":
                    min_dur = 2.0
                elif block["type"] == "Servo Shutter":
                    min_dur = 0.2
                else:
                    min_dur = 0.1 # For Dark Bias
                    
                # Apply the specific minimum to the input box
                block["duration"] = st.number_input(
                    "Duration (s)", 
                    value=max(float(block["duration"]), min_dur), 
                    min_value=min_dur, 
                    key=f"dur_{i}"
                )
                
            with col_vg:
                block["vg"] = st.number_input("Target Vg (V)", value=block["vg"], step=0.1, key=f"vg_{i}")
                
            with col_opt:
                # DECOUPLED LASER SETTINGS
                if block["type"] == "Laser Wavelength":
                    sub_1, sub_2 = st.columns(2)
                    block["channel"] = sub_1.number_input("Channel", value=block.get("channel", def_channel), step=1, key=f"ch_wl_{i}")
                    block["wavelength"] = sub_2.number_input("Wavelength (nm)", value=block.get("wavelength", def_wavelength), step=1, key=f"wl_{i}")
                
                elif block["type"] == "Laser Power":
                    sub_1, sub_2 = st.columns(2)
                    block["channel"] = sub_1.number_input("Channel", value=block.get("channel", def_channel), step=1, key=f"ch_pw_{i}")
                    block["power"] = sub_2.number_input("Power (nW)", value=block.get("power", def_power), step=10.0, key=f"pw_{i}")
                
                elif block["type"] == "Laser Toggle":
                    sub_1, sub_2 = st.columns(2)
                    block["channel"] = sub_1.number_input("Channel", value=block.get("channel", def_channel), step=1, key=f"ch_tog_{i}")
                    # block["toggle_state"] = sub_2.selectbox("State", [1, 0], format_func=lambda x: "ON" if x == 1 else "OFF", key=f"tog_{i}")
                
                elif block["type"] == "Servo Shutter":
                    st.caption("Toggles physical shutter state")
                else:
                    st.caption("Standard Dark Measurement")

            with col_del:
                st.write("") 
                if st.button("❌", key=f"del_{i}"):
                    st.session_state["sequence_blocks"].pop(i)
                    st.rerun()

    # --- 5. Add New Blocks (CLEAN DROPDOWN) ---
    st.write("---")
    col_sel, col_add, col_clr = st.columns([2, 1, 1])
    
    with col_sel:
        new_block_type = st.selectbox(
            "Select Block to Add:", 
            ["Dark Bias", "Laser Wavelength", "Laser Power", "Laser Toggle", "Servo Shutter"]
        )
        
    with col_add:
        st.write("") # Alignment spacing
        if st.button("➕ Add Block", use_container_width=True):
            # Set default duration to match your new minimums
            if new_block_type in ["Laser Power", "Laser Wavelength"]:
                default_dur = 5.0
            elif new_block_type == "Laser Toggle":
                default_dur = 2.0
            else:
                default_dur = 1.0
                
            new_block = {"type": new_block_type, "duration": default_dur, "vg": 1.0}
            
            # Pre-fill required dictionary keys based on the type chosen
            if new_block_type == "Laser Wavelength":
                new_block.update({"channel": def_channel, "wavelength": def_wavelength})
            elif new_block_type == "Laser Power":
                new_block.update({"channel": def_channel, "wavelength": def_wavelength, "power": def_power})
            elif new_block_type == "Laser Toggle":
                new_block.update({"channel": def_channel, "toggle_state": 1})
                
            st.session_state["sequence_blocks"].append(new_block)
            st.rerun()
            
    with col_clr:
        st.write("")
        if st.button("🗑️ Clear All", use_container_width=True):
            st.session_state["sequence_blocks"] = []
            st.rerun()

    st.divider()

    # --- 6. Save Configuration ---
    st.subheader("3. Save to Queue")
    if st.button("🚀 Send to Time-Pulse Queue", type="primary"):
        if not st.session_state["sequence_blocks"]:
            st.error("Your sequence is empty! Add some blocks first.")
        else:
            config = {
                "hardware_mode": "Custom Blocks", 
                "electrical_mode": "Pulsed Vg Train",
                "description": description,
                "device_number": device_number,
                "run_number": run_number,
                "time_label": time_label,
                "wait_time": wait_time,
                "current_limit_a": i_lim_a,
                "current_limit_b": i_lim_b,
                "current_range_a": i_rng_a,
                "current_range_b": i_rng_b,
                "nplc_a": nplc_a,
                "nplc_b": nplc_b,
                "vd_const": vd_const,
                "base_vg": base_vg,
                "pulse_width": pulse_width,
                "rest_time": rest_time,
                "cycle_number": cycle_number,
                "sequence_blocks": st.session_state["sequence_blocks"]
            }
            
            output_dir = Path("config/time_pulse_queue")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            existing_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
            next_idx = len(existing_files) + 1
            filename = f"{next_idx:02d}_CustomBlocks_Dev{device_number}.json"
            
            with open(output_dir / filename, "w") as f:
                json.dump(config, f, indent=4)
                
            st.success(f"✅ Saved custom sequence with {len(st.session_state['sequence_blocks'])} steps to {filename}!")