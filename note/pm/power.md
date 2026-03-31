## `power.py`
This script serves as a hardware abstraction layer for a **Thorlabs PM100D Power Meter**. It uses PyVISA to communicate with the instrument to measure optical power (Watts).

---

### 1. Initialization and Connection: `__init__`
This method establishes the digital link to the specific power meter model.

* **`self.rm.list_resources(...)`**: Searches for a very specific USB hardware ID (`0x1313::0x8078`). This ensures the script only attempts to connect to a compatible Thorlabs PM100D device.
* **`self.meter.read_termination = '\n'`**: Defines the end of a message, allowing Python to know exactly when the instrument has finished sending a data string.
* **`sense:power:unit W`**: Explicitly sets the measurement unit to Watts.
* **`sense:power:range:auto 1`**: Enables "Auto-ranging," allowing the meter to automatically switch internal sensitivity levels based on the strength of the incoming light.

---

### 2. Sensor Calibration: `config_meter` and `zero_sensor`
These functions prepare the hardware for the specific wavelength and environment of your experiment.

* **`sense:average:count {average_count}`**: Sets internal hardware-level averaging. A higher count (e.g., 20) smooths out high-frequency noise from the laser or ambient light.
* **`sense:correction:wavelength {wavelength}`**: **Critical Step.** Power meter sensors have different sensitivities for different colors of light. This command tells the meter which wavelength (e.g., 660nm) you are using so it can apply the correct internal calibration factor.
* **`sense:correction:collect:zero`**: Initiates the "Dark Current" calibration.
* **`query('*opc?')`**: This is a "Wait" command. It stands for "Operation Complete" and prevents Python from sending more commands until the internal zeroing process is finished.


---

### 3. Data Acquisition: `measure_power`
This function captures a time-series of power data.

* **`np.zeros(num_points)`**: Pre-allocates memory for the arrays. This is more efficient than "appending" to a list during high-speed measurements.
* **`time.perf_counter()`**: Uses a high-resolution hardware timer (more accurate than `time.time()`) to track the exact elapsed time between measurements.
* **`query('measure:power?')`**: Triggers a new measurement on the PM100D and immediately requests the result.
* **`time.sleep(measure_interval)`**: Controls the sampling rate (e.g., one measurement every 0.2 seconds).

---

### 4. Summary of Functions in `power.py`

| Function | Purpose |
| :--- | :--- |
| **`__init__`** | Locates and opens the USB connection specifically for a Thorlabs PM100D. |
| **`config_meter`** | Configures the hardware for a specific laser wavelength and sets the noise-smoothing level. |
| **`zero_sensor`** | Calibrates the sensor for "true dark" to remove electronic offsets. |
| **`measure_power`** | Performs a sequence of measurements and returns them as two NumPy arrays: Time and Power. |
| **`close_meter`** | Safely releases the USB resource and shuts down the PyVISA manager. |
