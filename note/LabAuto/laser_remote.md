## `laser_remote.py`
The `laser_remote.py` script is the high-level **wrapper** that sits on the Electrical Computer. Its primary job is to solve a major performance bottleneck: **Network Lag**.

Normally, waiting for a remote computer to click a GUI and send back an "ACK" (acknowledgment) would pause your Keithley measurement for 1–2 seconds. This class uses **Multithreading** and a **Queue** to make laser control "non-blocking".

---

### 1. The Architecture: Asynchronous Threading
Instead of sending a command and waiting for a reply in your main experiment loop, this class creates a separate, "invisible" worker.

* **`self.cmd_queue = queue.Queue()`**: Acts as a "mailbox". The main experiment drops a command in the mailbox and immediately continues measuring the Keithley.
* **`self.worker = threading.Thread(...)`**: This is the dedicated "mail carrier". It runs in the background, constantly checking the mailbox, sending the JSON to the Light Computer, and waiting for the reply so the main script doesn't have to wait.


---

### 2. The Internal Network Worker: `_network_worker(self)`
This is the loop running inside the background thread.

* **`task = self.cmd_queue.get(timeout=0.2)`**: It tries to grab a command from the queue. The timeout ensures the thread stays responsive and can check if `self.running` has become `False`.
* **`self.conn.send_json(payload)`**: It transmits the command (like `{"channel": 6, "on": 1}`) to the laser server.
* **`reply = self.conn.receive_json()`**: It waits for the "ACK" from the Light Computer.
* **`self.cmd_queue.task_done()`**: This signals that the background task is finished, allowing the queue to process the next item.

---

### 3. User Commands: `send_cmd(self, ...)`
This is the function you actually call in your measurement scripts. It has two modes:

* **Fire-and-Forget (`wait_for_reply=False`)**: 
    * This is the "High Performance" mode.
    * It drops the command in the queue and returns in about **1 microsecond**, allowing your Keithley loop to keep sampling at a high frequency while the laser turns on in the background.
* **Synchronous Mode (`wait_for_reply=True`)**:
    * Used when you absolutely *must* confirm the light is on before proceeding.
    * **`self.cmd_queue.join()`**: This forces the main script to pause until the background worker has finished the task and received the reply.

---

### 4. Lifecycle Management
* **`close(self)`**: 
    * Sets `self.running = False` to tell the background thread to stop its loop.
    * **`self.worker.join(timeout=1.0)`**: Waits up to one second for the background thread to finish cleanly before closing the actual network socket (`self.conn.close()`).

---

### Summary of Purpose
| Component | Purpose |
| :--- | :--- |
| **`cmd_queue`** | Buffers laser commands so the Keithley script doesn't have to wait for the network. |
| **`_network_worker`** | Handles the actual "talking" to the Light Computer in a background thread. |
| **`send_cmd`** | Provides an interface to switch between "Fast" (asynchronous) and "Safe" (synchronous) control. |


## Detailed note:

#### 1. Core Architecture: The "Non-Blocking" Worker
The class uses a **Producer-Consumer** pattern with two distinct threads:
* **Main Thread (Producer):** Runs your experiment/Keithley loop. It drops commands into a "mailbox" (`self.cmd_queue`) and keeps moving.
* **Background Worker (Consumer):** An independent thread that sits in a `while` loop. It waits for commands, handles the "blocking" network communication (`send_json` and `receive_json`), and signals when done.



#### 2. Program Flow: Synchronous vs. Asynchronous
The `send_cmd` method allows you to choose your priority based on the experiment type:

| Case | Mechanism | Program Flow | Best Used For |
| :--- | :--- | :--- | :--- |
| **Asynchronous** (`wait_for_reply=False`) | `queue.put()` | **Fire-and-Forget:** Main thread returns in ~1µs. Keithley sampling continues at maximum frequency. | Time-dependent transient measurements. |
| **Synchronous** (`wait_for_reply=True`) | `queue.put()` + `queue.join()` | **Blocking:** Main thread pauses until the background worker receives an "ACK" from the laser. | Steady-state Id-Vg sweeps where light state must be confirmed. |



#### 3. Communication Logic: The `response_container`
Since background threads cannot "return" values to the main thread, this script uses a **shared mutable list** called a `response_container`.
1.  **Main Thread** creates an empty list `[]` and puts it in the queue.
2.  **Worker Thread** receives the JSON reply from the network and `appends` it to that specific list.
3.  **Main Thread** (after `queue.join()`) reads the first item from that list to get the result.

#### 4. Thread Synchronization Signals
* **`task_done()`**: Called by the **Worker** after processing a command. It decrements the queue's internal counter. It **does not** end the worker thread.
* **`join()` (Queue)**: Called by the **Main Thread**. It pauses execution until the queue counter hits zero.
* **`join()` (Thread)**: Called during `close()`. It waits for the background thread to exit its loop and terminate completely.
