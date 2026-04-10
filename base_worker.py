import time
import json
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from PyQt5.QtCore import QThread, pyqtSignal

from keithley.keithley import Keithley2636B

# ==========================================
# DATACLASS DEFINITIONS
# ==========================================
@dataclass
class SweepData:
    Vd: float
    Vg: float
    Id: float
    Ig: float

@dataclass
class TimeDepData:
    Time: float
    Vd: float
    Vg: float
    Id: float
    Ig: float
    Light_State: int
    Servo_State: int

# ==========================================
# UTILITY FUNCTIONS
# ==========================================
def get_pp_exact(df, wavelength, power_nw):
    if df is None: return None
    try:
        return float(df.loc[int(wavelength), str(power_nw)])
    except KeyError:
        print(f"Warning: Cannot convert {power_nw}nW to PP for {wavelength}nm.")
        return None

# ==========================================
# BASE WORKER CLASS
# ==========================================
class BaseMeasurementWorker(QThread):
    status_update = pyqtSignal(str)
    sequence_finished = pyqtSignal()

    def __init__(self, resource_id, config_files_list, laser=None, servo=None):
        super().__init__()
        self.resource_id = resource_id
        self.config_files = config_files_list
        self.laser = laser 
        self.servo = servo 

        self.k = None
        self.power_table = None
        self.running = True
        self.current_channel = None 
        self.status_label_text = "" 
        
        # clamping range
        self.expected_max_id = None
        self.expected_max_ig = None

    def _init_hardware(self):
        self.status_update.emit("Initializing Keithley...")
        self.k = Keithley2636B(self.resource_id)
        self.k.connect()
        self.k.clean_instrument()
        self.k.config()

    def _get_power_table(self):
        pt_path = Path("calibration") / "pp_df.csv"
        if pt_path.exists():
            self.power_table = pd.read_csv(pt_path, index_col=0)

    def _setup_files(self, params, prefix):
        output_dir = Path("data")
        output_dir.mkdir(parents=True, exist_ok=True) 

        device_num = params.get('device_number', '0')
        run_num = params.get('run_number', '1')
            
        filename = output_dir / f"{prefix}_{device_num}_{run_num}.csv"
        config_backup = output_dir / f"{prefix}_{device_num}_{run_num}_config.json"
        
        if filename.exists() or config_backup.exists():
            raise FileExistsError(f"{filename.name} already exists. Aborting to prevent overwrite!")
        
        with open(config_backup, 'w') as f_back:
            json.dump(params, f_back, indent=4)

        return filename

    def _apply_base_keithley_settings(self, params, autorange=True):
        self.k.set_auto_zero_once()
        self.k.set_nplc('a', params.get("nplc_a", 1.0))
        self.k.set_nplc('b', params.get("nplc_b", 1.0))
        self.k.set_limit('a', params.get("current_limit_a", 1e-3))
        self.k.set_limit('b', params.get("current_limit_b", 1e-3))
        
        if autorange:
            self.k.set_autorange('a', 1)
            self.k.set_autorange('b', 1)
        else:
            self.k.set_autorange('a', 0)
            self.k.set_autorange('b', 0)
            self.expected_max_id = params.get("current_range_a", 1e-6) 
            self.expected_max_ig = params.get("current_range_b", 1e-6)
            self.k.set_range('a', self.expected_max_id)
            self.k.set_range('b', self.expected_max_ig)

    def _precondition_device(self, params):
        wait_time = params.get("wait_time", 0)
        for i in range(wait_time, 0, -1):
            if not self.running: break
            self.status_update.emit(f"Dark Stabilization... {i}s")
            time.sleep(1)

        dep_v = params.get('deplete_voltage')
        dep_t = int(params.get('deplete_time', 0))
        
        if dep_v is not None and self.running:
            self.status_update.emit(f"Depleting Gate at {dep_v}V for {dep_t}s...")
            self.k.set_Vd(0.0) 
            self.k.set_Vg(dep_v)
            for i in range(dep_t, 0, -1):
                if not self.running: break
                time.sleep(1)

    def _setup_laser_steady(self, params):
        if params.get("laser_settings") and self.laser:
            ls = params["laser_settings"]
            pp = get_pp_exact(self.power_table, ls['wavelength'], ls['power'])
            
            self.current_channel = ls['channel']
            self.status_update.emit("Configuring Laser")
            self.laser.send_cmd({"channel": ls['channel'], "wavelength": ls['wavelength'], "power": pp}, wait_for_reply=True)
            self.status_update.emit("Turning Light ON...")
            self.laser.send_cmd({"channel": self.current_channel, "on": 1}, wait_for_reply=True)
            
            for i in range(int(params.get('laser_stable_time', 0)), 0, -1):
                if not self.running: break
                self.status_update.emit(f"Light is ON! Stabilizing... {i}s")
                time.sleep(1)
    
    def clamp_data(self, I_D, I_G):
        """Prevents +9.9e37 overflow, this will happen when measured Id > current range"""
        if self.expected_max_id is None:
            return I_D, I_G
        I_D_record = max(-self.expected_max_id, min(self.expected_max_id, I_D))
        I_G_record = max(-self.expected_max_ig, min(self.expected_max_ig, I_G))
        return I_D_record, I_G_record

    def _shutdown_hardware(self):
        self.status_update.emit("Shutting down hardware safely...")
        if self.servo and getattr(self.servo, 'is_on', False):
            self.servo.toggle_light() 
        if self.laser:
            if self.current_channel is not None:
                self.laser.send_cmd({"channel": self.current_channel, "on": 1}, wait_for_reply=False)
            self.laser.close() 
        if self.k:
            self.k.shutdown()

    def _cleanup_queue(self):
        if "FILE EXISTS ERROR" not in self.status_label_text: 
            self.status_update.emit("Clearing Queue Files...")
            for config_file in self.config_files:
                try:
                    config_file.unlink() 
                except Exception as e:
                    print(f"Could not delete {config_file}: {e}")

    def stop(self):
        self.running = False
        self.wait()

    def run(self):
        raise NotImplementedError("Child must define run()!")