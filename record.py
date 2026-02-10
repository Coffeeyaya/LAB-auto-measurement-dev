import pyvisa
import time
import csv

# ---------- CONFIG ----------
FILENAME = "keithley_fast.csv"
DRAIN_VOLTAGE = 1.0
GATE_HIGH = 1.0
GATE_LOW = -1.0
PULSE_WIDTH = 1.0
TOTAL_CYCLES = 5
DT = 0.01  # Target sample interval in seconds (~10ms)

# ---------- CONNECT ----------
rm = pyvisa.ResourceManager()
keithley = rm.open_resource("GPIB0::26::INSTR")
keithley.write_termination = '\n'
keithley.read_termination = '\n'
keithley.timeout = 10000

# ---------- RESET & CONFIGURE ----------
keithley.write("smua.reset()")
keithley.write("smub.reset()")

keithley.write(f"smua.source.func = smua.OUTPUT_DCVOLTS")
keithley.write(f"smua.source.levelv = {DRAIN_VOLTAGE}")
keithley.write("smua.source.output = smua.OUTPUT_ON")

keithley.write(f"smub.source.func = smub.OUTPUT_DCVOLTS")
keithley.write(f"smub.source.levelv = {GATE_LOW}")
keithley.write("smub.source.output = smub.OUTPUT_ON")

# ---------- OPEN CSV ----------
with open(FILENAME, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Time_s", "V_Gate", "I_Drain", "I_Gate"])

    start_exp = time.time()

    # ---------- PULSED MEASUREMENT LOOP ----------
    for cycle in range(TOTAL_CYCLES):
        for v_gate in [GATE_HIGH, GATE_LOW]:
            keithley.write(f"smub.source.levelv = {v_gate}")
            step_start = time.time()
            npts = int(PULSE_WIDTH / DT)
            
            for _ in range(npts):
                # Timestamp
                t_now = time.time() - start_exp
                
                # Measure both currents in a single query
                raw = keithley.query("print(smua.measure.i(), smub.measure.i())")
                try:
                    idrain, igate = raw.strip().split()
                except ValueError:
                    idrain, igate = "NaN", "NaN"
                
                # Write CSV without flushing each line (faster)
                writer.writerow([t_now, v_gate, idrain, igate])
                
                # Delay to target DT
                elapsed = time.time() - step_start
                sleep_time = DT - elapsed % DT
                if sleep_time > 0:
                    time.sleep(sleep_time)

# ---------- TURN OFF OUTPUTS ----------
keithley.write("smua.source.output = smua.OUTPUT_OFF")
keithley.write("smub.source.output = smub.OUTPUT_OFF")
keithley.close()

print(f"Fast GPIB measurement complete. Data saved to {FILENAME}")
