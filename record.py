import pyvisa
import time
import csv
import os

# --- CONFIGURATION ---
FILENAME = "live_measurements.csv"
DRAIN_VOLTAGE = 1.0
GATE_HIGH = 1.0
GATE_LOW = -1.0
PULSE_WIDTH = 1.0
TOTAL_CYCLES = 5

# --- SETUP INSTRUMENT ---
rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR')

keithley.timeout = 10000
keithley.read_termination = '\n'
keithley.write_termination = '\n'

print("--- STARTING RECORDER ---")
print(f"Data file: {FILENAME}")

try:
    # --- INITIALIZE ---
    keithley.write("abort")
    keithley.write("errorqueue.clear()")
    keithley.write("format.data = format.ASCII")

    keithley.write("""
        smua.reset()
        smub.reset()

        smua.source.func = smua.OUTPUT_DCVOLTS
        smub.source.func = smub.OUTPUT_DCVOLTS

        smua.source.limiti = 0.01
        smub.source.limiti = 0.001

        smua.measure.nplc = 0.01
        smub.measure.nplc = 0.01

        smua.source.levelv = {0}
        smua.source.output = smua.OUTPUT_ON
        smub.source.output = smub.OUTPUT_ON
    """.format(DRAIN_VOLTAGE))

    # --- OPEN CSV FILE ---
    with open(FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time_s", "V_Gate_V", "I_Drain_A", "I_Gate_A"])
        f.flush()
        os.fsync(f.fileno())

        start_exp = time.time()

        for cycle in range(TOTAL_CYCLES):
            for v_gate in (GATE_HIGH, GATE_LOW):

                keithley.write(f"smub.source.levelv = {v_gate}")
                step_start = time.time()

                print(f"Cycle {cycle+1}: Gate -> {v_gate} V")

                while (time.time() - step_start) < PULSE_WIDTH:
                    try:
                        raw = keithley.query(
                            "print(smua.measure.i(), smub.measure.i())"
                        )
                        i_drain, i_gate = map(float, raw.strip().split())

                        t_now = time.time() - start_exp

                        writer.writerow([t_now, v_gate, i_drain, i_gate])
                        f.flush()
                        os.fsync(f.fileno())

                    except (ValueError, pyvisa.errors.VisaIOError):
                        pass

finally:
    print("Recording finished. Turning outputs OFF.")
    keithley.write("smua.source.output = smua.OUTPUT_OFF")
    keithley.write("smub.source.output = smub.OUTPUT_OFF")
    keithley.close()
