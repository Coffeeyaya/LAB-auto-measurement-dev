from PyQt5.QtCore import QThread, pyqtSignal
import time
import csv
import threading

# -------------------------------
# Measurement Worker using QThread
# -------------------------------
class MeasureWorker(QThread):
    # Emit measurement data: time, Vg, Vd, Id, Ig
    new_data = pyqtSignal(float, float, float, float, float)

    def __init__(self, keithley, interval=0.1, csv_file="data.csv"):
        super().__init__()
        self.k = keithley
        self.interval = interval
        self.csv_file = csv_file
        self._running = False
        self.start_time = None

        # Prepare CSV
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time", "V_Gate", "V_Drain", "I_Drain", "I_Gate"])

    def run(self):
        self._running = True
        self.start_time = time.time()

        while self._running:
            t, Vg, Vd, Id, Ig = self.k.measure_once()  # implement measure_once in Keithley2636B
            if Id is not None:
                # Emit signal
                self.new_data.emit(t, Vg, Vd, Id, Ig)
                # Save to CSV
                with open(self.csv_file, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([t, Vg, Vd, Id, Ig])
            time.sleep(self.interval)

    def stop(self):
        self._running = False
        self.wait()  # wait for thread to finish cleanly

# -------------------------------
# Vg Pulse Scheduler using threading.Thread
# -------------------------------
class VgPulseScheduler:
    def __init__(self, keithley):
        self.k = keithley
        self._running = False
        self._thread = None

    def start_periodic(self, high, low, period_s, duration_s=None):
        """Run Vg pulses in a separate thread."""
        if self._running:
            return
        self._running = True

        def worker():
            t_end = time.time() + duration_s if duration_s else float('inf')
            while self._running and time.time() < t_end:
                self.k.set_voltage(Vg=high)
                time.sleep(period_s / 2)
                if not self._running:
                    break
                self.k.set_voltage(Vg=low)
                time.sleep(period_s / 2)

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
            self._thread = None

# -------------------------------
# Example Usage (Terminal)
# -------------------------------
if __name__ == "__main__":
    # Assume you already have Keithley2636B instance
    from keithley import Keithley2636B  # your existing class
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    keithley = Keithley2636B(RESOURCE_ID)
    keithley.connect()
    keithley.clean_instrument()
    keithley.config()
    keithley.set_voltage(Vd=1.0, Vg=0.0)

    # Start measurement worker
    measure_worker = MeasureWorker(keithley, interval=0.1, csv_file="data.csv")
    measure_worker.new_data.connect(lambda t, Vg, Vd, Id, Ig: print(f"{t:.2f}s | Vg={Vg} | Vd={Vd} | Id={Id:.3e} | Ig={Ig:.3e}"))
    measure_worker.start()

    # Start periodic Vg pulse
    pulse = VgPulseScheduler(keithley)
    pulse.start_periodic(high=1.0, low=-1.0, period_s=2.0, duration_s=10.0)  # 2 s period, 10 s total

    try:
        while True:
            cmd = input("Type 'stop' to end, or 'Vg <value>' / 'Vd <value>': ").strip()
            if cmd.lower() == 'stop':
                break
            elif cmd.startswith('Vg'):
                _, val = cmd.split()
                keithley.set_voltage(Vg=float(val))
            elif cmd.startswith('Vd'):
                _, val = cmd.split()
                keithley.set_voltage(Vd=float(val))
    except KeyboardInterrupt:
        pass
    finally:
        pulse.stop()
        measure_worker.stop()
        keithley.set_voltage(Vd=0, Vg=0)
        keithley.shutdown()
        print("Finished.")
