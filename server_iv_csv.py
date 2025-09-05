import os
import time
from utils.socket_utils import send_cmd, receive_msg, create_server, accept_client

CSV_FOLDER = r"C:\Users\mmm11\OneDrive\桌面\yun-chen\code\auto\LAB-auto-measurement\data"
os.makedirs(CSV_FOLDER, exist_ok=True)

HOST = "0.0.0.0"
PORT = 5002  # separate port for CSV transfer


def send_file(conn, filepath):
    """Send a single CSV file in chunks."""
    if not os.path.exists(filepath):
        send_cmd(conn, f"FILE_NOT_FOUND {filepath}")
        return

    filesize = os.path.getsize(filepath)
    filename = os.path.basename(filepath)

    # Send header
    send_cmd(conn, f"FILE {filename} {filesize}")
    ack = receive_msg(conn)
    if ack != "READY":
        return

    # Send file contents
    with open(filepath, "rb") as f:
        while chunk := f.read(4096):
            conn.sendall(chunk)

    send_cmd(conn, "FILE_DONE")
    print(f"[CSV SERVER] Sent {filename} ({filesize} bytes)")


def watch_and_send_csvs(conn, folder):
    """Continuously watch folder for new CSV files and send them."""
    known_files = set()
    while True:
        try:
            current_files = {f for f in os.listdir(folder) if f.endswith(".csv")}
            new_files = sorted(current_files - known_files)
            for new_file in new_files:
                filepath = os.path.join(folder, new_file)
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    send_file(conn, filepath)
                    known_files.add(new_file)
            time.sleep(1)
        except Exception as e:
            print(f"[CSV SERVER] Watcher error: {e}")
            break


def handle_client(conn, addr):
    print(f"[CSV SERVER] Connected by {addr}")
    try:
        watch_and_send_csvs(conn, CSV_FOLDER)
    except ConnectionError:
        print(f"[CSV SERVER] Client {addr} disconnected")
    finally:
        conn.close()


def main():
    server_socket = create_server(HOST, PORT)
    conn, addr = accept_client(server_socket)
    try:
        handle_client(conn, addr)
    finally:
        server_socket.close()


if __name__ == "__main__":
    main()
