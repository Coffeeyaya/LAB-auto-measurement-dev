## `idvg_pulse.py`
This script is the engine for your **Pulsed Transfer Characteristics**. While the Time-Dependent script measures how current degrades over *time*, this script measures how current responds to *changing gate voltages*, but uses microsecond pulses to prevent bias stress from ruining the measurement.

Here is the "Architect's Breakdown" of the purpose of each major block and function in your code:

---

### Part 1: The Preparations
Before the Keithley even fires a voltage, the script ensures the environment is safe and calibrated.

* **`get_pp_exact` (The Translator):** * **Purpose:** The laser hardware only understands "Percentage (0-100%)", but physics is done in "Nanowatts". This function reads your calibration CSV and translates requested optical power into the correct hardware percentage.
* **`_setup_files` (The Safety Net):**
    * **Purpose:** Generates the `.csv` and `.json` filenames. Crucially, if it sees that `idvg_1-1_1.csv` already exists, it instantly aborts the script. This prevents you from accidentally overwriting a hard-earned dataset if you forget to update the "Run Number" in the UI.

---

### Part 2: The Physics Engine (`AutoIdVgWorker.run`)
This is the core of the script. It reads like a chronological recipe for a perfect semiconductor measurement.

#### 1. The Pre-Conditioning Phase
Before taking data, the device must be put into a known, baseline state.
* **Dark Wait (`wait_time`):** Allows the semiconductor to relax in the dark if it was previously exposed to ambient room light while you were loading the sample.
* **The Depletion Step (`deplete_voltage` & `deplete_time`):** * **Purpose:** If your device has charge traps filled with electrons, this step applies a strong reverse-bias voltage for a few seconds to violently "flush" those traps empty. This ensures every sweep starts from the exact same baseline.
* **Laser Stabilization (`laser_stable_time`):** If the laser is used, it turns the light on and waits. Lasers take time to reach thermal equilibrium; measuring instantly would result in a creeping, inaccurate photocurrent.

#### 2. The Sweep Execution (The "Pulse" Mechanics)
This block (lines 149-183) is the most critical part of the entire file. It sets up the conditions required for microsecond hardware pulses.
* **`set_autorange(..., 0)` & `set_range`:** * **Purpose:** Disables the Keithley's "smart" auto-ranging. If left on, the Keithley tries to mechanically click physical relays during the 5ms pulse to find the best range, causing massive lag and ruining the pulse timing. By forcing a `fixed_range_a`, the hardware is locked and ready for high-speed action.
* **`k.set_Vg(base_vg)`:** * **Purpose:** Drops the device to its resting voltage (often 0V). This is where the device "lives" when it is not being actively measured.
* **The `for vg in vg_points:` Loop:**
    * **Purpose:** Iterates through your requested voltage steps (e.g., -5V to +5V).
    * Instead of slowly ramping the voltage, it fires `measure_pulsed_vg`. The hardware instantly spikes to the target `vg`, takes a snapshot of the current, and instantly drops back to `base_vg`.
    * **`time.sleep(rest_time)`:** Forces the script to pause (e.g., for 100ms) before firing the next point. This allows the semiconductor lattice to "breathe" and release any temporary charge trapped during that 5ms pulse.

---

### Part 3: The Monitor (`AutoIdVgWindow`)
Because the Worker is operating in the background, this GUI class acts as your live window into the experiment.

* **Logarithmic Y-Axis (`self.ax1.set_yscale('log')`):** * **Purpose:** Transfer characteristics (Id-Vg) are almost always viewed on a Log scale because Drain Current changes by orders of magnitude (from picoamps to microamps) as the transistor turns on.
* **The 10Hz Plot Throttle (`current_time - self.last_draw_time > 0.1`):**
    * **Purpose:** If you are pulsing very fast, the Worker thread will spit out data incredibly quickly. Redrawing a Matplotlib UI takes heavy CPU power. This `if` statement acts as a throttle, ensuring the UI only repaints the screen a maximum of 10 times per second, keeping your computer perfectly smooth while the hardware runs at max speed.
* **Safe Shutdowns (`closeEvent` & `on_finished`):**
    * **Purpose:** If you get bored and click the red 'X' to close the window halfway through a sweep, these functions catch that event, stop the Worker, command the laser to turn off, and tell the Keithley to drop its voltage to 0V before the Python process actually dies.

### Summary
Every line in this script is designed to solve a specific physical problem: `fixed_range` solves mechanical hardware lag, `depletion` solves charge trapping history, and the `background thread` + `GUI throttle` solves software UI freezing.