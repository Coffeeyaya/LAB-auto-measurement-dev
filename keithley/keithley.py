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
# from LabAuto.network import Connection

class Keithley2636B:
    def __init__(self, resource_id, limiti_a=1e-3, limiti_b=1e-3,
             rangei_a=1e-5, rangei_b=1e-5, nplc_a=1, nplc_b=1):
        self.resource_id = resource_id
        self.limiti_a = limiti_a # source limit (current)
        self.limiti_b = limiti_b
        self.rangei_a = rangei_a # source range (current)
        self.rangei_b = rangei_b
        self.nplc_a = nplc_a
        self.nplc_b = nplc_b
        self.rm = None # pyvisa.ResourceManager()
        self.keithley = None # rm.open_resource(self.resource_id)
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
        # k.write("smua.source.output=1") # this is done by enable_output

        k.write("smub.source.func=smub.OUTPUT_DCVOLTS; smub.source.levelv=0")
        k.write(f"smub.source.limiti={self.limiti_b}; smub.measure.rangei={self.rangei_b}")
        k.write(f"smub.measure.nplc={self.nplc_b}; smub.measure.autorangei=0")
        # k.write("smub.source.output=1")

        # "Once" mode: Takes a zero reference reading just once when the command is sent, 
        # and applies that same offset to all future measurements. (A great middle-ground for speed + stability).
        self.keithley.write("smua.measure.autozero = smua.AUTOZERO_ONCE")
        self.keithley.write("smub.measure.autozero = smub.AUTOZERO_ONCE")

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

    def enable_output(self, smu_char, state):
        """
        smu_char: channel a or b
        state: '1' for ON and '0' for OFF
        """
        smu = f"smu{smu_char.lower()}"
        val = "1" if state else "0"
        self.keithley.write(f"{smu}.source.output = {val}")

    def set_autorange(self, smu_char, state):
        """
        smu_char: channel a or b
        state: '1' for ON and '0' for OFF
        """
        smu = f"smu{smu_char.lower()}"
        val = "1" if state else "0"
        self.keithley.write(f"{smu}.measure.autorangei = {val}")

    def set_nplc(self, smu_char, nplc_value):
        """
        smu_char: channel a or b
        """
        smu = f"smu{smu_char.lower()}"
        self.keithley.write(f"{smu}.measure.nplc = {nplc_value}")
        
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
        """
        measure current of channel a(drain) and b(gate)
        use self.lock to ensure that: only one of set_Vd(), set_Vg(), and measure() can run at a time
        """
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
            
    def shutdown(self):
        """
        set
        """
        print("Shutting down...")
        try:
            self.keithley.write("smua.source.levelv = 0")
            self.keithley.write("smub.source.levelv = 0")
            self.enable_output("a", False)
            self.enable_output("b", False)
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

# def run_experiment(light_ip, port=5001, cycles=3):
#     print(f"Connecting to Light Computer at {light_ip}...")
#     conn = Connection.connect(light_ip, port)
    
#     k = Keithley2636B(RESOURCE_ID)
#     k.connect()
#     k.clean_instrument()
#     k.config()
    
#     k.enable_output('a', True)
#     k.enable_output('b', True)
    
#     vg_sequence = [(-1, 2.0), (1, 2.0)]
    
#     try:
#         # 1. Start the asynchronous background Vg pulse
#         k.start_vg_pulse(vg_sequence)
        
#         # 2. Main synchronization loop for the Light PC
#         for i in range(cycles):
#             print(f"\n--- Light Cycle {i+1} ---")
            
#             # 3. Light ON
#             print("Main Thread: Sending LIGHT ON command...")
#             conn.send_json({"channel": 6, "wavelength": "660", "power": "17", "on": 1})
#             conn.receive_json()  # Wait for Light PC to finish clicking
            
#             # The light is now ON. The Vg thread is still pulsing in the background.
#             # Define how long you want the light to stay ON.
#             time.sleep(10) 
            
#             # 4. Light OFF
#             print("Main Thread: Sending LIGHT OFF command...")
#             conn.send_json({"channel": 6, "on": 0})
#             conn.receive_json()  # Wait for Light PC to finish clicking
            
#             # The light is now OFF. 
#             # Define how long you want the light to stay OFF before the next cycle.
#             time.sleep(10)
            
#     finally:
#         # 5. Clean up BOTH the socket and the background thread
#         conn.close()
#         k.stop_vg_pulse()
#         print("Experiment complete. Socket closed and Vg pulse stopped safely.")

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    LIGHT_IP = "192.168.50.17"
    # run_experiment(LIGHT_IP, 5001, 3)
    # k = Keithley2636B(RESOURCE_ID)
    # k.connect()
    # k.clean_instrument()
    # k.config()

    # k.enable_output('a', True)
    # k.enable_output('b', True)
    # k.set_Vd(1.0)
    # k.set_Vg(0.0)

    # time.sleep(5)

    # k.set_Vd(0)
    # k.set_Vg(0)
    # k.enable_output("a", False)
    # k.enable_output("b", False)
    # k.shutdown()
