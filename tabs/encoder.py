import streamlit as st
import json
import time
from pathlib import Path
import pandas as pd
from tabs.helper import launch_in_terminal
import streamlit.components.v1 as components
import numpy as np

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
    enc_mode = st.radio("Encoding Mode", ["ASCII Text", "Raw Binary", "2D Canvas (10x10)"], horizontal=True, key="enc_mode")
    col_e1, col_e2 = st.columns([3, 1])
    
    final_bin = ""
    if enc_mode == "ASCII Text":
        raw_msg = col_e1.text_input("Message to Transmit", key="enc_raw_message")
        final_bin = "".join([format(ord(c), '08b') for c in raw_msg])
        st.caption(f"📠 **Live Translation ({len(final_bin)} bits):** `{final_bin}`")
    elif enc_mode == "Raw Binary":
        raw_bin = col_e1.text_input("Binary String (1s and 0s)", key="enc_binary_string")
        final_bin = "".join([c for c in str(raw_bin) if c in ['0', '1']])
        if str(raw_bin) != final_bin: 
            st.caption(f"⚠️ *Filtered invalid characters. Transmitting:* `{final_bin}`")
    # --- MODE 3: NATIVE PIXEL ART EDITOR (10x10 GRID) ---
    elif enc_mode == "2D Canvas (10x10)":
        with col_e1:
            st.markdown("**Draw your shape!** (Click and drag to paint pixels)")
            
            # 1. The Custom HTML/JS Engine
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

                  // Handles clicking and dragging
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
                  
                  if (ones === 50) {
                     stats.innerHTML = `<span style="color: #00ff00;">⚖️ Perfect ML Balance! (50 White / 50 Black)</span>`;
                  } else {
                     stats.innerHTML = `Balance: ${ones} White / ${zeros} Black`;
                  }
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
            
            # 2. Render the HTML widget
            components.html(pixel_editor_html, height=420)
            
            # 3. The Streamlit Bridge
            final_bin = st.text_input("📠 **Paste your copied string here:**", key="canvas_paste")
            st.text(f'#1s = {final_bin.count("1")}, #0s = {final_bin.count("0")}')
            

    col_e2.number_input("Bit Duration (s)", step=0.1, key="enc_bit_duration", help="How long each bit holds the Vg state before moving to the next bit")
    total_time = (len(final_bin) + 5) * st.session_state["enc_bit_duration"] + 16 
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
    st.subheader("🚀 Queue Management & Actions")
    
    queue_dir = Path("config/time_pulse_queue")
    queue_dir.mkdir(exist_ok=True, parents=True)
    queued_files = sorted(list(queue_dir.glob("*.json")))

    # --- NEW: Queue Preview & Clear Logic ---
    if queued_files:
        col_sel, col_clr = st.columns([3, 1])
        
        # 1. Select a file from the queue to preview
        selected_file = col_sel.selectbox(
            "Select a queued file to preview:", 
            options=queued_files, 
            format_func=lambda x: x.name,
            key="enc_preview_select"
        )
        
        # 2. Display the content
        if selected_file:
            with st.expander(f"🔍 Previewing: {selected_file.name}", expanded=False):
                with open(selected_file, "r") as f:
                    preview_data = json.load(f)
                st.json(preview_data)

        # 3. The Clear Button
        st.write("") # Quick alignment fix
        if col_clr.button("🗑️ Clear Queue", use_container_width=True, key="enc_clear_queue"):
            for f in queued_files: 
                f.unlink() # Physically deletes the JSON file
            st.rerun()
    else:
        st.warning("📦 Queue is currently empty.")

    st.write("---") # Visual separator
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
                
                # FIX: Safely find the highest existing index prefix in the folder
                highest_idx = 0
                for f in queued_files:
                    try:
                        # Extracts the "05" from "05_Encoder_1-1.json"
                        prefix = int(f.name.split('_')[0])
                        highest_idx = max(highest_idx, prefix)
                    except ValueError:
                        pass
                        
                next_idx = highest_idx + 1
                
                # Added a short timestamp to guarantee it never overwrites
                timestamp = int(time.time()) % 10000 
                filename = f"{next_idx:02d}_Encoder_{st.session_state['enc_device_number']}_{timestamp}.json"
                
                with open(queue_dir / filename, "w") as f:
                    json.dump(config_dict_enc, f, indent=4)
                    
                st.success(f"✅ Saved to: {filename}")
                time.sleep(0.5)
                st.rerun()

    with col_btn2:
        if st.button("▶ Run Script in Terminal (run_time_pulse)", type="secondary", use_container_width=True, key="enc_run_btn"):
            if not queued_files:
                st.error("The queue is empty! Add a configuration first.")
            else:
                success, msg = launch_in_terminal("run_time_pulse.py")
                if success: st.success(msg)
                else: st.error(msg)