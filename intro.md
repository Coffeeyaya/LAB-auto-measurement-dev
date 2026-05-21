Project Overview: Automated Photodetector Measurement System
You are an AI programming assistant helping maintain and expand a Python-based automated hardware control system for semiconductor and photodetector characterization.

1. System Architecture
The system uses a decoupled, queue-based architecture to separate the user interface from hardware execution:

Frontend (Streamlit): Users interact with a modular Streamlit UI (organized in tabs). The UI does not control hardware directly. Instead, it generates and formats experiment configurations and saves them as .json files into a queue folder (config/time_pulse_queue). the entry point is app.py.

Backend (Hardware Workers): A separate execution script reads the .json files in alphabetical/numerical order, translates them into SCPI or serial commands, and executes the physical measurements (e.g., base_worker.py).

Network: The setup spans two local private computers. The Electrical PC (Client: 192.168.1.10) runs the main UI and SMUs. The Laser PC (Server: 192.168.1.20) listens for TCP/IP commands to control optical hardware.

2. Core Hardware

Keithley SMUs: Used to apply voltages (Vd, Vg) and measure currents (Id, Ig).

AOTF Laser Controller: Controlled via the Laser PC to set specific wavelengths (nm), channels, and powers (nW).

Servo Motor Shutter: A physical shutter controlled via serial/Arduino to strictly gate the laser beam.

3. Key Workflows & Modules

Time-Dependent / Pulsed Vg Train: The core measurement mode. Applies alternating gate voltages (Vg On / Base Vg) synchronized with laser and servo actuation to measure transient photo-responses.

Baseline Reset: An interleaved hardware mode that runs before formal measurements. It biases the device until the dark current falls below a specific target (e.g., 1e-11 A) to ensure consistent starting conditions.

Batch Generator (batch_tab.py): A UI tool that takes a base JSON template and sweeps a parameter (like laser power or servo time), automatically generating a numbered queue of alternating Baseline Reset and Measurement JSON files.

Optical Encoder (encoder.py): An experimental UI that converts ASCII text or custom 2D canvas drawings (10x10 pixel grids) into flattened 1D binary strings (1s and 0s). These strings dictate light pulses to generate balanced datasets for Machine Learning classification.

4. Coding Guidelines for AI Responses

When modifying Streamlit UI files, ensure state management (st.session_state) is handled safely.

When generating JSON files, strictly maintain the sequential naming convention (e.g., 01_..., 02_...) so the backend queue executes in the correct order.

Never use standard list length len(queue) for file numbering; always parse the actual highest prefix in the directory to prevent overwriting bugs.

Ensure all Keithley data clamping logic safely handles negative polarities during overflow events.