import datetime
import subprocess
import os
from utils.socket_utils import send_cmd, receive_msg, create_server, accept_client

HOST = "0.0.0.0"
PORT = 5000  # command port

# ------------------- MUST CONFIGURE -------------------
DEFAULT_FOLDER = r"C:\Users\mmm11\OneDrive\桌面\yun-chen\code\auto\LAB-auto-measurement"
# ------------------------------------------------------

processes = {}        # {script_name: subprocess.Popen}
current_client = None

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
                send_cmd(conn, response)
                # CSV server should be started separately by the user if needed
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
        kill_all_scripts()
        conn.close()


# ------------------- Main -------------------
def main():
    if not DEFAULT_FOLDER:
        raise RuntimeError("DEFAULT_FOLDER must be set before running server.")

    server_socket = create_server(host=HOST, port=PORT)
    conn, addr = accept_client(server_socket)
    try:
        handle_client(conn, addr)
    finally:
        server_socket.close()


if __name__ == "__main__":
    main()
