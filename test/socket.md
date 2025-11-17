# Python socket programming
# 1. setup host to wait for clients
- `create_server` will return `socket.socket` object that can be sent into the following `Connection` object
```python
def create_server(host, port, backlog=1):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(backlog)
    print(f"Server listening on {host}:{port}...")
    return server_socket
```

| Line                                  | Meaning                                                                           |
| ------------------------------------- | --------------------------------------------------------------------------------- |
| `socket.socket(AF_INET, SOCK_STREAM)` | Create a TCP socket using IPv4                                                    |
| `setsockopt(... SO_REUSEADDR, 1)`     | Allow immediate reuse of the port (avoids “address already in use” after crashes) |
| `bind((host, port))`                  | Attach this socket to a network interface & port                                  |
| `listen(backlog)`                     | Start listening for incoming connections (queue size = `backlog` = #clients it can accept)                 |


# 2. Connection class: TCP wrapper
- for high-level communication using string and json, rather raw bytes
## 2.1 init, connect (by client), accept (by server)
```python
class Connection:
    """
    socket connection class
    """
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buffer = ""

    @classmethod
    def connect(cls, host_ip: str, port: int):
        """
        Connect to a server and return a Connection object.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host_ip, port))
        print(f"Connected to {host_ip}:{port}")
        return cls(s)
    
    @classmethod
    def accept(cls, server_socket: socket.socket):
        """
        Accept a new client from a server_socket.
        """
        conn, addr = server_socket.accept()
        print(f"Connected by {addr}")
        return cls(conn), addr
    # note: use @classmethod, to call connect and accept before creating the obj
```
- `__init__`: Stores the socket, Keeps a buffer for incomplete incoming messages
- `connect`: Used by client side
  - Creates a socket, connects, and returns a `Connection` object.
- `accept`: Used by server side
  - Accepts an incoming connection and wraps it in a `Connection` object.
- Using `@classmethod` allows:
    ```python
    conn = Connection.connect(...)
    ```
    without constructing the object manually.


## 2.2 send and receive messages
```python
def send(self, msg: str):
        """
        Send a newline-terminated string message.
        """
        self.sock.sendall((msg + "\n").encode())
        print(f"[SEND] {msg}")

def receive(self) -> str:
    """
    Receive one complete newline-terminated message.
    """
    while True:
        if "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            line = line.strip()
            if line:
                print(f"[RECV] {line}")
                return line
        chunk = self.sock.recv(1024).decode()
        if not chunk:
            raise ConnectionError("Connection closed by peer")
        self.buffer += chunk
```
- `send`:
  - Adds a newline terminator `\n`
  - Encodes the string to bytes
  - Ensures full transmission (`sendall()`)
- `receive`:
- Check if there’s a `newline` in the buffer
  - If yes, extract one full line.
  - If not, call `sock.recv(1024)` to read more bytes.
    - Append to buffer
    - Repeat
  - TCP does not preserve message boundaries, so you must do this manually.
## 2.3 wait for messages
```python
def wait_for(self, target: str):
    while True:
        msg = self.receive()  # could be str OR dict?
        if msg == target:  # handle old plain string
            return msg
        # if isinstance(msg, dict) and msg.get("cmd") == target:  # handle JSON
        #     return msg
```
- A `helper loop` that keeps reading `until you get the exact message requested`
- Useful for `synchronization`, ex:
  - “device is ready”
  - “measurement finished”
  - “start next step”

## 2.4 json and close

```python
def send_json(self, obj):
    self.send(json.dumps(obj))

def receive_json(self):
    return json.loads(self.receive())

def close(self):
    self.sock.close()
```
- `send_json`: Serializes Python → JSON → sends as text message.
- `receive_json`: Reads one complete line → parses JSON → returns a dict.
- `close`: close the socket.

# 3. Example usage

### server.py
```python
from LabAuto.network import create_server, Connection

server = create_server("0.0.0.0", 5555)
conn, addr = Connection.accept(server)
msg = conn.receive()
conn.send("ok")
obj = conn.receive_json()
conn.close()
```

### client.py
```python
from LabAuto.network import Connection

conn = Connection.connect("127.0.0.1", 5555)
conn.send("hello")
reply = conn.receive()
# send JSON
conn.send_json({"cmd": "move", "steps": 100})
conn.close()
```