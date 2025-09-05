from utils.socket_utils import send_cmd, receive_msg, wait_for
import socket
import os
import threading

# SERVER_IP = "192.168.137.1"
SERVER_IP = "192.168.151.20" # for server_laser(Windows 7)
# SERVER_IP = "" # for server_iv (Windows 10)
PORT = 5000

SAVE_DIR = "data"

def connect_to_server(ip=SERVER_IP, port=PORT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    print(f"Connected to {ip}:{port}")
    return sock
def receive_file(sock, save_dir=SAVE_DIR):
    """Receive a single CSV file from the server."""
    os.makedirs(save_dir, exist_ok=True)

    header = receive_msg(sock)
    if not header.startswith("FILE "):
        print("Unexpected message:", header)
        return

    _, filename, filesize = header.split()
    filesize = int(filesize)
    filepath = os.path.join(save_dir, filename)

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
        print(f"[FILE RECEIVED] {filepath} ({filesize} bytes)")
    else:
        print(f"[FILE INCOMPLETE] {filepath}")

def file_listener(sock, stop_event):
    """Thread function: continuously receive CSV files until stop_event is set."""
    while not stop_event.is_set():
        try:
            # Peek at the next message without blocking
            sock.settimeout(0.5)
            try:
                msg = receive_msg(sock)
            except socket.timeout:
                continue  # no message yet
            finally:
                sock.settimeout(None)

            if msg.startswith("FILE "):
                # Put back the header and receive the file
                # (already handled by receive_file)
                receive_file(sock)
            else:
                print("[SERVER MESSAGE]", msg)
        except ConnectionError:
            print("[DISCONNECTED] Server closed connection")
            break

def main():
    sock = connect_to_server()
    stop_event = threading.Event()
    listener_thread = threading.Thread(target=file_listener, args=(sock, stop_event), daemon=True)
    listener_thread.start()

    try:
        while True:
            cmd = input("Enter command (RUN <script>/KILL <script>/quit): ").strip()
            if not cmd:
                continue
            send_cmd(sock, cmd)

            if cmd.lower() == "quit":
                stop_event.set()
                break

            # Wait for server response for commands other than file
            if not cmd.lower().startswith("run "):
                response = receive_msg(sock)
                print("[RESPONSE]", response)
    finally:
        sock.close()
        stop_event.set()
        listener_thread.join()
        print("Connection closed.")

if __name__ == "__main__":
    main()