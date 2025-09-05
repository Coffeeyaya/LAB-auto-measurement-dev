import os
import socket
from utils.socket_utils import send_cmd, receive_msg

SERVER_IP = "192.168.137.1"  # Windows server IP
PORT = 5002
CHUNK_SIZE = 4096
SAVE_FOLDER = r"data"  # where to save CSV

def receive_file(sock):
    # Receive header
    header = receive_msg(sock)
    if not header.startswith("FILE"):
        print("Invalid header:", header)
        return

    _, filename, filesize = header.split()
    filesize = int(filesize)
    send_cmd(sock, "READY")  # tell server to start sending

    filepath = os.path.join(SAVE_FOLDER, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    received = 0
    with open(filepath, "wb") as f:
        while received < filesize:
            chunk = sock.recv(min(CHUNK_SIZE, filesize - received))
            if not chunk:
                break
            f.write(chunk)
            received += len(chunk)

    done_msg = receive_msg(sock)
    if done_msg == "DONE":
        print(f"Received file {filename} successfully.")

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_IP, PORT))
    print(f"Connected to {SERVER_IP}:{PORT}")

    receive_file(sock)

    sock.close()

if __name__ == "__main__":
    main()
