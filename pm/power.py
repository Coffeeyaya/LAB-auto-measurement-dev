import visa
import time
import csv

# ------------------------
# User settings
# ------------------------
WAVELENGTH = 660       # nm
AVERAGE_COUNT = 10      # smoothing
MEASURE_INTERVAL = 0.2  # seconds
SAVE_TO_CSV = True
CSV_FILENAME = "power_log_relative.csv"

# ------------------------
# Connect to PM100D
# ------------------------
rm = visa.ResourceManager()
res = rm.list_resources('USB?*::0x1313::0x8078::?*::INSTR')

if not res:
    raise Exception("PM100D not found")

meter = rm.open_resource(res[0])
meter.read_termination = '\n'
meter.write_termination = '\n'
meter.timeout = 2000

print("Connected to:", meter.query('*idn?'))

# ------------------------
# Configure meter
# ------------------------
meter.write('sense:power:unit W')
meter.write('sense:power:range:auto 1')
meter.write(f'sense:average:count {AVERAGE_COUNT}')
meter.write('configure:power')
meter.write(f'sense:correction:wavelength {WAVELENGTH}')

# ------------------------
# Optional CSV logging
# ------------------------
if SAVE_TO_CSV:
    csv_file = open(CSV_FILENAME, mode='w', newline='')
    writer = csv.writer(csv_file)
    writer.writerow(["Time (s)", "Power (W)"])

print("Starting measurement... Press Ctrl+C to stop.")

# ------------------------
# Continuous loop
# ------------------------
t0 = time.perf_counter()   # high-resolution timer

try:
    while True:
        power = meter.query_ascii_values('read?')[0]
        t = time.perf_counter() - t0   # relative time in seconds

        print(f"{t:8.3f} s  |  {power:.6e} W")

        if SAVE_TO_CSV:
            writer.writerow([t, power])
            csv_file.flush()

        time.sleep(MEASURE_INTERVAL)

except KeyboardInterrupt:
    print("\nMeasurement stopped.")

finally:
    if SAVE_TO_CSV:
        csv_file.close()
    meter.close()
    rm.close()