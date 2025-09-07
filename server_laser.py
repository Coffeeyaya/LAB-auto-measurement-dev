import datetime
import subprocess
import os
from utils.socket_utils import send_cmd, receive_msg, create_server, accept_client

HOST = "0.0.0.0"
PORT = 5000

DEFAULT_FOLDER = r"C:\Users\8300Elite\Desktop\auto\LAB-auto-measurement"  # must be set
processes = {}        # {script_name: subprocess.Popen}
current_client = None
watcher_threads = []

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
        return "CANNOT_RUN_SERVER"

    if not os.path.exists(full_path):
        return "SCRIPT_NOT_FOUND"

    if script_name in processes and processes[script_name].poll() is None:
        return "SCRIPT_ALREADY_RUNNING"

    proc = subprocess.Popen(["python", full_path])
    processes[script_name] = proc
    log_event(f"RUN {script_name} (PID={proc.pid})")
    return "SCRIPT_STARTED"


def kill_script(script_name):
    global processes

    if script_name == SERVER_SCRIPT_NAME:
        return "CANNOT_KILL_SERVER"

    if script_name in processes:
        proc = processes[script_name]
        if proc.poll() is None:  # still running
            subprocess.call(["taskkill", "/F", "/T", "/PID", str(proc.pid)], shell=True)
            log_event(f"KILL {script_name} (PID={proc.pid})")
        del processes[script_name]
        return "SCRIPT_KILLED"
    return "SCRIPT_NOT_RUNNING"


def kill_all_scripts():
    for name in list(processes.keys()):
        kill_script(name)
    return "ALL_STOPPED"


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
                response = run_script(script_name)

            elif cmd.startswith("KILL "):
                script_name = cmd[5:]
                response = kill_script(script_name)

            elif cmd == "STOP_ALL":
                response = kill_all_scripts()

            elif cmd.lower() == "quit":
                response = "QUIT"
                log_event("QUIT received")
                break

            else:
                response = "UNKNOWN_COMMAND"

            send_cmd(conn, response)

    finally:
        kill_all_scripts()  # cleanup
        conn.close()


# ------------------- Main -------------------
def main():
    if not DEFAULT_FOLDER:
        raise RuntimeError("DEFAULT_FOLDER must be set before running server.")

    server_socket = create_server(host=HOST, port=PORT)
    try:
        while True:
            conn, addr = accept_client(server_socket)
            try:
                handle_client(conn, addr)
            finally:
                conn.close()
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()  # set True in server_iv.py
