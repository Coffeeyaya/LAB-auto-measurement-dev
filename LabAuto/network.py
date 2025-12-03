import socket
import json
import time

def create_server(host, port, backlog=1):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(backlog)
    print(f"Server listening on {host}:{port}...")
    return server_socket

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

    def wait_for(self, target: str):
        while True:
            msg = self.receive()  # could be str OR dict?
            if msg == target:  # handle old plain string
                return msg
            # if isinstance(msg, dict) and msg.get("cmd") == target:  # handle JSON
            #     return msg
            
    def send_json(self, obj):
        self.send(json.dumps(obj))

    def receive_json(self):
        return json.loads(self.receive())

    def close(self):
        self.sock.close()





# ------------------------------------------------------------
# ReconnectConnection — Auto-reconnecting wrapper
# ------------------------------------------------------------
class ReconnectConnection:
    """
    A wrapper around Connection that automatically reconnects on error.
    Call send_json() or receive_json() as usual.

    - If the connection breaks (WiFi lost, MacBook sleeps, server resets),
      it will retry until reconnected.
    """

    def __init__(self, host, port, retry_delay=2):
        self.host = host
        self.port = port
        self.retry_delay = retry_delay
        self.conn = None  # underlying Connection object

    def _ensure_connection(self):
        """
        Ensure that self.conn exists and is connected.
        If not, keep retrying until it succeeds.
        """
        while self.conn is None:
            try:
                print(f"[RECONNECT] Trying {self.host}:{self.port}...")
                self.conn = Connection.connect(self.host, self.port)
                print("[RECONNECT] Success!")
            except Exception as e:
                print(f"[WARN] Connect failed: {e}. Retrying in {self.retry_delay}s.")
                time.sleep(self.retry_delay)

    # -------------------------------
    # Send JSON with auto-reconnect
    # -------------------------------
    def send_json(self, obj):
        self._ensure_connection()
        try:
            self.conn.send_json(obj)
        except Exception:
            print("[WARN] Send failed. Dropping connection and retrying...")
            self.conn = None
            time.sleep(self.retry_delay)
            self.send_json(obj)

    # -------------------------------
    # Receive JSON with auto-reconnect
    # -------------------------------
    def receive_json(self):
        self._ensure_connection()
        try:
            return self.conn.receive_json()
        except Exception:
            print("[WARN] Receive failed. Dropping connection and retrying...")
            self.conn = None
            time.sleep(self.retry_delay)
            return None  # Caller can interpret None as missing data

    # -------------------------------
    # Graceful close
    # -------------------------------
    def close(self):
        if self.conn:
            self.conn.close()
        self.conn = None
        print("[CLOSE] ReconnectConnection closed.")

