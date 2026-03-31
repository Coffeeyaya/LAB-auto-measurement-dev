'''
lowest level control code that interact with keithley
'''
import pyvisa
import time
import threading

class Keithley2636B:
    def __init__(self, resource_id, limiti_a=1e-3, limiti_b=1e-3,
             rangei_a=1e-4, rangei_b=1e-4, nplc_a=1, nplc_b=1):
        self.resource_id = resource_id
        self.limiti_a = limiti_a # source limit (current)
        self.limiti_b = limiti_b
        self.rangei_a = rangei_a # source range (current)
        self.rangei_b = rangei_b
        self.nplc_a = nplc_a
        self.nplc_b = nplc_b
        self.rm = None # pyvisa.ResourceManager()
        self.keithley = None # rm.open_resource(self.resource_id)
        # self.start_time = None
        # self.Vd = 0.0
        # self.Vg = 0.0

        self.lock = threading.Lock()
 
    # connection
    def connect(self):
        try:
            self.rm = pyvisa.ResourceManager()
            self.keithley = self.rm.open_resource(self.resource_id)
            self.keithley.timeout = 20000
            # Sets a 20-second "wait time." This is crucial for high-precision measurements (high NPLC) 
            # where the Keithley takes a long time to integrate the signal before replying.
            self.keithley.write_termination = '\n'
            # Tells the Keithley that every command from Python ends with a "newline" character so it knows when to start processing.
            self.keithley.read_termination = '\n'
            # Tells Python to stop listening for a response once it hits a "newline" from the instrument.
            print("Connected.")
        except Exception as e:
            raise RuntimeError(f"Connection failed: {e}")

    # initial settings before measurement
    def config(self):
        k = self.keithley
        k.write("smua.source.func=smua.OUTPUT_DCVOLTS; smua.source.levelv=0")
        k.write(f"smua.source.limiti={self.limiti_a}; smua.measure.rangei={self.rangei_a}")
        k.write(f"smua.measure.nplc={self.nplc_a}; smua.measure.autorangei=0")

        k.write("smub.source.func=smub.OUTPUT_DCVOLTS; smub.source.levelv=0")
        k.write(f"smub.source.limiti={self.limiti_b}; smub.measure.rangei={self.rangei_b}")
        k.write(f"smub.measure.nplc={self.nplc_b}; smub.measure.autorangei=0")

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
        
    def set_auto_zero_once(self):
        self.keithley.write("smua.measure.autozero = smua.AUTOZERO_ONCE")
        self.keithley.write("smub.measure.autozero = smub.AUTOZERO_ONCE")

    def set_autorange(self, smu_char, state):
        """
        smu_char: channel a or b
        state: '1' for ON and '0' for OFF
        """
        smu = f"smu{smu_char.lower()}"
        val = "1" if state else "0"
        self.keithley.write(f"{smu}.measure.autorangei = {val}")

    def set_range(self, smu_char, range_value):
        """
        smu_char: channel a or b
        range_value: range for measured current (if actual current > range_value, then it overflows, if actual value << range_value, then the measured value will be much greater then the actual value)
        """
        smu = f"smu{smu_char.lower()}"
        self.keithley.write(f"{smu}.measure.rangei={range_value}")

    def set_limit(self, smu_char, limit_value):
        """
        smu_char: channel a or b
        limit_value: limit for measured current (compliance)
        """
        smu = f"smu{smu_char.lower()}"
        self.keithley.write(f"{smu}.source.limiti={limit_value}") # <-- Fixed!

    def set_nplc(self, smu_char, nplc_value):
        """
        smu_char: channel a or b
        """
        smu = f"smu{smu_char.lower()}"
        self.keithley.write(f"{smu}.measure.nplc = {nplc_value}")
        
    def set_Vd(self, v):
        with self.lock:
            # self.Vd = v
            
            try:
                self.keithley.write(f"smua.source.levelv = {v}")
            except:
                pass

    def set_Vg(self, v):
        with self.lock:
            # self.Vg = v
            try:
                self.keithley.write(f"smub.source.levelv = {v}")
            except:
                pass
            
    def measure_pulsed_vg(self, target_vg, base_vg=0.0, pulse_width=0.005):
        """
        Applies target_vg, waits pulse_width (seconds), measures Id and Ig, 
        and immediately returns Vg to base_vg to prevent charge trapping.
        """
        with self.lock:
            try:
                # We send a 1-line TSP script to execute directly on the Keithley hardware.
                # This guarantees the pulse is exactly 'pulse_width' long (e.g., 5ms), 
                # completely avoiding Python/USB communication lag during the pulse.
                cmd = (
                    f"smub.source.levelv={target_vg} "
                    f"delay({pulse_width}) "
                    "id=smua.measure.i() "
                    "ig=smub.measure.i() "
                    f"smub.source.levelv={base_vg} "
                    "print(id, ig)"
                )
                self.keithley.write(cmd)
                resp = self.keithley.read().replace("\t", ",").split(",")
                
                if len(resp) >= 2:
                    return float(resp[0]), float(resp[1])
            except Exception as e:
                print(f"Pulsed measure error: {e}")
                return 0.0, 0.0

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
            
    def shutdown(self):
        """
        set
        """
        print("Shutting down...")
        try:
            self.keithley.write("smua.source.levelv = 0")
            self.keithley.write("smub.source.levelv = 0")
            self.enable_output("a", False) # open circuit
            self.enable_output("b", False)
            self.keithley.close() # releases the USB resource so other programs (or a new script run) can access it without "Resource Busy" errors
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
    LIGHT_IP = "192.168.50.17"
    k = Keithley2636B(RESOURCE_ID)
    k.connect()
    k.clean_instrument()
    k.config()

    k.enable_output('a', True)
    k.enable_output('b', True)
    k.set_Vd(1.0)
    k.set_Vg(0.0)

    time.sleep(5)

    k.set_Vd(0)
    k.set_Vg(0)
    k.enable_output("a", False)
    k.enable_output("b", False)
    k.shutdown()
