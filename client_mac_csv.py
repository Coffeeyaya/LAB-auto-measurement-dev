import os
import socket
from utils.socket_utils import send_cmd, receive_msg

SERVER_IP = "192.168.50.101"  # Windows IV machine
PORT = 5002
SAVE_DIR = "/Users/tsaiyunchen/Desktop/lab/code/auto_measurement/raw_data/data"

os.makedirs(SAVE_DIR, exist_ok=True)

def receive_file(sock):
    header = receive_msg(sock)
    if not header.startswith("FILE "):
        print("[CSV CLIENT] Unexpected message:", header)
        return
    _, filename, filesize = header.split()
    filesize = int(filesize)
    
    filepath = os.path.join(SAVE_DIR, filename)

    send_cmd(sock, "READY")
    received = 0
    with open(filepath, "wb") as f:
        while received < filesize:
            chunk = sock.recv(min(4096, filesize - received))
            if not chunk:
                break
            f.write(chunk)
            received += len(chunk)

    done = receive_msg(sock)
    if done == "FILE_DONE":
        print(f"[CSV CLIENT] Received {filename} ({filesize} bytes)")
    else:
        print(f"[CSV CLIENT] File incomplete: {filename}")

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_IP, PORT))
    print(f"[CSV CLIENT] Connected to {SERVER_IP}:{PORT}")

    try:
        while True:
            receive_file(sock)
    except ConnectionError:
        print("[CSV CLIENT] Server disconnected")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
