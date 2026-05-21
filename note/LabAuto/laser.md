## `laser.py`
This script is fundamentally different from the others. While the Keithley uses a direct digital API, the AOTF Laser Controller software likely has no programming interface. Therefore, `laser.py` uses **Computer Vision and Mouse Automation** (via `pyautogui`) to "play" the software like a human would.

---

### 1. Initialization and Mapping
* **`init_AOTF()`**: 
    * It searches for a window titled "AOTF Controller" using `pygetwindow`.
    * It forces the window to the top-left corner `(0, 0)` so that all subsequent mouse coordinates are predictable.
    * It creates a **Coordinate Grid**: It uses `numpy` to define 8 rows (channels) and 3 columns (Lambda, Power, ON/OFF).
    * **Returns**: A dictionary where you can look up `grid[channel]["lambda"]` to get the exact (X, Y) pixel location to click.

* **`get_popup_window(window_title)`**: 
    * When you click a channel, a sub-window (popup) appears. This function waits up to 5 seconds for that popup to exist.
    * Once found, it activates the popup so the script can type values into it.

---

### 2. Coordinate Math
Since the popup windows always appear in the same relative position, these functions calculate the "offset" from the main window to find the text boxes:
* **`get_lambda_edit_coord` / `get_power_edit_coord`**: These take a base coordinate and add fixed pixels (e.g., `+350` or `+295`) to find the specific input field where the number is typed.
* **`get_lambda_ok_coord` / `get_power_ok_coord`**: Calculates the position of the "OK" or "Confirm" button to close the popup.

---

### 3. Interaction Helpers
* **`move_and_click(coord)`**: A simple wrapper that moves the mouse to a location and performs a click with a short delay to ensure the OS registers the event.
* **`fill_box_no_ctrl_a(content)`**: 
    * Instead of riskily trying to "Select All," it copies your value (like "660") to the **System Clipboard** using `pyperclip`.
    * It then triggers a `Ctrl+V` (Paste) and hits `Enter`.
* **`press_on_button(grid, channel)`**: Looks up the "ON" toggle for the specified channel and clicks it.

---

### 4. High-Level Logic (The "Functions")
* **`change_lambda_function`**: 
    1.  Clicks the wavelength button on the main grid.
    2.  Waits for the `popup wavelength slider.vi` window.
    3.  Double-clicks the entry box to prepare for typing.
    4.  Pastes the new wavelength and clicks "OK".

* **`change_power_function`**: 
    * Follows the same logic as the wavelength function but targets the power button and the `popup power slider.vi` window.

---

### Summary of Purpose
| Function | Scientific Purpose |
| :--- | :--- |
| **`init_AOTF`** | Calibrates the software position on your monitor. |
| **`change_lambda_function`** | Automatically sets the laser wavelength (400nm – 700nm). |
| **`change_power_function`** | Automatically sets the laser intensity (0% – 100%). |
| **`press_on_button`** | Physically toggles the light for a specific channel. |

**Critical Note for Modularization**: Because this script relies on screen pixels, it will **break** if the "AOTF Controller" window is resized or if the monitor resolution changes. 
