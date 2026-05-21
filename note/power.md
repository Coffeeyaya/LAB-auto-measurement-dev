## `power.py`
The script is a **calibration utility**. Its primary goal is to find the exact "Power Percentage" (PP) setting in the laser software required to achieve a specific physical "Target Power" (in nanowatts) at a given wavelength. Since laser diodes are nonlinear and their efficiency changes with wavelength, this script automates the tedious process of manual calibration.

---

### 1. The Core Logic: `find_pp_for_target_power`
This function uses a **Binary Search Algorithm** to find the correct laser setting. Instead of checking every percentage from 1 to 150, it narrows down the correct value mathematically.


* **`mid = (low + high) / 2`**: The script starts by testing the middle value of the current range.
* **`laser.send_cmd(...)`**: It sends the command to the Light Computer to set the laser to that "mid" power and turn it ON.
* **`pm.measure_power(...)`**: It captures several data points from the Thorlabs power meter.
* **`np.mean(p[-3:])`**: To avoid noise, it averages only the last three measurements once the sensor has stabilized.
* **The Decision Logic**:
    * If the measured power is **higher** than the target, the new "high" bound becomes `mid`.
    * If the measured power is **lower**, the new "low" bound becomes `mid`.
* **`tolerance`**: The loop stops once the difference between the measured and target power is small enough (e.g., within 2 nW).

---

### 2. The Multi-Calibration Wrapper: `multi_power_multi_wavelength`
This function automates the calibration for an entire array of different colors (wavelengths) and intensities.

* **`pm.zero_sensor()`**: Before starting, it calibrates the power meter for absolute darkness to ensure accurate readings.
* **`sorted_powers = sorted(power_arr)`**: It sorts the target powers from lowest to highest.
* **Dynamic Bounding Optimization**: 
    * This is a clever efficiency trick. 
    * Once the script finds the PP for 10 nW (e.g., PP = 25), it knows that 20 nW **must** require a PP higher than 25. 
    * It updates `current_pp_min = pp`, so the next search starts at 25 instead of 1, saving several iterations.

---

### 3. Data Storage and Output
The script produces two main results, which it organizes using **Pandas DataFrames**:

1.  **`pp_df`**: A table where the rows are wavelengths and columns are target powers. Each cell contains the **Laser PP setting** needed.
2.  **`measured_power_df`**: A table showing the **actual power** measured at those settings to verify accuracy.

Both are saved as CSV files in a `/calibration` folder for other scripts to use later.

---

### 4. Summary of Function Purposes

| Function | Detailed Purpose |
| :--- | :--- |
| **`find_pp_for_target_power`** | Uses binary search to find the laser setting (PP) for one specific power/wavelength. |
| **`multi_power_multi_wavelength`** | Orchestrates a full calibration sweep across multiple channels and intensities. |
| **`pm.config_meter`** | Configures the PM100D for the correct wavelength before measuring. |
| **`laser.send_cmd`** | Remote-controls the laser GUI to toggle power and states. |

---

### 5. Hardware Safety & Robustness
* **`try...finally`**: No matter if the code crashes or finishes successfully, `pm.close_meter()` is always called to release the USB resource.
* **Wait times (`time.sleep(1)`)**: These allow the laser GUI popups to close and the power meter sensor to settle after the light intensity changes.
