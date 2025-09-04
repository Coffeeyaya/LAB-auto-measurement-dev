import datetime
import subprocess
import os
from utils.socket_utils import send_cmd, receive_msg, wait_for, create_server, accept_client


HOST = "0.0.0.0"
PORT = 5000

DEFAULT_FOLDER = r""  # adjust to your folder
processes = {}  # {script_name: subprocess.Popen object}
current_client = None  # store (ip, port) of active client

SERVER_SCRIPT_NAME = os.path.basename(__file__)  # the server's own filename
LOG_FILE = os.path.join(DEFAULT_FOLDER, "server_log.txt")

def log_event(event: str):
    """Append a timestamped event to the log file with client info."""
    global current_client
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    client_info = f"{current_client[0]}:{current_client[1]}" if current_client else "UNKNOWN"
    line = f"[{timestamp}] [{client_info}] {event}\n"
    with open(LOG_FILE, "a") as f:
        f.write(line)
    print(line.strip())  # also show on console

def run_script(script_name):
    global processes
    full_path = os.path.join(DEFAULT_FOLDER, script_name)
    
    if script_name == SERVER_SCRIPT_NAME:
        return "CANNOT_RUN_SERVER"
    
    if not os.path.exists(full_path):
        return "SCRIPT_NOT_FOUND"
    
    if script_name in processes and processes[script_name].poll() is None:
        return "SCRIPT_ALREADY_RUNNING"
    
    proc = subprocess.Popen(["python", full_path], shell=True)
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
            subprocess.call(f"taskkill /F /T /PID {proc.pid}", shell=True)
            del processes[script_name]
            log_event(f"KILL {script_name} (PID={proc.pid})")
            return "SCRIPT_KILLED"
        else:
            del processes[script_name]
            return "SCRIPT_ALREADY_FINISHED"
    return "SCRIPT_NOT_RUNNING"


def handle_client(conn, addr):
    global current_client
    current_client = addr
    log_event("CONNECTED")

    while True:
        try:
            cmd = receive_msg(conn)  # <- use socket_utils
        except ConnectionError:
            log_event("DISCONNECTED")
            print("Client disconnected.")
            break
        
        if cmd.startswith("RUN "):
            script_name = cmd[4:]
            response = run_script(script_name)
        
        elif cmd.startswith("KILL "):
            script_name = cmd[5:]
            response = kill_script(script_name)
        
        elif cmd.lower() == "quit":
            log_event("QUIT received")
            break
        
        else:
            response = "UNKNOWN_COMMAND"

        send_cmd(conn, response)  # <- use socket_utils
        
# ------------------- Main -------------------
def main():
    server_socket = create_server(host=HOST, port=PORT)  # wrapper
    conn, addr = accept_client(server_socket)            # wrapper
    try:
        handle_client(conn, addr)
    finally:
        conn.close()
        server_socket.close()

if __name__ == "__main__":
    main()
