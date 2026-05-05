import streamlit as st
import json
import os
from pathlib import Path

def move_block(index, direction):
    """Helper function to interchange sequence blocks in the session state."""
    blocks = st.session_state["sequence_blocks"]
    if direction == "up" and index > 0:
        blocks.insert(index - 1, blocks.pop(index))
    elif direction == "down" and index < len(blocks) - 1:
        blocks.insert(index + 1, blocks.pop(index))

def render_build_block_tab():
    st.header("🧱 Custom Sequence Builder")
    st.markdown("Build your measurement timeline block by block. Use the arrows to reorder steps.")

    # --- 0. Initialize Session States ---
    if "sequence_blocks" not in st.session_state or len(st.session_state["sequence_blocks"]) == 0:
        st.session_state["sequence_blocks"] = [
            {"type": "Dark Bias", "duration": 1.0, "vg": 0.0},
            {"type": "Dark Bias", "duration": 1.0, "vg": 1.0} 
        ]

    # --- 1. General & Hardware Settings ---
    st.subheader("📝 General Information")
    col1, col2, col3, col4 = st.columns(4)
    description = col1.text_input("Description", value="Custom Sequence")
    device_number = col2.text_input("Device Number", value=st.session_state.get("device_number", "1-1"))
    run_number = col3.text_input("Run Number", value=st.session_state.get("run_number", "1"))
    time_label = col4.text_input("Label", value="Custom")

    st.divider()

    # --- 2. Advanced SMU & Timing Limits ---
    st.subheader("🔌 SMU & Global Settings")
    col_smu1, col_smu2, col_smu3, col_smu4 = st.columns(4)
    with col_smu1:
        i_lim_a = st.number_input("I-Limit A (A)", value=0.001, format="%.1e")
        vd_const = st.number_input("Vd Const (V)", value=1.0, step=0.1)
    with col_smu2:
        i_rng_a = st.number_input("I-Range A (A)", value=1e-6, format="%.1e")
        base_vg = st.number_input("Base Vg (V)", value=0.0, step=0.1)
    with col_smu3:
        nplc_a = st.number_input("NPLC", value=1.0, step=0.1)
        cycle_number = st.number_input("Cycle Number", value=3, min_value=1)
    with col_smu4:
        wait_time = st.number_input("Initial Wait (s)", value=0, min_value=0)

    st.subheader("🔦 Default Laser Settings")
    col_opt1, col_opt2, col_opt3 = st.columns(3)
    def_channel = col_opt1.number_input("Default Channel", value=6, step=1)
    def_wavelength = col_opt2.number_input("Default Wavelength (nm)", value=660, step=1)
    def_power = col_opt3.number_input("Default Power (nW)", value=100.0, step=1.0)

    st.divider()

    # --- 3. The Block Builder (With Reordering) ---
    st.subheader("2. Build Your Sequence")
    
    for i, block in enumerate(st.session_state["sequence_blocks"]):
        with st.container():
            # Added a column specifically for ordering arrows
            col_type, col_dur, col_vg, col_opt, col_order, col_del = st.columns([1.5, 1, 1, 3.5, 0.8, 0.5])
            
            with col_type:
                st.info(f"**Step {i+1}:** {block['type']}")
                
            with col_dur:
                min_dur = 5.0 if block["type"] in ["Laser Power", "Laser Wavelength"] else (2.0 if block["type"] == "Laser Toggle" else 0.1)
                block["duration"] = st.number_input("Duration (s)", value=max(float(block["duration"]), min_dur), min_value=min_dur, key=f"dur_{i}")
                
            with col_vg:
                block["vg"] = st.number_input("Target Vg (V)", value=block["vg"], step=0.1, key=f"vg_{i}")
                
            with col_opt:
                # DECOUPLED LASER SETTINGS
                if block["type"] == "Laser Wavelength":
                    sub_1, sub_2 = st.columns(2)
                    block["channel"] = sub_1.number_input("Channel", value=block.get("channel", def_channel), step=1, key=f"ch_wl_{i}")
                    block["wavelength"] = sub_2.number_input("Wavelength (nm)", value=block.get("wavelength", def_wavelength), step=1, key=f"wl_{i}")
                
                elif block["type"] == "Laser Power":
                    # CRITICAL FIX: The parser needs wavelength to calculate get_pp_exact()
                    sub_1, sub_2, sub_3 = st.columns(3)
                    block["channel"] = sub_1.number_input("Ch", value=block.get("channel", def_channel), step=1, key=f"ch_pw_{i}")
                    block["wavelength"] = sub_2.number_input("WL (nm)", value=block.get("wavelength", def_wavelength), step=1, key=f"wl_pw_{i}")
                    block["power"] = sub_3.number_input("Pwr (nW)", value=block.get("power", def_power), step=10.0, key=f"pw_{i}")
                
                elif block["type"] == "Laser Toggle":
                    block["channel"] = st.number_input("Channel", value=block.get("channel", def_channel), step=1, key=f"ch_tog_{i}")
                
                elif block["type"] == "Servo Shutter":
                    st.caption("Toggles physical shutter state")
                else:
                    st.caption("Standard Dark Measurement")

            with col_order:
                # Up and Down Arrows for Interchangeability
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

    # --- 4. Add New Blocks ---
    st.write("---")
    col_sel, col_add, col_clr = st.columns([2, 1, 1])
    
    with col_sel:
        new_block_type = st.selectbox(
            "Select Block to Add:", 
            ["Dark Bias", "Laser Wavelength", "Laser Power", "Laser Toggle", "Servo Shutter"]
        )
        
    with col_add:
        st.write("") 
        if st.button("➕ Add Block", use_container_width=True):
            default_dur = 5.0 if new_block_type in ["Laser Power", "Laser Wavelength"] else (2.0 if new_block_type == "Laser Toggle" else 1.0)
            new_block = {"type": new_block_type, "duration": default_dur, "vg": 1.0}
            
            # Pre-fill required keys safely
            if new_block_type == "Laser Wavelength":
                new_block.update({"channel": def_channel, "wavelength": def_wavelength})
            elif new_block_type == "Laser Power":
                new_block.update({"channel": def_channel, "wavelength": def_wavelength, "power": def_power})
            elif new_block_type == "Laser Toggle":
                new_block.update({"channel": def_channel, "on": 1})
                
            st.session_state["sequence_blocks"].append(new_block)
            st.rerun()
            
    with col_clr:
        st.write("")
        if st.button("🗑️ Clear All", use_container_width=True):
            st.session_state["sequence_blocks"] = []
            st.rerun()

    st.divider()

    # --- 5. Save Configuration ---
    st.subheader("3. Save to Queue")
    if st.button("🚀 Send to Time-Pulse Queue", type="primary"):
        if not st.session_state["sequence_blocks"]:
            st.error("Your sequence is empty! Add some blocks first.")
        else:
            config = {
                "hardware_mode": "Custom Blocks", 
                "description": description,
                "device_number": device_number,
                "run_number": run_number,
                "time_label": time_label,
                "wait_time": wait_time,
                "current_limit_a": i_lim_a,
                "current_range_a": i_rng_a,
                "nplc_a": nplc_a,
                "vd_const": vd_const,
                "base_vg": base_vg,
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