# client_mac_iv.py (modified with single reader + queue)
from utils.socket_utils import send_cmd, receive_msg
import socket
import os
import threading
import queue
import time

SERVER_IP = "192.168.50.101"  # Replace with server_iv IP
PORT = 5000
SAVE_DIR = "data_iv"

# Queue for messages from the server
msg_queue = queue.Queue()

def connect_to_server(ip=SERVER_IP, port=PORT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    print(f"Connected to IV server at {ip}:{port}")
    return sock

def receive_file(sock, save_dir=SAVE_DIR, header=None):
    os.makedirs(save_dir, exist_ok=True)
    if not header:
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
        print(f"[IV FILE RECEIVED] {filepath} ({filesize} bytes)")
    else:
        print(f"[FILE INCOMPLETE] {filepath}")

def socket_reader(sock, stop_event):
    """Single thread that reads all messages from the socket."""
    while not stop_event.is_set():
        try:
            sock.settimeout(0.5)
            try:
                msg = receive_msg(sock)
            except socket.timeout:
                continue
            finally:
                sock.settimeout(None)

            if msg.startswith("FILE "):
                # CSV file transfer handled immediately
                receive_file(sock, header=msg)
            else:
                # Put other messages into the queue for main thread
                msg_queue.put(msg)
        except ConnectionError:
            print("[IV DISCONNECTED] Server closed connection")
            break

def main():
    sock = connect_to_server()
    stop_event = threading.Event()
    reader_thread = threading.Thread(target=socket_reader, args=(sock, stop_event), daemon=True)
    reader_thread.start()

    try:
        while True:
            cmd = input("IV Command (RUN/KILL/quit): ").strip()
            if not cmd:
                continue
            send_cmd(sock, cmd)

            if cmd.lower() == "quit":
                stop_event.set()
                break

            # Wait for a response (for commands other than RUN)
            if not cmd.lower().startswith("run "):
                # Wait for message from queue
                try:
                    response = msg_queue.get(timeout=10)
                    print("[IV RESPONSE]", response)
                except queue.Empty:
                    print("[IV RESPONSE] No response received.")
            else:
                # For RUN commands, optionally wait for SCRIPT_STARTED
                try:
                    response = msg_queue.get(timeout=10)
                    print("[IV RESPONSE]", response)
                except queue.Empty:
                    print("[IV RESPONSE] No response received for RUN command.")
    finally:
        sock.close()
        stop_event.set()
        reader_thread.join()
        print("IV client connection closed.")

if __name__ == "__main__":
    main()
