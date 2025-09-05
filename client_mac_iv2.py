# client_mac_iv.py
from utils.socket_utils import send_cmd, receive_msg
import socket
import os
import threading

SERVER_IP = "192.168.50.101"  # Replace with server_iv IP
PORT = 5000
SAVE_DIR = "data_iv"

def connect_to_server(ip=SERVER_IP, port=PORT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    print(f"Connected to IV server at {ip}:{port}")
    return sock

def receive_file(sock, save_dir=SAVE_DIR):
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
        print(f"[IV FILE RECEIVED] {filepath} ({filesize} bytes)")
    else:
        print(f"[FILE INCOMPLETE] {filepath}")

def file_listener(sock, stop_event):
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
                receive_file(sock)
            else:
                print("[IV SERVER MESSAGE]", msg)
        except ConnectionError:
            print("[IV DISCONNECTED] Server closed connection")
            break

def main():
    sock = connect_to_server()
    stop_event = threading.Event()
    listener_thread = threading.Thread(target=file_listener, args=(sock, stop_event), daemon=True)
    listener_thread.start()

    try:
        while True:
            cmd = input("IV Command (RUN/KILL/quit): ").strip()
            if not cmd:
                continue
            send_cmd(sock, cmd)
            if cmd.lower() == "quit":
                stop_event.set()
                break
            if not cmd.lower().startswith("run "):
                response = receive_msg(sock)
                print("[IV RESPONSE]", response)
    finally:
        sock.close()
        stop_event.set()
        listener_thread.join()
        print("IV client connection closed.")

if __name__ == "__main__":
    main()
