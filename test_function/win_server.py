import socket
import subprocess
import os
from utils.socket_utils import send_cmd, receive_msg, wait_for, create_server, accept_client

HOST = "0.0.0.0"
PORT = 5001

DEFAULT_FOLDER = r"C:\Users\ASUS\Desktop\test\LAB-auto-measurement"  # adjust to your folder
processes = {}  # {script_name: subprocess.Popen object}

# ------------------- Script Management -------------------
def run_script(script_name):
    global processes
    full_path = os.path.join(DEFAULT_FOLDER, script_name)
    print(full_path)
    if not os.path.exists(full_path):
        return "SCRIPT_NOT_FOUND"
    
    if script_name in processes and processes[script_name].poll() is None:
        return "SCRIPT_ALREADY_RUNNING"
    
    proc = subprocess.Popen(["python", full_path], shell=True)
    processes[script_name] = proc
    return "SCRIPT_STARTED"

def kill_script(script_name):
    global processes
    if script_name in processes:
        proc = processes[script_name]
        if proc.poll() is None:  # still running
            subprocess.call(f"taskkill /F /T /PID {proc.pid}", shell=True)
            del processes[script_name]
            return "SCRIPT_KILLED"
        else:
            del processes[script_name]
            return "SCRIPT_ALREADY_FINISHED"
    return "SCRIPT_NOT_RUNNING"

def handle_client(conn):
    while True:
        try:
            cmd = receive_msg(conn)  # <- use socket_utils
        except ConnectionError:
            print("Client disconnected.")
            break
        
        if cmd.startswith("RUN "):
            script_name = cmd[4:]
            response = run_script(script_name)
        
        elif cmd.startswith("KILL "):
            script_name = cmd[5:]
            response = kill_script(script_name)
        
        elif cmd.lower() == "quit":
            break
        
        else:
            response = "UNKNOWN_COMMAND"

        send_cmd(conn, response)  # <- use socket_utils
        
# ------------------- Main -------------------
def main():
    server_socket = create_server(host=HOST, port=PORT)  # wrapper
    conn, addr = accept_client(server_socket)            # wrapper
    try:
        handle_client(conn)
    finally:
        conn.close()
        server_socket.close()

if __name__ == "__main__":
    main()
