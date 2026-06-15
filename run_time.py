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
from kCube import WaveplateController
from base_worker import BaseMeasurementWorker, TimeDepData
from base_gui import TimeDepWindow

# ==========================================
# THE UNIVERSAL WORKER THREAD (CONTINUOUS)
# ==========================================
class TimeDepWorker(BaseMeasurementWorker):
    new_config = pyqtSignal(int, str)
    new_data = pyqtSignal(int, object) # Emits TimeDepData Dataclass

    def __init__(self, resource_id, config_files, laser=None, servo=None, qwp=None):
        super().__init__(resource_id, config_files)
        self.laser = laser
        self.servo = servo
        self.qwp = qwp

    # ------------------------------------------
    # SEQUENCE BUILDER
    # ------------------------------------------
    def _build_sequence_single(self, params):
        """
        builds the timeline based on the requested hardware mode.
        """
        hardware_mode = params.get("hardware_mode", "Dark Current")
        
        if hardware_mode == "Custom Blocks":
            return self._build_custom_blocks(params)

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

        ch_idx = int(channels[0])
        wavelength = int(wavelengths[0])
        pp = self.get_pp_exact(wavelengths[0], powers[0])

        # Optical setup
        sequence = [
            {"Vg": vg_off, "duration": 5.0, "laser_cmd1": {"channel": ch_idx, "wavelength": wavelength}},
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

    def _build_custom_blocks(self, params):
        """Builds a timeline based on the GUI's custom block array and repeat rules."""
        blocks = params.get("sequence_blocks", [])
        rules = params.get("repeat_rules", [])

        # 1. Format blocks into standard measurement steps
        formatted_steps = []
        for b in blocks:
            step = {"Vg": b.get("vg", 0.0), "duration": b.get("duration", 1.0)}
            b_type = b.get("type", "Dark Bias")
            
            if b_type == "Laser Wavelength":
                step["laser_cmd1"] = {"channel": b["channel"], "wavelength": b["wavelength"]}
            elif b_type == "Laser Power":
                wl = b.get("wavelength", 660)
                pp = self.get_pp_exact(wl, b["power"])
                step["laser_cmd1"] = {"channel": b["channel"], "power": pp}
            elif b_type == "Laser Toggle":
                step["laser_cmd2"] = {"channel": b["channel"], "on": 1}
            elif b_type == "Servo Shutter":
                step["laser_cmd3"] = 1
            elif b_type == "QWP Rotation":
                step["qwp_cmd"] = b.get("qwp_angle", 45.0)
            formatted_steps.append(step)

        # 2. Clean and sort rules (1-based UI to 0-based code)
        clean_rules = []
        for r in rules:
            s = max(0, int(r["start"]) - 1)
            e = min(len(blocks) - 1, int(r["end"]) - 1)
            c = max(1, int(r["cycles"]))
            if s <= e:
                clean_rules.append({"start": s, "end": e, "cycles": c})
        
        # Sort rules: Longest ranges first to build the tree from top-down
        clean_rules.sort(key=lambda x: (x["end"] - x["start"], -x["start"]), reverse=True)

        # 3. Recursive Expansion Function
        def expand_range(start_idx, end_idx, active_rules):
            result = []
            i = start_idx
            while i <= end_idx:
                # Find the rule that starts exactly at index i
                applicable_rule = next((r for r in active_rules if r["start"] == i and r["end"] <= end_idx), None)

                if applicable_rule:
                    # Find all rules strictly inside this one
                    sub_rules = [r for r in active_rules if r != applicable_rule and 
                                 r["start"] >= applicable_rule["start"] and r["end"] <= applicable_rule["end"]]
                    
                    # Recursively expand the inner content once
                    sub_sequence = expand_range(applicable_rule["start"], applicable_rule["end"], sub_rules)
                    
                    # Repeat it the requested number of times
                    for _ in range(applicable_rule["cycles"]):
                        result.extend(sub_sequence)
                    
                    # Jump index past this rule
                    i = applicable_rule["end"] + 1
                else:
                    # No rule starts here, just add the individual step
                    result.append(formatted_steps[i])
                    i += 1
            return result

        # Initial call: expand everything from 0 to len-1
        if not formatted_steps:
            return []
            
        return expand_range(0, len(formatted_steps) - 1, clean_rules)

    # ------------------------------------------
    # EXECUTION
    # ------------------------------------------
    def _switch_source(self, target_vg, laser_cmd1=None, laser_cmd2=None, laser_cmd3=None, qwp_cmd=None):
        """
        this function can be used only for continuous Vg, not pulsed
        """
        ###
        if getattr(self, 'current_applied_vg', None) != target_vg:
            self.k.set_Vg(target_vg)
            self.current_applied_vg = target_vg
        ###
            
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
        if qwp_cmd is not None and self.qwp:
            self.status_update.emit(f"Rotating QWP to {qwp_cmd} degrees...")
            self.qwp.move_to_degree(qwp_cmd, wait=False)

    def _execute_time_measurement(self, filename, params, sequence, config_idx, label):
        vd_const = float(params["vd_const"])
        start_time = time.time()
        last_emit_time = start_time
        
        self.current_applied_vg = None # Reset tracker for DC voltage

        with open(filename, 'w', newline='') as f_csv:
            writer = csv.writer(f_csv)
            writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G", "Light_State", "Servo_State"])

            for step_idx, step in enumerate(sequence):
                if not self.running: break

                target_vg = step["Vg"]
                
                # Update hardware states (Keithley + Optics)
                self._switch_source(target_vg, step.get("laser_cmd1"), step.get("laser_cmd2"), step.get("laser_cmd3"), step.get("qwp_cmd"))
                
                step_end = time.time() + step["duration"]
                self.status_update.emit(f"[{label}] Step {step_idx+1}/{len(sequence)}: Continuous Read at {target_vg}V...")
                
                # Fast Continuous Sampling
                while time.time() < step_end:
                    if not self.running: break

                    reading = self.k.measure() # Standard DC Measure!
                    
                    if reading and len(reading) == 2:
                        I_D, I_G = reading 
                        if I_D is not None:
                            t = time.time() - start_time
                            writer.writerow([t, vd_const, target_vg, I_D, I_G, self.current_light_state, self.servo_state])

                            current_t = time.time()
                            if current_t - last_emit_time > 0.2:
                                packet = TimeDepData(
                                    Time=t, Vd=vd_const, Vg=target_vg, 
                                    Id=I_D, Ig=I_G, 
                                    Light_State=self.current_light_state, Servo_State=self.servo_state
                                )
                                self.new_data.emit(config_idx, packet)
                                last_emit_time = current_t

    def _execute_baseline_reset(self, params, label):
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
        
        while self.running:
            # Safeguard: Don't wait forever
            if time.time() - start_time > timeout:
                self.status_update.emit(f"[{label}] Timeout reached ({timeout}s). Proceeding anyway.")
                break
                
            reading = self.k.measure()
            if reading and len(reading) == 2:
                I_D, I_G = reading
                if I_D is not None:
                    current_id_abs = abs(I_D)
                    # self.status_update.emit(f"[{label}] Wait: |Id| = {current_id_abs:.2e} A (Target: < {target_baseline:.2e} A)")
                    
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
                
                # Pre-run dark stabilization
                for i in range(params.get("wait_time", 0), 0, -1):
                    if not self.running: break
                    self.status_update.emit(f"Initial wait... {i}s")
                    time.sleep(1)

                try:
                    filename = self._setup_files(params, prefix="time_steady")
                except FileExistsError as e:
                    self.status_label_text = f"FILE EXISTS ERROR: {e}"
                    self.status_update.emit(self.status_label_text)
                    break 

                label = params.get("label", f"Run {params.get('run_number', 1)}")
                self.new_config.emit(config_idx, label)

                ### -- baseline reset -- ###
                hw_mode = params.get("hardware_mode", "Dark Current")
                if hw_mode == "Baseline Reset":
                    self.k.enable_output('a', True)
                    self.k.enable_output('b', True)
                    self._apply_base_keithley_settings(params, autorange=True)
                    self._execute_baseline_reset(params, label)
                    self.k.enable_output('a', False)
                    self.k.enable_output('b', False)
                    continue # <--- CRITICAL: Skips the CSV creation and sequence builder below
                ### ------------------- ###
                
                # Apply Settings (AUTORANGE MUST BE OFF FOR time dependent measurements)
                self._apply_base_keithley_settings(params, autorange=False)
                
                self.k.set_Vd(float(params["vd_const"]))
                self.k.enable_output('a', True)
                self.k.enable_output('b', True)
                
                # Build and Execute Sequence
                sequence = self._build_sequence_single(params)
                
                # Append Post-Measurement Reset Sequence
                if "reset_vg" in params:
                    # 1. Apply Reset Pulse
                    sequence.append({"Vg": float(params["reset_vg"]), "duration": float(params.get("reset_duration", 5.0))})
                    # 2. Relax at 0V for 3s
                    sequence.append({"Vg": 0.0, "duration": 3.0})
                
                self._execute_time_measurement(filename, params, sequence, config_idx, label)

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
    queue_dir = Path("config/time_queue")
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
    needs_qwp = False
    
    for config_path in config_queue:
        try:
            with open(config_path, "r") as f:
                params = json.load(f)
                hw_mode = params.get("hardware_mode", "Dark Current")
                
                if hw_mode in ["Laser Only", "Laser + Servo", "Custom Blocks"]:
                    needs_laser = True
                if hw_mode in ["Laser + Servo", "Custom Blocks"]:
                    needs_servo = True
                
                if hw_mode == "Custom Blocks":
                    blocks = params.get("sequence_blocks", [])
                    for b in blocks:
                        if b.get("type") == "QWP Rotation":
                            needs_qwp = True
                            break
        except Exception as e:
            pass

    # 3. CONNECT TO HARDWARE
    laser = None
    servo = None
    qwp = None
    
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

    if needs_qwp:
        print("QWP required by config. Connecting to Thorlabs Motor...")
        try:
            qwp = WaveplateController()
            qwp.home() 
        except Exception as e:
            print(f"QWP Connection failed ({e}). Running without waveplate control.")

    # 4. LAUNCH APP
    app = QApplication(sys.argv)
    worker = TimeDepWorker(RESOURCE_ID, config_queue, laser=laser, servo=servo, qwp=qwp)
    window = TimeDepWindow(worker)
    window.show()
    sys.exit(app.exec_())