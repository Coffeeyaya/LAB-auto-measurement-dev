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

# --- CONFIGURATION ---
RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
FILENAME = "shared_data.csv"
DRAIN_V = 1.0       
GATE_HIGH = 1.0     
GATE_LOW = -1.0     
POINTS_PER_PHASE = 30  
CYCLE_NUMBERS = 5

class Keithley2636B:
    def __init__(self, resource_id, filename="shared_data.csv"):
        self.resource_id = resource_id
        self.filename = filename
        self.rm = None
        self.keithley = None
        self.start_time = None

        self.Vd = 0.0  
        self.Vg = 0.0  

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
    
    def set_Vd(self, v):
        self.Vd = v
        
        try:
            self.keithley.write(f"smua.source.levelv = {v}")
        except:
            pass

    def set_Vg(self, v):
        self.Vg = v
        try:
            self.keithley.write(f"smub.source.levelv = {v}")
        except:
            pass

    def measure(self):
        try:
            self.keithley.write("print(smua.measure.i(), smub.measure.i())")
            resp = self.keithley.read().replace("\t", ",").split(",")
            if len(resp) >= 2:
                return float(resp[0]), float(resp[1])
        except:
            return 0.0, 0.0
        
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

    # initial settings before measurement
    def config(self, limiti_a=1e-3, limiti_b=1e-3, rangei_a=1e-6, rangei_b=1e-6, nplc_a=1, nplc_b=1):
        k = self.keithley
        k.write("smua.source.func=smua.OUTPUT_DCVOLTS; smua.source.levelv=0")
        k.write(f"smua.source.limiti={limiti_a}; smua.measure.rangei={rangei_a}")
        k.write(f"smua.measure.nplc={nplc_a}; smua.measure.autorangei=0")
        k.write("smua.source.output=1")

        k.write("smub.source.func=smub.OUTPUT_DCVOLTS; smub.source.levelv=0")
        k.write(f"smub.source.limiti={limiti_b}; smub.measure.rangei={rangei_b}")
        k.write(f"smub.measure.nplc={nplc_b}; smub.measure.autorangei=0")
        k.write("smub.source.output=1")

    # prepare csv file for saving data
    def prepare_file(self):

        if os.path.exists(self.filename):
            try:
                os.remove(self.filename)
            except:
                pass

        with open(self.filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time", "V_Gate", "I_Drain", "I_Gate"])

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
    # Create an instance
    smu = Keithley2636B(RESOURCE_ID)

    # Connect and initialize
    smu.connect()
    smu.clean_instrument()
    smu.config()

    # Run measurement
    smu.run()  # will use your global constants for gate/drain voltage, points, cycles

    # Shutdown outputs safely
    smu.shutdown()