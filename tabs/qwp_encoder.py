import streamlit as st
import json
import time
from pathlib import Path
from tabs.helper import launch_in_terminal
import streamlit.components.v1 as components

def render_qwp_encoder_tab():
    st.title("🎡 QWP Optical Encoder")
    st.markdown("Transmit custom ASCII messages or binary sequences by rotating a Quarter-Wave Plate (QWP) and toggling the laser shutter.")
    st.info("Encoding: `1` = RCP (45°), `0` = LCP (135°). Vg is fixed at 0V.")

    # 1. Initialize defaults
    default_cfg = {
        "qwp_description": "QWP Encoder Test", "qwp_device_number": "1-1", "qwp_run_number": "1", "qwp_label": "qwp_encoder",
        "qwp_wait_time": 5, "qwp_current_limit_a": 1e-3, "qwp_current_limit_b": 1e-3, 
        "qwp_current_range_a": 1e-5, "qwp_current_range_b": 1e-5,
        "qwp_nplc_a": 1.0, "qwp_nplc_b": 1.0, "qwp_vd_const": 1.0, 
        
        "qwp_binary_string": "01001000", "qwp_on_time": 2.0, "qwp_off_time": 1.0, "qwp_rest_time": 10.0,
        "qwp_reset_vg": 0.0, "qwp_reset_duration": 0.0, "qwp_relax_time": 0.0,
        "qwp_raw_message": "Hi",
        "qwp_wavelength": 660, "qwp_channel": 6, "qwp_power": 100.0,
        "qwp_init_laser": True
    }

    for k, v in default_cfg.items():
        if k not in st.session_state:
            st.session_state[k] = v

    st.subheader("📂 Load Existing Configuration")
    if "qwp_uploader_key" not in st.session_state: st.session_state["qwp_uploader_key"] = 0
    uploaded_qwp = st.file_uploader("Upload a previous JSON config", type=["json"], key=f"qwp_uploader_{st.session_state['qwp_uploader_key']}")

    if uploaded_qwp is not None:
        try:
            uploaded_cfg = json.load(uploaded_qwp)
            for k, v in uploaded_cfg.items():
                st.session_state[f"qwp_{k}"] = str(v) if k in ["run_number", "device_number", "description", "label"] else v
            st.session_state["qwp_uploader_key"] += 1
            st.rerun()
        except Exception as e:
            st.error(f"Failed to read JSON file: {e}")

    st.divider()

    # ==========================================
    # ENCODING ENGINE
    # ==========================================
    st.subheader("1. Message Payload")
    qwp_mode = st.radio("Encoding Mode", ["ASCII Text", "Raw Binary", "2D Canvas (10x10)"], horizontal=True, key="qwp_mode")
    col_e1, col_e2 = st.columns([3, 1])
    
    final_bin = ""
    if qwp_mode == "ASCII Text":
        raw_msg = col_e1.text_input("Message to Transmit", key="qwp_raw_message")
        final_bin = "".join([format(ord(c), '08b') for c in raw_msg])
        st.caption(f"📠 **Live Translation ({len(final_bin)} bits):** `{final_bin}`")
    elif qwp_mode == "Raw Binary":
        raw_bin = col_e1.text_input("Binary String (1s and 0s)", key="qwp_binary_string")
        final_bin = "".join([c for c in str(raw_bin) if c in ['0', '1']])
        if str(raw_bin) != final_bin: 
            st.caption(f"⚠️ *Filtered invalid characters. Transmitting:* `{final_bin}`")
    elif qwp_mode == "2D Canvas (10x10)":
        with col_e1:
            st.markdown("**Draw your shape!** (Click and drag to paint pixels)")
            
            pixel_editor_html = """
            <!DOCTYPE html>
            <html>
            <head>
            <style>
              body { background-color: #0e1117; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; margin: 0; padding: 10px; }
              .grid { display: grid; grid-template-columns: repeat(10, 25px); gap: 2px; background: #444; border: 3px solid #555; touch-action: none; }
              .cell { width: 25px; height: 25px; background: black; cursor: crosshair; user-select: none; border-radius: 2px; }
              .cell.active { background: white; box-shadow: 0 0 5px rgba(255,255,255,0.5); }
              .controls { margin-top: 15px; display: flex; gap: 10px; width: 100%; justify-content: center;}
              button { padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
              #copyBtn { background: #ff4b4b; color: white; }
              #copyBtn:hover { background: #ff6b6b; }
              #clearBtn { background: #333; color: white; border: 1px solid #555; }
              #clearBtn:hover { background: #444; }
              .stats { margin-top: 10px; font-size: 14px; color: #aaa; font-weight: bold; }
            </style>
            </head>
            <body>
              <div class="grid" id="grid"></div>
              <div class="stats" id="stats">Balance: 0 White / 100 Black</div>
              <div class="controls">
                <button id="copyBtn">📋 Copy 100-bit String</button>
                <button id="clearBtn">🗑️ Clear</button>
              </div>

              <script>
                const grid = document.getElementById('grid');
                const stats = document.getElementById('stats');
                const copyBtn = document.getElementById('copyBtn');
                let isDrawing = false;
                let drawMode = true; 
                let cells = [];

                for (let i = 0; i < 100; i++) {
                  const cell = document.createElement('div');
                  cell.className = 'cell';
                  cells.push(cell);
                  grid.appendChild(cell);

                  cell.addEventListener('mousedown', (e) => {
                    isDrawing = true;
                    drawMode = !cell.classList.contains('active');
                    cell.classList.toggle('active', drawMode);
                    updateStats();
                  });
                  cell.addEventListener('mouseover', (e) => {
                    if (isDrawing) {
                      cell.classList.toggle('active', drawMode);
                      updateStats();
                    }
                  });
                }

                window.addEventListener('mouseup', () => isDrawing = false);

                document.getElementById('clearBtn').addEventListener('click', () => {
                  cells.forEach(c => c.classList.remove('active'));
                  updateStats();
                });

                function getBinaryString() {
                  return cells.map(c => c.classList.contains('active') ? '1' : '0').join('');
                }

                function updateStats() {
                  const str = getBinaryString();
                  const ones = (str.match(/1/g) || []).length;
                  const zeros = 100 - ones;
                  stats.innerHTML = `Balance: ${ones} White / ${zeros} Black`;
                }

                copyBtn.addEventListener('click', () => {
                  navigator.clipboard.writeText(getBinaryString()).then(() => {
                    const oldText = copyBtn.innerText;
                    copyBtn.innerText = "✅ Copied to Clipboard!";
                    setTimeout(() => copyBtn.innerText = oldText, 2000);
                  });
                });
              </script>
            </body>
            </html>
            """
            components.html(pixel_editor_html, height=420)
            final_bin = st.text_input("📠 **Paste your copied string here:**", key="qwp_canvas_paste")

    st.subheader("⏱️ Bit Timing (Per Bit)")
    bt_col1, bt_col2, bt_col3 = st.columns(3)
    bt_col1.number_input("Rest Time (s)", step=0.1, key="qwp_rest_time", help="Shutter closed, motor rotating. Recommend >= 10s.")
    bt_col2.number_input("ON Time (s)", step=0.1, key="qwp_on_time", help="Shutter open, measuring bit signal.")
    bt_col3.number_input("OFF Time (s)", step=0.1, key="qwp_off_time", help="Shutter closed, measuring post-bit baseline.")

    st.subheader("⚡ Reset Pulse Settings (Per Bit)")
    col_rv1, col_rv2, col_rv3 = st.columns(3)
    col_rv1.number_input("Reset Vg (V)", value=st.session_state.get("qwp_reset_vg", 0.0), step=0.1, key="qwp_reset_vg", help="Applied after each bit")
    col_rv2.number_input("Reset Duration (s)", value=st.session_state.get("qwp_reset_duration", 0.0), step=0.1, key="qwp_reset_duration")
    col_rv3.number_input("Relaxation Time (s)", value=st.session_state.get("qwp_relax_time", 0.0), step=0.1, key="qwp_relax_time", help="Time at Vg=0 after reset")

    total_bit_time = (st.session_state["qwp_rest_time"] + st.session_state["qwp_on_time"] + 
                      st.session_state["qwp_off_time"] + st.session_state["qwp_reset_duration"] + 
                      st.session_state["qwp_relax_time"] * 2) 
    total_time = (len(final_bin) + 5) * total_bit_time + 16 
    st.info(f"⏱️ **Total Bit Cycle:** {total_bit_time:.1f}s | **Estimated Total Time:** ~{total_time:.1f} seconds")

    st.divider()

    # ==========================================
    # UI WIDGETS
    # ==========================================
    st.subheader("2. Measurement Settings")
    col1, col2, col3, col4 = st.columns(4)
    col1.text_input("Description", key="qwp_description")
    col2.text_input("Device Number", key="qwp_device_number")
    col3.text_input("Run Number", key="qwp_run_number")
    col4.number_input("Wait Time (s)", min_value=0, step=1, key="qwp_wait_time")

    col5, col6, col7 = st.columns(3)
    with col5:
        st.number_input("Current Limit A (A)", format="%e", step=1e-4, key="qwp_current_limit_a")
        st.number_input("Current Limit B (A)", format="%e", step=1e-4, key="qwp_current_limit_b")
    with col6:
        st.number_input("Current Range A (A)", format="%e", step=1e-6, key="qwp_current_range_a")
        st.number_input("Current Range B (A)", format="%e", step=1e-6, key="qwp_current_range_b")
    with col7:
        st.number_input("NPLC A", step=0.1, key="qwp_nplc_a")
        st.number_input("NPLC B", step=0.1, key="qwp_nplc_b")

    st.subheader("⚡ Electrical Settings")
    st.number_input("Vd Const (V)", step=0.1, key="qwp_vd_const")
    st.warning("⚠️ **Note:** QWP motor rotation takes ~10s. Ensure 'Rest Time' is sufficient.")

    st.subheader("🔦 Laser Configuration")
    col_o1, col_o2, col_o3, col_o4 = st.columns([1, 1, 1, 1])
    col_o1.number_input("Wavelength (nm)", step=1, key="qwp_wavelength")
    col_o2.number_input("Channel", step=1, key="qwp_channel")
    col_o3.number_input("Power (nW)", step=10.0, key="qwp_power")
    with col_o4:
        st.write("") # padding
        st.checkbox("Init Laser Settings", key="qwp_init_laser", help="If enabled, it will send wavelength/power commands before measurement starts.")

    st.divider()

    # ==========================================
    # ACTIONS & SAVING
    # ==========================================
    st.subheader("🚀 Queue Management & Actions")
    
    queue_dir = Path("config/time_pulse_queue")
    queue_dir.mkdir(exist_ok=True, parents=True)
    queued_files = sorted(list(queue_dir.glob("*.json")))

    if queued_files:
        col_sel, col_clr = st.columns([3, 1])
        selected_file = col_sel.selectbox("Select a queued file to preview:", options=queued_files, format_func=lambda x: x.name, key="qwp_preview_select")
        if selected_file:
            with st.expander(f"🔍 Previewing: {selected_file.name}", expanded=False):
                with open(selected_file, "r") as f:
                    preview_data = json.load(f)
                st.json(preview_data)
        if col_clr.button("🗑️ Clear Queue", use_container_width=True, key="qwp_clear_queue"):
            for f in queued_files: f.unlink()
            st.rerun()
    else:
        st.warning("📦 Queue is currently empty.")

    st.write("---")
    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        if st.button("➕ Add QWP Encoder Config to Queue", type="primary", use_container_width=True, key="qwp_save"):
            if not final_bin:
                st.error("No message or binary string provided!")
            else:
                config_dict_qwp = {
                    "hardware_mode": "QWP Encoder",
                    "electrical_mode": "DC Vg=0",
                    "description": st.session_state["qwp_description"], 
                    "device_number": st.session_state["qwp_device_number"], 
                    "run_number": st.session_state["qwp_run_number"], 
                    "label": st.session_state.get("qwp_label", "qwp_encoder"),
                    "current_limit_a": st.session_state["qwp_current_limit_a"], 
                    "current_limit_b": st.session_state["qwp_current_limit_b"],
                    "current_range_a": st.session_state["qwp_current_range_a"], 
                    "current_range_b": st.session_state["qwp_current_range_b"],
                    "nplc_a": st.session_state["qwp_nplc_a"], 
                    "nplc_b": st.session_state["qwp_nplc_b"],
                    "vd_const": st.session_state["qwp_vd_const"], 
                    "vg_on": 0.0, 
                    "base_vg": 0.0,
                    "pulse_width": 0.0,
                    "on_time": st.session_state["qwp_on_time"],
                    "off_time": st.session_state["qwp_off_time"],
                    "rest_time": st.session_state["qwp_rest_time"],
                    "reset_vg": st.session_state["qwp_reset_vg"],
                    "reset_duration": st.session_state["qwp_reset_duration"],
                    "relax_time": st.session_state["qwp_relax_time"],
                    "wavelength_arr": st.session_state["qwp_wavelength"], 
                    "channel_arr": st.session_state["qwp_channel"], 
                    "power_arr": st.session_state["qwp_power"],
                    "binary_string": final_bin, 
                    "wait_time": st.session_state["qwp_wait_time"],
                    "init_laser": st.session_state["qwp_init_laser"]
                }
                
                highest_idx = 0
                for f in queued_files:
                    try:
                        prefix = int(f.name.split('_')[0])
                        highest_idx = max(highest_idx, prefix)
                    except ValueError: pass
                        
                next_idx = highest_idx + 1
                timestamp = int(time.time()) % 10000 
                filename = f"{next_idx:02d}_QWP_Encoder_{st.session_state['qwp_device_number']}_{timestamp}.json"
                
                with open(queue_dir / filename, "w") as f:
                    json.dump(config_dict_qwp, f, indent=4)
                    
                st.success(f"✅ Saved to: {filename}")
                time.sleep(0.5)
                st.rerun()

    with col_btn2:
        st.markdown("**2. Run Queue**")
        if st.button("▶ Run Script in Terminal (run_time_pulse)", type="primary", use_container_width=True, key="qwp_run_btn"):
            if not queued_files:
                st.error("The queue is empty! Add a configuration first.")
            else:
                success, msg = launch_in_terminal("run_time_pulse.py")
                if success: st.success(msg)
                else: st.error(msg)

        st.write("") # padding
        if st.button("⚙️ Open QWP Manual Control", type="secondary", use_container_width=True, key="qwp_manual_btn"):
            success, msg = launch_in_terminal("qwp_GUI.py")
            if success: st.success(msg)
            else: st.error(msg)

        st.write("") # padding
        if st.button("⚙️ Open Servo GUI", type="secondary", use_container_width=True, key="qwp_servo_btn"):
            success, msg = launch_in_terminal("servo_GUI.py")
            if success: st.success(msg)
            else: st.error(msg)
