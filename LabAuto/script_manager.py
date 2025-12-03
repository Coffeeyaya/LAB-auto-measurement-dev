import os
import subprocess
import sys
from LabAuto.network import create_server, Connection
import signal
import platform

import threading

processes = {}  # {script_name: subprocess.Popen}
SERVER_SCRIPT_NAME = None  # will be set when needed


def set_server_name(name: str):
    """Set the current server script name to prevent running/killing it."""
    global SERVER_SCRIPT_NAME
    SERVER_SCRIPT_NAME = name


def run_script(script_name: str):
    """
    Start a Python script if not already running.
    Assumes the script is in the same folder as the server.
    """
    global processes
    full_path = os.path.join(os.path.abspath('.'), script_name)

    if script_name == SERVER_SCRIPT_NAME:
        return {"status": "error", "message": "CANNOT_RUN_SERVER"}

    if not os.path.exists(full_path):
        return {"status": "error", "message": "SCRIPT_NOT_FOUND"}

    if script_name in processes and processes[script_name].poll() is None:
        return {"status": "error", "message": "SCRIPT_ALREADY_RUNNING"}
    
    python_executable = sys.executable
    # choose method based on OS
    system = platform.system()

    if system == "Darwin":  # macOS
        applescript = f'''
        tell application "iTerm"
            create window with default profile
            tell current window
                tell current session
                    write text "{python_executable} {full_path}"
                end tell
            end tell
        end tell
        '''
        proc = subprocess.Popen(
            ["osascript", "-e", applescript],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    # elif system == "Windows":
    #     proc = subprocess.Popen(
    #     ["conda", "run", "-n", "myenv", "python", full_path],
    #     creationflags=subprocess.CREATE_NEW_CONSOLE
    # )
    elif system == "Windows": 
        proc = subprocess.Popen( [python_executable, full_path], creationflags=subprocess.CREATE_NEW_CONSOLE )


    else:  # Linux
        proc = subprocess.Popen(
            ["gnome-terminal", "--", python_executable, full_path]
        )

    processes[script_name] = proc
    return {"status": "ok", "message": f"{script_name} started"}


def kill_script(script_name: str):
    """
    Kill a running Python script.
    """
    global processes

    if script_name == SERVER_SCRIPT_NAME:
        return {"status": "error", "message": "CANNOT_KILL_SERVER"}

    if script_name in processes:
        proc = processes[script_name]
        if proc.poll() is None:  # still running
            if platform.system() == "Windows":
                subprocess.call(["taskkill", "/F", "/T", "/PID", str(proc.pid)])
            else:  # macOS / Linux
                os.kill(proc.pid, signal.SIGTERM)
        del processes[script_name]
        return {"status": "ok", "message": f"{script_name} killed"}

    return {"status": "error", "message": "SCRIPT_NOT_RUNNING"}


def kill_all_scripts():
    """Kill all tracked scripts."""
    for name in list(processes.keys()):
        kill_script(name)
    return {"status": "ok", "message": "ALL_STOPPED"}

def handle_client(conn: Connection):
    """
    Handle a single client connection using JSON commands.
    Works with run_script, kill_script, and kill_all_scripts from this module.
    default_folder: the folder where the "script to be run" resides in
    """
    try:
        while True:
            try:
                data = conn.receive_json()  # Receive JSON command
            except ConnectionError:
                break

            cmd_type = data.get("cmd")
            target = data.get("target", "")

            if cmd_type == "RUN":
                response = run_script(target)
            elif cmd_type == "KILL":
                response = kill_script(target)
            elif cmd_type == "QUIT":
                response = kill_all_scripts()
                conn.send_json(response)
                return True
            else:
                response = {"status": "error", "message": "Invalid command"}

            conn.send_json(response)
    finally:
        kill_all_scripts()
        conn.close()


def run_server(host, port, csv_handler=None):

    server_socket = create_server(host, port)
    try:
        while True:
            conn, addr = Connection.accept(server_socket)

            if csv_handler is not None:
                csv_handler(conn)
            else:
                # main script manager client loop
                should_quit = handle_client(conn)
                if should_quit:
                    print("QUIT received. Server shutting down.")
                    break
    finally:
        server_socket.close()


def run_server_threading(host, port, csv_handler=None):
    """Threaded TCP server that accepts multiple independent clients."""
    server_socket = create_server(host, port)

    print(f"[SERVER] Listening on {host}:{port}")

    def client_thread(conn, addr):
        print(f"[THREAD] Started for {addr}")

        try:
            if csv_handler is not None:
                csv_handler(conn)
            else:
                should_quit = handle_client(conn)
                if should_quit:
                    print("[SERVER] QUIT received — shutting down server.")
                    os._exit(0)   # Hard shutdown for safety; change if needed.

        except ConnectionError:
            print(f"[SERVER] Client {addr} disconnected.")

        except Exception as e:
            print(f"[SERVER] Exception in {addr}: {e}")

        finally:
            conn.close()
            print(f"[THREAD] Closed connection for {addr}")

    try:
        while True:
            conn, addr = Connection.accept(server_socket)
            print(f"[SERVER] New client: {addr}")

            t = threading.Thread(
                target=client_thread,
                args=(conn, addr),
                daemon=True
            )
            t.start()

    finally:
        server_socket.close()
        print("[SERVER] Socket closed.")
