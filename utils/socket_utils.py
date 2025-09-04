import time

def send_cmd(sock, msg: str):
    """Send a message to the socket with newline termination."""
    sock.sendall((msg + "\n").encode())
    print(f"[SEND] {msg}")


def receive_msg(sock) -> str:
    """Receive one complete message (newline terminated)."""
    buf = ""
    while True:
        chunk = sock.recv(1024).decode()
        if not chunk:
            raise ConnectionError("Connection closed by peer")
        buf += chunk
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            line = line.strip()
            if line:
                print(f"[RECV] {line}")
                return line


def wait_for(sock, target: str, timeout: int = 30):
    """
    Wait until a specific message is received.
    """
    # start = time.time()
    while True:
        msg = receive_msg(sock)
        if msg == target:
            print(f"[WAIT] Got expected message: {target}")
            return msg
        # if time.time() - start > timeout:
        #     raise TimeoutError(f"Timeout waiting for {target}, last received: {msg}")
