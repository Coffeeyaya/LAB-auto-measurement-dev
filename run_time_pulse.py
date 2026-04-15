import sys
import time
import csv
import json
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import pyqtSignal
from LabAuto.laser_remote import LaserController
from servo import ServoController
from base_worker import BaseMeasurementWorker, TimeDepData
from base_gui import TimeDepWindow

# ==========================================
# THE UNIVERSAL WORKER THREAD (PULSED)
# ==========================================
class TimeDepPulseWorker(BaseMeasurementWorker):
    new_config = pyqtSignal(int, str)
    new_data = pyqtSignal(int, object) # Emits TimeDepData Dataclass

    # ------------------------------------------
    # SEQUENCE BUILDER
    # ------------------------------------------
    def _build_sequence_single(self, params):
        """
        builds the timeline based on the requested hardware mode.
        only handles single wavelength, single power
        """
        sequence = []
        hardware_mode = params.get("hardware_mode", "Dark Current")

        # ==========================================
        # THE NEW CUSTOM BLOCK PARSER
        # ==========================================
        if hardware_mode == "Custom Blocks":
            blocks = params.get("sequence_blocks", [])
            cycle_number = int(params.get("cycle_number", 1)) 
            
            for _ in range(cycle_number):
                for b in blocks:
                    step = {"Vg": b["vg"], "duration": b["duration"]}
                    
                    # --- STRING RENAMED HERE ---
                    if b["type"] == "Laser Settings":
                        pp = self.get_pp_exact(b["wavelength"], b["power"])
                        step["laser_cmd1"] = {"channel": b["channel"], "power": pp}
                        step["laser_cmd2"] = {"channel": b["channel"], "on": 1}
                        
                    elif b["type"] == "Servo Shutter":
                        step["laser_cmd3"] = 1
                        
                    sequence.append(step)
                    
            return sequence
        
        vg_off = params.get('vg_off', 0.0)
        vg_on = params.get('vg_on', 1.0)
        cycle_number = int(params.get("cycle_number", 1))

        # --- MODE 1: DARK CURRENT ---
        if hardware_mode == "Dark Current":
            for _ in range(cycle_number):
                sequence.append({"Vg": vg_off, "duration": params.get("duration_1", 1.0)})
                sequence.append({"Vg": vg_on,  "duration": params.get("duration_2", 1.0)})
            sequence.append({"Vg": vg_off, "duration": 1.0})
            return sequence

        # --- OPTICAL MODES SETUP ---
        channels = np.array(params.get("channel_arr", [0])).astype(int).astype(str)
        wavelengths = np.array(params.get("wavelength_arr", [660])).astype(int)
        powers = np.array(params.get("power_arr", [100])).astype(int).astype(str)

        ###
        if len(channels) != 1 or len(wavelengths) != 1 or len(powers) != 1:
            print('* this function can only handle single wavelength, single power')
            return []
        ###

        ch_idx = channels[0]
        # wavelength = wavelengths[0]
        pp = self.get_pp_exact(wavelengths[0], powers[0])

        # Optical setup
        sequence = [
            # {"Vg": vg_off, "duration": 5.0, "laser_cmd1": {"channel": ch_idx, "wavelength": wavelength}},
            {"Vg": vg_off, "duration": 5.0, "laser_cmd1": {"channel": ch_idx, "power": pp}}
        ]

        # --- MODE 2: LASER ONLY ---
        if hardware_mode == "Laser Only":
            for _ in range(cycle_number):
                sequence.append({"Vg": vg_off, "duration": params.get("duration_1", 1.0)})
                sequence.append({"Vg": vg_on,  "duration": params.get("duration_2", 1.0)})
                for _ in range(int(params.get("on_off_number", 1))):
                    sequence.append({"Vg": vg_on, "duration": params.get("duration_3", 1.0), "laser_cmd2": {"channel": ch_idx, "on": 1}})
                    sequence.append({"Vg": vg_on, "duration": params.get("duration_4", 1.0), "laser_cmd2": {"channel": ch_idx, "on": 1}})
            sequence.append({"Vg": vg_off, "duration": 1.0})
        
        # --- MODE 3: LASER + SERVO ---
        elif hardware_mode == "Laser + Servo":
            sequence.append({"Vg": vg_off, "duration": 3.0, "laser_cmd2": {"channel": ch_idx, "on": 1}})
            for _ in range(cycle_number):
                sequence.append({"Vg": vg_off, "duration": params.get("duration_1", 1.0)})
                sequence.append({"Vg": vg_on,  "duration": params.get("duration_2", 1.0)})
                for _ in range(int(params.get("on_off_number", 1))):
                    sequence.append({"Vg": vg_on, "duration": params.get("servo_time_on", 1.0), "laser_cmd3": 1})
                    sequence.append({"Vg": vg_on, "duration": params.get("servo_time_off", 1.0), "laser_cmd3": 1})
            sequence.append({"Vg": vg_off, "duration": 1.0, "laser_cmd2": {"channel": ch_idx, "on": 1}})
        return sequence

    # ------------------------------------------
    # EXECUTION
    # ------------------------------------------
    def _switch_source(self, laser_cmd1=None, laser_cmd2=None, laser_cmd3=None):
        if laser_cmd1 and self.laser: 
            self.status_update.emit("Configuring laser...")
            self.laser.send_cmd(laser_cmd1, wait_for_reply=False) 
        if laser_cmd2 and self.laser: 
            self.status_update.emit("Toggling laser ON/OFF...")
            self.laser_channel = laser_cmd2["channel"]
            self.laser.send_cmd(laser_cmd2, wait_for_reply=False) 
            self.current_light_state = 1 - self.current_light_state
        if laser_cmd3 and self.servo:
            self.status_update.emit("Toggling Physical Shutter...")
            self.servo.toggle_light()
            self.servo_state = 1 - self.servo_state 

    def _execute_time_pulse_measurement(self, filename, params, sequence, config_idx, label):
        vd_const = float(params["vd_const"])
        base_vg = float(params.get("base_vg", 0.0))
        pulse_width = float(params.get("pulse_width", 0.005))
        rest_time = float(params.get("rest_time", 0.1))

        start_time = time.time()
        last_emit_time = start_time

        # Pre-bias to Base Vg
        self.k.set_Vg(base_vg)
        time.sleep(1)

        with open(filename, 'w', newline='') as f_csv:
            writer = csv.writer(f_csv)
            writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G", "Light_State", "Servo_State"])

            for step_idx, step in enumerate(sequence):
                if not self.running: break

                self._switch_source(step.get("laser_cmd1"), step.get("laser_cmd2"), step.get("laser_cmd3"))
                
                target_vg = step["Vg"]
                step_end = time.time() + step["duration"]
                self.status_update.emit(f"[{label}] Step {step_idx+1}/{len(sequence)}: Pulsing to {target_vg}V...")
                
                while time.time() < step_end:
                    if not self.running: break

                    time_left = step_end - time.time()
                    if time_left < pulse_width:
                        time.sleep(max(0, time_left))
                        break

                    # Fire the Fast Pulse
                    reading = self.k.measure_pulsed_vg(target_vg, base_vg, pulse_width)
                    
                    if reading and len(reading) == 2:
                        I_D, I_G = reading 
                        if I_D is not None:
                            # Safely clamp values using parent class
                            I_D_clamped, I_G_clamped = self.clamp_data(I_D, I_G)

                            t = time.time() - start_time
                            writer.writerow([t, vd_const, target_vg, I_D_clamped, I_G_clamped, self.current_light_state, self.servo_state])

                            current_t = time.time()
                            if current_t - last_emit_time > 0.2:
                                # Pack and Emit DataClass Object
                                packet = TimeDepData(
                                    Time=t, Vd=vd_const, Vg=target_vg, 
                                    Id=I_D_clamped, Ig=I_G_clamped, 
                                    Light_State=self.current_light_state, Servo_State=self.servo_state
                                )
                                self.new_data.emit(config_idx, packet)
                                last_emit_time = current_t

                    time.sleep(rest_time)

    def _execute_baseline_reset(self, filename, params, config_idx, label):
        """
        Independent mode: Applies Vg=0, measures DC current until |Id| drops below target.
        """
        vd_const = float(params.get("vd_const", 1.0))
        target_baseline = float(params.get("target_baseline", 1e-11))
        timeout = float(params.get("timeout", 600)) # Default 10 minutes timeout
        
        self.status_update.emit(f"[{label}] Starting Baseline Reset. Target: {target_baseline:.2e} A")
        
        # Apply standard dark conditions
        self.k.set_Vg(0.0)
        self.k.set_Vd(vd_const)

        start_time = time.time()
        
        # FIX 2: Separate timers for data and UI
        last_data_emit = start_time
        last_ui_emit = start_time

        with open(filename, 'w', newline='') as f_csv:
            writer = csv.writer(f_csv)
            writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G", "Light_State", "Servo_State"])

            while self.running:
                # Safeguard: Don't wait forever
                if time.time() - start_time > timeout:
                    self.status_update.emit(f"[{label}] Timeout reached ({timeout}s). Proceeding anyway.")
                    break
                    
                reading = self.k.measure()
                
                if reading and len(reading) == 2:
                    I_D, I_G = reading
                    if I_D is not None:
                        t = time.time() - start_time
                        
                        # Save the data point (added 0s for light/servo state)
                        writer.writerow([t, vd_const, 0.0, I_D, I_G, 0, 0])
                        f_csv.flush() # CRITICAL: Ensure it writes to disk immediately!
                        
                        current_t = time.time()
                        if current_t - last_data_emit > 0.2:
                            
                            # FIX 1: Safely clamp data and add missing Light/Servo states
                            I_D_clamped, I_G_clamped = self.clamp_data(I_D, I_G)
                            packet = TimeDepData(
                                Time=t, Vd=vd_const, Vg=0.0, 
                                Id=I_D_clamped, Ig=I_G_clamped,
                                Light_State=0, Servo_State=0 
                            )
                            self.new_data.emit(config_idx, packet)
                            last_data_emit = current_t
                        
                        current_id_abs = abs(I_D)
                        
                        # Update the UI every 2 seconds
                        if current_t - last_ui_emit > 2.0:
                            self.status_update.emit(f"[{label}] Wait: |Id| = {current_id_abs:.2e} A (Target: < {target_baseline:.2e} A)")
                            last_ui_emit = current_t
                        
                        if current_id_abs <= target_baseline:
                            self.status_update.emit(f"[{label}] Baseline reached! ({current_id_abs:.2e} A)")
                            break
                
                time.sleep(0.1)

    # ------------------------------------------
    # ORCHESTRATOR
    # ------------------------------------------
    def run(self):
        # Initialize tracking states
        self.current_light_state = 0 
        self.servo_state = 0 
        self.laser_channel = None

        try:
            self._init_hardware()
            self._get_power_table()

            for config_idx, config_file in enumerate(self.config_files):
                if not self.running: 
                    break

                self.status_update.emit(f"Loading config: {config_file.name}...")
                with open(config_file, "r") as f:
                    params = json.load(f)
                
                

                label = params.get("label", f"Run {params.get('run_number', 1)}")
                self.new_config.emit(config_idx, label)
                
                ### -- BASELINE RESET MODE -- ###
                if hw_mode == "Baseline Reset":
                    try:
                        # FIX 3: Name the file "baseline_" instead of "time_pulse_"
                        filename = self._setup_files(params, prefix="baseline")
                    except FileExistsError as e:
                        self.status_update.emit(f"FILE EXISTS ERROR: {e}")
                        break 
                        
                    self.k.enable_output('a', True)
                    self.k.enable_output('b', True)
                    
                    self._apply_base_keithley_settings(params, autorange=True)
                    
                    self._execute_baseline_reset(filename, params, config_idx, label)
                    
                    self.k.enable_output('a', False)
                    self.k.enable_output('b', False)
                    continue # Skips the rest of the loop for this config
                ### ------------------------- ###

                try:
                    filename = self._setup_files(params, prefix="time_pulse")
                except FileExistsError as e:
                    self.status_label_text = f"FILE EXISTS ERROR: {e}"
                    self.status_update.emit(self.status_label_text)
                    break 

                # Pre-run dark stabilization
                for i in range(params.get("wait_time", 0), 0, -1):
                    if not self.running: break
                    self.status_update.emit(f"Initial wait... {i}s")
                    time.sleep(1)
                # Apply Settings (AUTORANGE MUST BE OFF FOR PULSES)
                self._apply_base_keithley_settings(params, autorange=False)

                
                self.k.set_Vd(float(params["vd_const"]))
                self.k.enable_output('a', True)
                self.k.enable_output('b', True)

                # Build and Execute Sequence
                sequence = self._build_sequence_single(params)
                self._execute_time_pulse_measurement(filename, params, sequence, config_idx, label)

                self.k.enable_output('a', False)
                self.k.enable_output('b', False)

        except Exception as e:
            self.status_update.emit(f"Hardware Error: {e}")
            
        finally:
            self._shutdown_hardware()
            self._cleanup_queue()
            self.sequence_finished.emit()

# ==========================================
# ENTRY POINT
# ==========================================
if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    LASER_IP = "10.0.0.2"

    # 1. READ QUEUE
    queue_dir = Path("config/time_pulse_queue")
    if not queue_dir.exists():
        print(f"Queue directory {queue_dir} not found!")
        sys.exit()

    config_queue = sorted(list(queue_dir.glob("*.json")))
    if not config_queue:
        print("Queue is empty. Exiting.")
        sys.exit()

    # 2. PRE-SCAN CONFIGS FOR HARDWARE NEEDS
    needs_laser = False
    needs_servo = False
    
    for config_path in config_queue:
        try:
            with open(config_path, "r") as f:
                params = json.load(f)
                hw_mode = params.get("hardware_mode", "Dark Current")
                
                if hw_mode in ["Laser Only", "Laser + Servo"]:
                    needs_laser = True
                if hw_mode == "Laser + Servo":
                    needs_servo = True
        except Exception as e:
            pass

    # 3. CONNECT TO HARDWARE
    laser = None
    servo = None
    
    if needs_laser:
        print("Laser required by config. Connecting to Laser PC...")
        try:
            laser = LaserController(LASER_IP)
        except Exception as e:
            print(f"Laser Connection failed ({e}). Running without laser.")

    if needs_servo:
        print("Servo required by config. Connecting to Shutter...")
        try:
            servo = ServoController() 
        except Exception as e:
            print(f"Servo Connection failed ({e}). Running without physical shutter.")

    # 4. LAUNCH APP
    app = QApplication(sys.argv)
    worker = TimeDepPulseWorker(RESOURCE_ID, config_queue, laser=laser, servo=servo)
    window = TimeDepWindow(worker)
    window.show()
    sys.exit(app.exec_())