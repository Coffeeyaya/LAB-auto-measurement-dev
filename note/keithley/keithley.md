## `keithley.py`
The functions are designed to bridge the gap between high-level Python logic and the low-level **TSP (Test Script Processor)** language used by the Keithley 2636B.

- `smu a`: drain 
- `smu b`: gate

### 1. Connection and Lifecycle
* **`__init__`**: Initializes the class instance, sets default measurement parameters (like NPLC and Current Limits), and creates a `threading.Lock` to ensure only one command is sent to the hardware at a time.
* **`connect`**: Initializes the PyVISA Resource Manager and opens a communication session with the physical instrument via its USB address.
* **`shutdown`**: Safely ramps voltages to zero, disables the physical output relays, and closes the connection to the instrument.
* **`__enter__` / `__exit__`**: Implements "Context Manager" support, allowing you to use the `with` statement to ensure the Keithley connects at the start and shuts down automatically at the end, even if the code crashes.

### 2. Hardware Configuration
* **`config`**: Sets the fundamental operating mode (Voltage Source) for both channels and sets the "limit"(compliance), "range" and "NPLC" (measurement resolution).
* **`clean_instrument`**: A "hard reset" routine that clears the device's memory, resets it to factory defaults, and flushes any error messages from the internal queue.
* **`set_auto_zero_once`**: Triggers a single internal calibration to cancel out thermal offsets, improving speed by not re-calibrating for every single point.
* **`set_nplc`**: Adjusts the integration time (Number of Power Line Cycles) to trade off between measurement speed and electrical noise rejection.
* **`set_range` / `set_autorange`**: Manually sets or enables the automatic selection of the current measurement range (e.g., 100nA vs 1mA).
* **`set_limit`**: Updates the current compliance (limit) to protect the 2D material device from overcurrent damage.

### 3. Voltage and Output Control
* **`enable_output`**: Turns the physical "Output" button on the Keithley ON or OFF for a specific channel.
* **`set_Vd`**: Sets the Drain voltage ($V_D$) on SMU Channel A.
* **`set_Vg`**: Sets the Gate voltage ($V_G$) on SMU Channel B.

### 4. Measurement and Pulsing
* **`measure`**: Queries the instrument for the current readings of both the Drain and the Gate simultaneously and returns them as floats.
* **`measure_pulsed_vg`**: Sends a "script" to the Keithley hardware to apply a voltage, wait for a precise duration (e.g., 5ms), measure the current, and return to 0V—all within the instrument's own processor to avoid computer lag.