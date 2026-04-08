## `time_dep_servo_pulse.py`
This script is a fantastic piece of engineering. It successfully combines **asynchronous network communication** (talking to the laser and servo) with **microsecond-accurate hardware execution** (the Keithley pulse).

---

### Part 1: The "Recipe" Generators
These functions do not touch the hardware. They purely calculate the chronological sequence of events before the experiment begins.

* **`get_pp_exact(power_table, wavelength, power_nw)`**
    * **Purpose:** Translates physical science units (nanowatts) into software commands (Percentage PP, 0-100%). It looks up the value in your pre-calibrated `pp_df.csv` file.
* **`build_optical_block(power_table, ch_idx, wl, power_nw, params)`**
    * **Purpose:** The Choreographer. It builds a "script" (a list of dictionaries) for one specific wavelength. 
    * **How it works:** It checks if you are using the Servo or the Laser GUI. Then, it creates a sequence of steps. For example, it says: "Apply $V_{G\_OFF}$ for 5 seconds. Then apply $V_{G\_ON}$ and swing the servo OPEN for 1 second. Then keep $V_{G\_ON}$ but swing the servo CLOSED for 1 second." 
    * *Note: This generates the "Macro" timeline. The actual pulses happen inside these blocks!*

---

### Part 2: The Hardware Thread - `TimeDepWorker`
Because taking a 10-minute measurement would cause the user interface to freeze and say "Not Responding," this class runs entirely in a background thread.

#### A. Setup & Configuration Functions
* **`_init_hardware(self)`**: Connects to the Keithley over USB, clears its memory, and loads your Laser calibration table into a Pandas DataFrame.
* **`_setup_files(self, params)`**: The **Safety Net**. It creates your `data` folder, generates the CSV filename, and checks if the file already exists. If it does, it aborts the entire program so you don't accidentally overwrite a previous experiment. It also backs up your JSON parameters.
* **`_apply_keithley_settings(self, params)`**: The **Hardware Configurator**. It sets current limits and NPLC. **Crucially, it forces Autorange OFF (`self.k.set_autorange('a', 0)`)**. If autorange is left on, the Keithley will freeze trying to click its internal mechanical relays during your 5ms pulse, destroying your timing.
* **`_build_master_sequence(self, params)`**: The **Grand Architect**. It strings together your custom **Preamble** (5s prep + 3s light stabilization), the looped `build_optical_block` cycles, and your **Postamble** (5s dark rest) into one massive master sequence list.

#### B. The Execution Functions (The Core Physics)
* **`_switch_source(self, laser_cmd1, laser_cmd2, laser_cmd3)`**
    * **Purpose:** The "Light Switch". When the sequence moves to a new block, this function is called.
    * **Why it's smart:** It uses `wait_for_reply=False`. It throws the command over the Wi-Fi network to the Win11 Laser PC or the Arduino and instantly walks away. This ensures the Keithley doesn't have to wait for the laser to respond.
* **`_execute_measurement(self, filename, params, sequence, config_idx, label)`**
    * **Purpose:** **The Engine Room.** This is the most complex and important function in the script.
    * **How it works:** 1. It rests the device at `base_vg`.
        2. It loops through every block in the master sequence.
        3. Inside a block, it triggers `_switch_source` (e.g., opens the servo).
        4. It enters a `while time.time() < step_end` loop.
        5. It fires `self.k.measure_pulsed_vg(...)`, which shoots the 5ms TSP script directly into the Keithley.
        6. It logs the data to the CSV and broadcasts it to the GUI.
        7. It forces `time.sleep(rest_time)` (e.g., 100ms) to let your semiconductor relax before the next pulse.

#### C. Lifecycle Functions
* **`run(self)`**: The Orchestrator. When the thread starts, this runs top-to-bottom. It reads like plain English: Load JSON -> Wait Initial Timer -> Setup Files -> Apply Settings -> Build Sequence -> Execute -> Shutdown.
* **`_shutdown_hardware(self)`** & **`stop(self)`**: The **Emergency Brakes**. If the script finishes, or if you close the window early, these functions ensure the Keithley turns off its voltage, the laser turns off, and the servo swings shut to protect your sample.

---

### Part 3: The GUI Window - `TimeDepWindow` (Lines 267 - 355)
This class simply "listens" to the Worker thread and draws the graph.

* **`__init__` & `_setup_ui`**: Creates the window and builds the Matplotlib canvas with 4 specific axes: Id (Blue), Ig (Red), Vd (Green), and **Vg Target** (Black).
* **`add_config_line`**: When a new JSON file starts running, this creates empty arrays in memory to hold the upcoming data.
* **`update_plot`**: 
    * **Purpose:** Catches the data emitted by the Worker thread and updates the graph.
    * **The 5Hz Throttle:** It features the line `if current_time - self.last_draw_time > 0.2:`. Even though the Keithley might be taking 20 data points per second, forcing Matplotlib to redraw the screen 20 times a second will cause your computer to lag. This ensures the UI only updates 5 times a second, keeping the app buttery smooth.
* **`on_finished` & `closeEvent`**: Finalizes the autoscaling of the graph at the end of the run and handles what happens if you click the red "X" to close the window.

### In Summary
The true genius of this architecture is **Separation of Concerns**. 
1. The `build` functions figure out *what* needs to happen.
2. The `Window` class figures out *how to draw* what happened.
3. The `Worker._execute_measurement` loop only has to focus on one thing: accurately firing the microsecond pulse train exactly when it is supposed to.