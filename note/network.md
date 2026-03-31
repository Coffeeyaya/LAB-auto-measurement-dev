In your system, `network.py` acts as the communication bridge between the **Electrical Computer** (running the Keithley) and the **Light Computer** (controlling the Laser). Since these two tasks often run on different physical machines, this script uses **TCP/IP Sockets** to send commands over your local network (RJ45 to usb-A connection).

---

## 1. Server Setup Function
* **`create_server(host, port, backlog=1)`**: 
    * `socket.socket(...)`: Creates a new internet-stream socket.
    * `setsockopt(..., SO_REUSEADDR, 1)`: Allows you to restart the script immediately if it crashes, without waiting for the operating system to time out the port.
    * `bind((host, port))`: Associates the server with a specific IP and Port.
    * `listen(backlog)`: Puts the socket in "listening" mode, ready to accept incoming connections from the Electrical Computer.

---

## 2. The `Connection` Class (Standard)
This class wraps a raw socket to make sending and receiving data easier and more reliable.

* **`__init__(self, sock)`**: Stores the active socket and initializes an empty `buffer` string to handle partial data packets.
* **`connect(cls, host_ip, port)`**: A "Class Method" that creates a socket, connects it to the server, and returns a fully initialized `Connection` object.
* **`accept(cls, server_socket)`**: Used by the server to wait for a client; it returns the new connection and the client's address.
* **`send(self, msg)`**: Appends a newline (`\n`) to your string, encodes it into bytes, and sends it all at once.
* **`receive(self)`**: 
    * This is the most complex logic. It reads data from the socket in 1024-byte chunks.
    * It checks the `buffer` for a newline (`\n`). If it finds one, it "slices" the first complete message out and saves the rest for the next call.
* **`send_json(self, obj)` / `receive_json(self)`**: These are "helper" functions that automatically convert Python dictionaries into JSON strings for transmission and back again.
* **`close(self)`**: Safely shuts down the communication link.

---

## 3. The `ReconnectConnection` Class (Robust)
This is an "Advanced" version of the connection class. It is designed for long experiments where the network might briefly drop or the server might be restarted.

* **`_connect(self)`**: Runs a `while True` loop that keeps trying to reach the server every few seconds until it succeeds.
* **`send_json(self, data)`**: Wraps the send logic in a `try/except` block. If the network fails (`OSError`), it automatically calls `_connect()` to fix the link and then tries to send the message again.
* **`receive_json(self)`**: Similar to send, if the connection is lost while waiting for a response, it reconnects automatically.
* **`close(self)`**: Closes the socket safely, ignoring errors if the socket is already dead.

---

## Summary of Purpose
| Function Category | Purpose |
| :--- | :--- |
| **Server Creation** | Used on the **Light Computer** to wait for instructions. |
| **Connection Handling** | Manages the "byte-to-string" conversion and ensures messages aren't cut in half. |
| **JSON Helpers** | Allows you to send complex commands (like `{"channel": 6, "power": 17}`) easily. |
