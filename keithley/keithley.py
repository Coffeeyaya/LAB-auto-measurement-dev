'''
test keithley version 2
with class implementation
run with plot.py
combined to run.bat
'''
import pyvisa
import time
import csv
import os
import threading

class Keithley2636B:
    def __init__(self, resource_id, limiti_a=1e-3, limiti_b=1e-3,
             rangei_a=1e-6, rangei_b=1e-6, nplc_a=1, nplc_b=1):
        self.resource_id = resource_id
        # self.filename = filename
        self.limiti_a = limiti_a
        self.limiti_b = limiti_b
        self.rangei_a = rangei_a
        self.rangei_b = rangei_b
        self.nplc_a = nplc_a
        self.nplc_b = nplc_b
        self.rm = None
        self.keithley = None
        self.start_time = None
        self.Vd = 0.0
        self.Vg = 0.0

        self.lock = threading.Lock()
 
    # connection
    def connect(self):
        try:
            self.rm = pyvisa.ResourceManager()
            self.keithley = self.rm.open_resource(self.resource_id)
            self.keithley.timeout = 20000
            self.keithley.write_termination = '\n'
            self.keithley.read_termination = '\n'
            print("Connected.")
        except Exception as e:
            raise RuntimeError(f"Connection failed: {e}")

    # initial settings before measurement
    def config(self):
        k = self.keithley
        k.write("smua.source.func=smua.OUTPUT_DCVOLTS; smua.source.levelv=0")
        k.write(f"smua.source.limiti={self.limiti_a}; smua.measure.rangei={self.rangei_a}")
        k.write(f"smua.measure.nplc={self.nplc_a}; smua.measure.autorangei=0")
        k.write("smua.source.output=1")

        k.write("smub.source.func=smub.OUTPUT_DCVOLTS; smub.source.levelv=0")
        k.write(f"smub.source.limiti={self.limiti_b}; smub.measure.rangei={self.rangei_b}")
        k.write(f"smub.measure.nplc={self.nplc_b}; smub.measure.autorangei=0")
        k.write("smub.source.output=1")

    # clean error
    def clean_instrument(self):
        print("Cleaning instrument...")
        try:
            try:
                self.keithley.clear()
            except:
                pass

            try:
                self.keithley.write("abort")
            except:
                pass

            try:
                self.keithley.write("*rst")
            except:
                pass

            self.keithley.write("*cls")
            time.sleep(0.5)

            while True:
                try:
                    err_count = int(float(self.keithley.query("print(errorqueue.count)")))
                    if err_count == 0:
                        break
                    self.keithley.query("print(errorqueue.next())")
                except:
                    break

            print("Instrument clean.")

        except Exception as e:
            print(f"Warning during clean: {e}")

    def set_Vd(self, v):
        with self.lock:
            self.Vd = v
            
            try:
                self.keithley.write(f"smua.source.levelv = {v}")
            except:
                pass

    def set_Vg(self, v):
        with self.lock:
            self.Vg = v
            try:
                self.keithley.write(f"smub.source.levelv = {v}")
            except:
                pass

    def measure(self):
        with self.lock:
            try:
                self.keithley.write("print(smua.measure.i(), smub.measure.i())")
                resp = self.keithley.read().replace("\t", ",").split(",")
                if len(resp) >= 2:
                    return float(resp[0]), float(resp[1])
            except:
                return 0.0, 0.0


    def start_vg_pulse(self, pulse_sequence):
        """
        pulse_sequence: list of tuples [(Vg1, duration1), (Vg2, duration2), ...]
        It will loop through sequence until stop_vg_pulse() is called.
        """
        if hasattr(self, '_pulse_thread') and self._pulse_thread.is_alive():
            print("Pulse thread already running")
            return

        self._pulse_running = True

        def pulse_worker():
            while self._pulse_running:
                for Vg, duration in pulse_sequence:
                    if not self._pulse_running:
                        break
                    self.set_Vg(Vg)
                    t_end = time.time() + duration
                    while time.time() < t_end:
                        if not self._pulse_running:
                            break
                        time.sleep(0.01)

        self._pulse_thread = threading.Thread(target=pulse_worker, daemon=True)
        self._pulse_thread.start()
        print("Vg pulse started")

    def stop_vg_pulse(self):
        self._pulse_running = False
        if hasattr(self, '_pulse_thread'):
            self._pulse_thread.join()
            print("Vg pulse stopped")

    # prepare csv file for saving data
    def prepare_file(self):

        if os.path.exists(self.filename):
            try:
                os.remove(self.filename)
            except:
                pass

        with open(self.filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time", "V_Drain", "V_Gate", "I_Drain", "I_Gate"])

    # set vg to a value, measure some points
    def set_vg_phase(self, gate_voltage, points_per_phase):

        k = self.keithley

        with open(self.filename, 'a', newline='') as f:
            writer = csv.writer(f)

            for _ in range(points_per_phase):

                try:
                    k.write("print(smua.measure.i(), smub.measure.i())")
                    resp = k.read().replace('\t', ',').split(',')

                    if len(resp) >= 2:
                        t = time.time() - self.start_time
                        writer.writerow([
                            t,
                            gate_voltage,
                            float(resp[0]),
                            float(resp[1])
                        ])
                except:
                    pass

                f.flush()

    def gate_periodic(self, vg_high, vg_low, points_per_phase, cycle_numbers):
        k = self.keithley
        for i in range(cycle_numbers):
            print(f"Cycle {i+1}/{cycle_numbers}...", end="", flush=True)

            # high Vg
            k.write(f"smub.source.levelv = {vg_high}")
            self.set_vg_phase(vg_high, points_per_phase)

            # low Vg
            k.write(f"smub.source.levelv = {vg_low}")
            self.set_vg_phase(vg_low, points_per_phase)
        
    # run measurement(includes measurement procedure)             
    def run(self):
        self.prepare_file()
        self.start_time = time.time()
        self.keithley.write(f"smua.source.levelv = {DRAIN_V}")
        self.gate_periodic(vg_high=GATE_HIGH, vg_low=GATE_LOW, points_per_phase=POINTS_PER_PHASE, cycle_numbers=CYCLE_NUMBERS)
        self.keithley.write("smua.source.levelv = 0")
        self.keithley.write("smub.source.levelv = 0")
        print("Done.")
    
    def shutdown(self):
        print("Shutting down...")
        try:
            self.keithley.write("smua.source.levelv = 0")
            self.keithley.write("smub.source.levelv = 0")
            self.keithley.write("smua.source.output = 0")
            self.keithley.write("smub.source.output = 0")
            self.keithley.close()
        except:
            pass
        print("Finished.")

    # context manager support(with open ... as ...)
    def __enter__(self):
        self.connect()
        self.clean_instrument()
        self.config()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    k = Keithley2636B(RESOURCE_ID)
    k.connect()
    k.clean_instrument()
    k.config()

    # Set initial voltages
    k.set_Vd(1.0)
    k.set_Vg(0.0)

    # Start Vg pulse: alternate +1/-1 V every 1 second
    pulse_seq = [(1.0, 1.0), (-1.0, 1.0)]
    k.start_vg_pulse(pulse_seq)

    # Let it run for 10 seconds
    time.sleep(10)

    # Stop pulse
    k.stop_vg_pulse()

    # Shutdown safely
    k.set_Vd(0)
    k.set_Vg(0)
    k.shutdown()
