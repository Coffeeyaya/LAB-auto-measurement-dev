## `laser_control.py`
The script is the **Server-Side Application** that runs on the **Light Computer**. It translates incoming network messages into physical mouse clicks on the laser's GUI. It is designed to be a persistent service that stays open and waits for the Electrical Computer to send commands.

---

### 1. The Multi-Layer Loop Architecture
This script uses a nested loop structure to ensure it is robust against network drops or experimental restarts.

#### The Outer Loop (`while True`)
* **Purpose**: Keeps the server software running infinitely.
* **`init_AOTF()`**: Every time a new experiment starts, it re-initializes the AOTF GUI mapping. This ensures that even if someone moved the laser window, the script "finds" it again before starting.
* **`Connection.accept(server_socket)`**: The script pauses here and "listens" for the Electrical Computer to connect over the network.

#### The Inner Loop (`while True`)
* **Purpose**: Handles the "conversation" during a single active experiment.
* **`conn.receive_json()`**: It waits for a specific command packet (e.g., `{"channel": 6, "on": 1}`).
* **Error Handling**: If the Electrical Computer crashes or the cable is unplugged, the `except` block catches the error, breaks the inner loop, and returns to the Outer Loop to wait for a fresh connection.

---

### 2. Logic and Bug Prevention
* **`is not None` Checks**: A critical fix was implemented here. In Python, `if 0:` is considered `False`. Since the Laser has a **Channel 0**, a standard `if channel_recv:` check would fail to process that channel. Using `is not None` ensures Channel 0 is handled correctly.
* **Sequential Processing**: The script checks for `wavelength`, then `power`, then `on`. It calls the corresponding functions from `laser.py` to perform the clicks.
* **`time.sleep(1)`**: Adds a small delay after GUI actions to allow the AOTF software's popup windows to close and the main window to become responsive again.

---

### 3. The Acknowledgment (ACK) System
* **`conn.send_json({"response": "ACK"})`**: After the mouse has finished clicking, the server sends an "ACK" message back to the Electrical Computer.
* **Purpose**: This is what releases the `queue.join()` block in your `laser_remote.py` script. It guarantees the Electrical Computer doesn't start measuring the Keithley until the light is actually physically toggled.


---

### 4. Summary of Functionality

| Line/Block | Purpose |
| :--- | :--- |
| **`run_laser_server`** | The main entry point that sets up the IP (`0.0.0.0` allows any IP to connect) and the port (`5001`). |
| **`try...finally`** | Ensures that if the script is stopped, the `server_socket` is properly closed, preventing "Port already in use" errors on restart. |
| **`change_lambda_function`** | Called only if the incoming data contains a "wavelength" key. |
| **`change_power_function`** | Called only if the incoming data contains a "power" key. |
| **`press_on_button`** | Called only if the incoming data contains an "on" key. |

---

### Final Overview of the Entire System Flow
1. **Electrical Computer** calls `send_cmd()`.
2. **`laser_remote.py`** sends a JSON packet over the network.
3. **`laser_control.py`** (this script) receives the JSON.
4. **`laser.py`** moves the mouse and clicks the GUI buttons.
5. **`laser_control.py`** sends back an "ACK".
6. **Electrical Computer** receives "ACK" and continues measuring the Keithley.
