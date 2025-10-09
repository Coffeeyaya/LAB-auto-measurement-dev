import os
import time
from LabAuto.network import Connection
from LabAuto.script_manager import run_server, set_server_name

set_server_name(os.path.basename(__file__))

HOST = '0.0.0.0'
PORT = 5002

CSV_FOLDER = r"C:\Users\mmm11\OneDrive\桌面\yun-chen\code\auto\send_data"
os.makedirs(CSV_FOLDER, exist_ok=True)

def send_file(conn: Connection, filepath):
    """Send a single CSV file in chunks."""
    if not os.path.exists(filepath):
        conn.send_json({"status": "error", "message": f"FILE_NOT_FOUND {filepath}"})
        return

    filesize = os.path.getsize(filepath)
    filename = os.path.basename(filepath)

    # Send header
    conn.send_json({"cmd": "FILE", "filename": filename, "size": filesize})
    ack = conn.receive_json()
    if ack.get("status") != "READY":
        return

    # Send file contents
    with open(filepath, "rb") as f:
        while chunk := f.read(4096):
            conn.sock.sendall(chunk)

    conn.send_json({"cmd": "FILE_DONE"})
    print(f"[CSV SERVER] Sent {filename} ({filesize} bytes)")

def watch_and_send_csvs(conn: Connection, folder: str):
    """Continuously watch folder for new CSV files and send them."""
    known_files = set()
    try:
        while True:
            current_files = {f for f in os.listdir(folder) if f.endswith(".csv")}
            new_files = sorted(current_files - known_files)
            for new_file in new_files:
                filepath = os.path.join(folder, new_file)
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    send_file(conn, filepath)
                    time.sleep(1)
                    known_files.add(new_file)
            time.sleep(1)
    except ConnectionError:
        print("[CSV SERVER] Client disconnected")
    except Exception as e:
        print(f"[CSV SERVER] Watcher error: {e}")

# ------------------- Extra Client Handler -------------------
def csv_client_handler(conn: Connection):
    try:
        watch_and_send_csvs(conn, CSV_FOLDER)
    except ConnectionError:
        print("[CSV SERVER] Client disconnected")
    finally:
        conn.sock.close()  # close here, not in run_server finally


# ------------------- Main -------------------
if __name__ == "__main__":
    run_server(host=HOST, port=PORT, csv_handler=csv_client_handler)

    