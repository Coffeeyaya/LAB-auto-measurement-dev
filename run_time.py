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
# HELPER
# ==========================================
def get_pp_exact(power_table, wavelength, power_nw):
    if power_table is None: return None
    try:
        return float(power_table.loc[int(wavelength), str(power_nw)])
    except KeyError:
        print(f"Warning: Cannot convert {power_nw}nW to PP for {wavelength}nm.")
        return None

# ==========================================
# THE UNIVERSAL WORKER THREAD (PULSED)
# ==========================================
class TimeDepWorker(BaseMeasurementWorker):
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
        pp = get_pp_exact(self.power_table, wavelengths[0], powers[0])

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
    def _switch_source(self, target_vg, laser_cmd1=None, laser_cmd2=None, laser_cmd3=None):
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
                self._switch_source(target_vg, step.get("laser_cmd1"), step.get("laser_cmd2"), step.get("laser_cmd3"))
                
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
                if not self.running: break

                self.status_update.emit(f"Loading config: {config_file.name}...")
                with open(config_file, "r") as f:
                    params = json.load(f)
                
                # Pre-run dark stabilization
                for i in range(params.get("wait_time", 0), 0, -1):
                    if not self.running: break
                    self.status_update.emit(f"Initial wait... {i}s")
                    time.sleep(1)

                try:
                    filename = self._setup_files(params, prefix="time_pulse")
                except FileExistsError as e:
                    self.status_label_text = f"FILE EXISTS ERROR: {e}"
                    self.status_update.emit(self.status_label_text)
                    break 

                # Apply Settings (AUTORANGE MUST BE OFF FOR time dependent measurements)
                self._apply_base_keithley_settings(params, autorange=False)
                
                self.k.set_Vd(float(params["vd_const"]))
                self.k.enable_output('a', True)
                self.k.enable_output('b', True)

                label = params.get("label", f"Run {params.get('run_number', 1)}")
                self.new_config.emit(config_idx, label)
                
                # Build and Execute Sequence
                sequence = self._build_sequence_single(params)
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
    worker = TimeDepWorker(RESOURCE_ID, config_queue, laser=laser, servo=servo)
    window = TimeDepWindow(worker)
    window.show()
    sys.exit(app.exec_())