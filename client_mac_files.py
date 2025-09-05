import socket, os

SAVE_DIR = "data_iv_csv"
SERVER_IP = "192.168.50.101"
PORT = 5001

os.makedirs(SAVE_DIR, exist_ok=True)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((SERVER_IP, PORT))
print(f"Connected to CSV server at {SERVER_IP}:{PORT}")

def receive_file():
    header = b""
    while b"\n" not in header:
        header += sock.recv(1024)
    header = header.decode().strip()
    if not header.startswith("FILE "):
        print("Unexpected message:", header)
        return
    _, filename, filesize = header.split()
    filesize = int(filesize)
    sock.sendall(b"READY\n")
    path = os.path.join(SAVE_DIR, filename)
    received = 0
    with open(path, "wb") as f:
        while received < filesize:
            chunk = sock.recv(min(4096, filesize - received))
            if not chunk:
                break
            f.write(chunk)
            received += len(chunk)
    done = sock.recv(1024).decode().strip()
    if done == "FILE_DONE":
        print(f"Received {filename}")

while True:
    receive_file()
