import datetime
import subprocess
import os
import time
import threading
from utils.socket_utils import send_cmd, receive_msg, create_server, accept_client

HOST = "0.0.0.0"
PORT = 5000

# ------------------- MUST CONFIGURE -------------------
DEFAULT_FOLDER = r"C:\Users\mmm11\OneDrive\桌面\yun-chen\code\auto\LAB-auto-measurement"
CSV_FOLDER = r"C:\Users\mmm11\OneDrive\桌面\yun-chen\code\auto\LAB-auto-measurement\data"
# ------------------------------------------------------

processes = {}        # {script_name: subprocess.Popen}
current_client = None
watcher_threads = []  # [(thread, stop_event)]

SERVER_SCRIPT_NAME = os.path.basename(__file__)
LOG_FILE = os.path.join(DEFAULT_FOLDER, "server_log.txt")


# ------------------- Utilities -------------------
def log_event(event: str):
    global current_client
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    client_info = f"{current_client[0]}:{current_client[1]}" if current_client else "UNKNOWN"
    line = f"[{timestamp}] [{client_info}] {event}\n"
    with open(LOG_FILE, "a") as f:
        f.write(line)
    print(line.strip())


def run_script(script_name):
    global processes
    full_path = os.path.join(DEFAULT_FOLDER, script_name)

    if script_name == SERVER_SCRIPT_NAME:
        return None, "CANNOT_RUN_SERVER"

    if not os.path.exists(full_path):
        return None, "SCRIPT_NOT_FOUND"

    if script_name in processes and processes[script_name].poll() is None:
        return processes[script_name], "SCRIPT_ALREADY_RUNNING"

    proc = subprocess.Popen(["python", full_path])
    processes[script_name] = proc
    log_event(f"RUN {script_name} (PID={proc.pid})")
    return proc, "SCRIPT_STARTED"


def kill_script(script_name):
    global processes

    if script_name == SERVER_SCRIPT_NAME:
        return "CANNOT_KILL_SERVER"

    if script_name in processes:
        proc = processes[script_name]
        if proc.poll() is None:
            subprocess.call(["taskkill", "/F", "/T", "/PID", str(proc.pid)], shell=True)
            log_event(f"KILL {script_name} (PID={proc.pid})")
        del processes[script_name]
        return "SCRIPT_KILLED"
    return "SCRIPT_NOT_RUNNING"


def kill_all_scripts():
    for name in list(processes.keys()):
        kill_script(name)
    return "ALL_STOPPED"


def send_file(conn, filepath):
    """Send one file to the client in chunks."""
    if not os.path.exists(filepath):
        send_cmd(conn, f"FILE_NOT_FOUND {filepath}")
        return

    filesize = os.path.getsize(filepath)
    filename = os.path.basename(filepath)

    # Send file header first
    send_cmd(conn, f"FILE {filename} {filesize}")
    ack = receive_msg(conn)
    if ack != "READY":
        return

    # Send the actual file
    with open(filepath, "rb") as f:
        while chunk := f.read(4096):
            conn.sendall(chunk)

    send_cmd(conn, "FILE_DONE")
    log_event(f"SEND_FILE {filename} ({filesize} bytes)")


def watch_and_send_csvs(conn, folder, known_files, stop_event):
    """Continuously watch folder for new CSV files and send them sequentially."""
    while not stop_event.is_set():
        try:
            current_files = {f for f in os.listdir(folder) if f.endswith(".csv")}
            new_files = current_files - known_files
            for new_file in sorted(new_files):
                filepath = os.path.join(folder, new_file)
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    send_file(conn, filepath)
                    known_files.add(new_file)
            time.sleep(1)
        except Exception as e:
            log_event(f"Watcher error: {e}")
            break


# ------------------- Client Handling -------------------
def handle_client(conn, addr):
    global current_client
    current_client = addr
    log_event("CONNECTED")

    try:
        while True:
            try:
                cmd = receive_msg(conn)
            except ConnectionError:
                log_event("DISCONNECTED")
                break

            if cmd.startswith("RUN "):
                script_name = cmd[4:]
                proc, response = run_script(script_name)

                # Send response BEFORE starting CSV watcher
                send_cmd(conn, response)

                if proc and response == "SCRIPT_STARTED":
                    known_files = set()
                    stop_event = threading.Event()
                    t = threading.Thread(
                        target=watch_and_send_csvs,
                        args=(conn, CSV_FOLDER, known_files, stop_event),
                        daemon=True
                    )
                    t.start()
                    watcher_threads.append((t, stop_event))

                continue

            elif cmd.startswith("KILL "):
                script_name = cmd[5:]
                response = kill_script(script_name)
                send_cmd(conn, response)

            elif cmd == "STOP_ALL":
                response = kill_all_scripts()
                send_cmd(conn, response)

            elif cmd.lower() == "quit":
                response = "QUIT"
                send_cmd(conn, response)
                log_event("QUIT received")
                break

            else:
                response = "UNKNOWN_COMMAND"
                send_cmd(conn, response)

    finally:
        # Stop all watchers
        for t, stop_event in watcher_threads:
            stop_event.set()
            t.join(timeout=2)

        kill_all_scripts()
        conn.close()


# ------------------- Main -------------------
def main():
    if not DEFAULT_FOLDER or not CSV_FOLDER:
        raise RuntimeError("DEFAULT_FOLDER and CSV_FOLDER must be set before running server.")

    server_socket = create_server(host=HOST, port=PORT)
    conn, addr = accept_client(server_socket)
    try:
        handle_client(conn, addr)
    finally:
        server_socket.close()


if __name__ == "__main__":
    main()
