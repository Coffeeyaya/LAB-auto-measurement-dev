import socket
import subprocess
import os

HOST = "0.0.0.0"
PORT = 5001

processes = {}  # {script_name: subprocess.Popen object}

def start_server(host=HOST, port=PORT):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Server listening on {host}:{port}...")
    conn, addr = server_socket.accept()
    print(f"Connected by {addr}")
    return server_socket, conn

DEFAULT_FOLDER = r"C:\Users\Win10User\combined"  # adjust to your folder
processes = {}

def run_script(script_name):
    global processes
    full_path = os.path.join(DEFAULT_FOLDER, script_name)
    if not os.path.exists(full_path):
        return "SCRIPT_NOT_FOUND"
    
    if script_name in processes and processes[script_name].poll() is None:
        return "SCRIPT_ALREADY_RUNNING"
    
    proc = subprocess.Popen(["python", full_path], shell=True)
    processes[script_name] = proc
    return "SCRIPT_STARTED"

def kill_script(script_name):
    global processes
    if script_name in processes and processes[script_name].poll() is None:
        processes[script_name].terminate()
        del processes[script_name]
        return "SCRIPT_KILLED"
    return "SCRIPT_NOT_RUNNING"

def handle_client(conn):
    while True:
        data = conn.recv(1024)
        if not data:
            break
        cmd = data.decode().strip()
        print(f"Received: {cmd}")

        if cmd.startswith("RUN "):
            script_name = cmd[4:]
            response = run_script(script_name)

        elif cmd.startswith("KILL "):
            script_name = cmd[5:]
            response = kill_script(script_name)

        elif cmd == "quit":
            break

        else:
            response = "UNKNOWN_COMMAND"

        conn.sendall((response + "\n").encode())

def main():
    server_socket, conn = start_server()
    try:
        handle_client(conn)
    finally:
        conn.close()
        server_socket.close()

if __name__ == "__main__":
    main()