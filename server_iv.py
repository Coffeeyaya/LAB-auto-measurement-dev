import subprocess
import os
from utils.socket_utils import send_cmd, receive_msg, create_server, accept_client

HOST = "0.0.0.0"
PORT = 5000  # command port

# ------------------- MUST CONFIGURE -------------------
DEFAULT_FOLDER = r"C:\Users\mmm11\OneDrive\桌面\yun-chen\code\auto\LAB-auto-measurement"
# ------------------------------------------------------
processes = {}        # {script_name: subprocess.Popen}

SERVER_SCRIPT_NAME = os.path.basename(__file__)

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
    return "SCRIPT_STARTED"


def kill_script(script_name):
    global processes

    if script_name == SERVER_SCRIPT_NAME:
        return "CANNOT_KILL_SERVER"

    if script_name in processes:
        proc = processes[script_name]
        if proc.poll() is None:  # still running
            subprocess.call(["taskkill", "/F", "/T", "/PID", str(proc.pid)], shell=True)
    
        del processes[script_name]
        return "SCRIPT_KILLED"
    return "SCRIPT_NOT_RUNNING"


def kill_all_scripts():
    for name in list(processes.keys()):
        kill_script(name)
    return "ALL_STOPPED"


# ------------------- Client Handling -------------------
def handle_client(conn):
    try:
        menu = (
            "\n=== Command Menu ===\n"
            "1. RUN iv_run.py\n"
            "2. KILL iv_run.py\n"
            "3. RUN server_iv_csv.py\n"
            "4. KILL server_iv_csv.py\n"
            "5. STOP_ALL\n"
            "Enter choice (1-5):"
        )
        send_cmd(conn, menu)

        while True:
            try:
                choice = receive_msg(conn)
            except ConnectionError:
                break
            if choice == "1":
                response = run_script("iv_run.py")
            elif choice == "2":
                response = kill_script("iv_run.py")
            elif choice == "3":
                response = run_script("server_iv_csv.py")
            elif choice == "4":
                response = kill_script("server_iv_csv.py")
            elif choice == "5":
                response = kill_all_scripts()
                break
            else:
                response = "invalid choice"
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
                handle_client(conn)
            finally:
                conn.close()
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()
