import pyvisa
import time

# --- CONFIG ---
RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"

try:
    rm = pyvisa.ResourceManager()
    keithley = rm.open_resource(RESOURCE_ID)
    
    # 1. TIMEOUT CHECK
    # We set a SHORT timeout (2 seconds) so you don't have to wait forever
    keithley.timeout = 2000 
    keithley.write_termination = '\n'
    keithley.read_termination = '\n' # Trying standard Line Feed
    
    print(f"Connected: {keithley.query('*idn?').strip()}")
    
    # 2. SETUP FOR SPEED
    keithley.write("abort")
    keithley.write("*rst")
    keithley.write("errorqueue.clear()")
    keithley.write("smua.source.output = 1")
    
    print("\n--- SPEED TEST (Trying to read 5 points) ---")
    
    for i in range(1, 6):
        start = time.time()
        
        # Ask for data
        try:
            # We use .query() which is safer than write() + read()
            current = keithley.query("print(smua.measure.i())")
            duration = time.time() - start
            
            print(f"Point {i}: {current.strip()} (Took {duration:.4f} sec)")
            
            if duration > 1.0:
                print("   [!] TOO SLOW! This is why you only get 1 point.")
                
        except Exception as e:
            print(f"Point {i}: FAILED ({e})")
            break

except Exception as e:
    print(f"Setup Error: {e}")

finally:
    try: keithley.write("smua.source.output = 0"); keithley.close()
    except: pass