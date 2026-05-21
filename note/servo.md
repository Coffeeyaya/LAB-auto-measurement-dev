## `servo.py`
The script serves as the **Hardware Abstraction Layer (HAL)** for a mechanical shutter system. While your laser is controlled via software GUI clicks, some of your experiments use a physical servo motor (connected to an Arduino) to physically block or unblock a light path.

---

## 1. Connection and Auto-Detection
This script is designed to be "plug-and-play" across different computers.

* **`auto_detect_port(self)`**: 
    * It scans the computer's USB ports using `serial.tools.list_ports.comports()`.
    * It looks for keywords like "CH340" (a common USB-to-Serial chip) or "Arduino".
    * If it fails to find a match, it provides **OS-specific fallbacks** (e.g., `COM3` for Windows or `/dev/cu...` for macOS).
* **`__init__(self, ...)`**: 
    * **`self.ser = serial.Serial(...)`**: Opens the actual data pipe to the Arduino at 9600 baud.
    * **`time.sleep(2)`**: This is a **critical safety delay**. Most Arduinos reset automatically when a serial connection is opened. This sleep ensures the Arduino finishes rebooting before Python tries to send commands.

---

## 2. Motor Logic and Movement
The script treats the servo motor as a binary "Light Toggle".

* **`angle_on` and `angle_off`**: These store the specific physical angles (e.g., 70° and 90°) that correspond to the shutter being open or closed.
* **`set_angle(self, value)`**: 
    * Converts the integer angle into a string, appends a newline (`\n`), and encodes it into **UTF-8 bytes**. 
    * The Arduino receives this number and moves the motor arm accordingly.
* **`toggle_light(self)`**: 
    * Manages the internal state `self.is_on`. 
    * If the light is currently ON, it sends the `angle_off` command; otherwise, it sends `angle_on`.


---

## 3. Safety and Teardown
* **`close(self)`**: 
    * **`self.set_angle(self.angle_off)`**: Ensures the shutter is physically closed before the program exits.
    * **`time.sleep(0.5)`**: This is a "mechanical delay". It gives the physical motor enough time to finish rotating before the software cuts the power to the serial port.

---

## Summary of Functionality

| Function | Purpose |
| :--- | :--- |
| **`__init__`** | Connects to the Arduino and waits for the hardware to wake up. |
| **`auto_detect_port`** | Searches for the Arduino hardware ID so you don't have to manually change COM ports. |
| **`set_angle`** | Sends a raw degree value (0-180) to the motor. |
| **`toggle_light`** | Flips the shutter between its predefined "On" and "Off" positions. |
| **`close`** | Safely parks the motor in the closed position and releases the USB port. |

---

### Understanding the Full "Shutter" Flow:
1.  **Python Script**: Calls `servo.toggle_light()`.
2.  **`servo.py`**: Sends the string `"70\n"` over the USB cable.
3.  **Arduino**: (Running its own internal code) reads `"70"`, converts it to a PWM signal, and moves the motor.
4.  **Hardware**: The mechanical arm moves, allowing light to hit your 2D material device.
