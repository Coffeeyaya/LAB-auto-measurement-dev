"""
laser_control.py

Stateful laser control server.

- Listens on port 5001 (same as before)
- Accepts one client at a time, but will accept a new client after disconnection
- Long-running tasks run in a worker thread
- SEND "STOP" to interrupt the current running task
- Uses Connection (server-side) from LabAuto.network
"""

import threading
import time
import os
import pandas as pd

from LabAuto.laser import (
    init_AOTF,
    get_coord,
    change_power_function,
    move_and_click,
    change_lambda_function,
)
from LabAuto.network import create_server, Connection

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
HOST = "0.0.0.0"
PORT = 5001  # keep same as before unless you change client code

# default safety values (override in code if you need)
DEFAULT_CHANNEL = 6
DEFAULT_POWER = "17"

# ------------------------------------------------------------------
# Shared state and synchronization
# ------------------------------------------------------------------
laser_state_lock = threading.Lock()
laser_state = "IDLE"       # IDLE, BUSY, DONE, INTERRUPTED, etc.

worker_lock = threading.Lock()
worker_thread = None

# Use a flag to request the worker to stop
stop_flag_lock = threading.Lock()
stop_flag = False

# Keep current connection object reference to allow status updates.
# This is set per-client connection handler; worker will get a conn passed in.
# Do NOT use this globally for send; always pass the conn arg to worker functions.


# ------------------------------------------------------------------
# Utilities for state management
# ------------------------------------------------------------------
def set_laser_state(state: str):
    global laser_state
    with laser_state_lock:
        laser_state = state
    print(f"[LASER STATE] {state}")


def get_laser_state():
    with laser_state_lock:
        return laser_state


def set_stop_flag(value: bool):
    global stop_flag
    with stop_flag_lock:
        stop_flag = value


def get_stop_flag() -> bool:
    with stop_flag_lock:
        return stop_flag


def worker_is_busy() -> bool:
    with worker_lock:
        return worker_thread is not None and worker_thread.is_alive()


def start_task_thread(target, *args, **kwargs):
    """
    Start a worker thread to run `target(*args, **kwargs)`.
    If a worker is already running, returns False.
    """
    global worker_thread
    with worker_lock:
        if worker_thread is not None and worker_thread.is_alive():
            return False
        # reset stop flag before starting
        set_stop_flag(False)
        worker_thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        worker_thread.start()
        return True


def stop_current_task():
    """
    Request the current worker to stop. Worker functions must check get_stop_flag().
    """
    if worker_is_busy():
        print("[CONTROL] Stop requested for current task.")
        set_stop_flag(True)
        return True
    return False


def safe_send(conn: Connection, msg: str):
    """
    Send safely; capture exceptions so the worker doesn't crash the process if client disconnects.
    """
    try:
        conn.send(msg)
    except Exception as e:
        print(f"[WARN] Failed to send to client: {e}")


# ------------------------------------------------------------------
# Task implementations (must periodically check get_stop_flag())
# ------------------------------------------------------------------
def time_dependent_wavelength(conn: Connection, grid, channel_arr, wavelength_arr, power_percentage_arr, on_time=10, off_time=10):
    """
    Sweep through wavelength/power arrays. Worker should be interruptible via STOP.
    """
    set_laser_state("wavelength")
    safe_send(conn, "wavelength")

    try:
        for i in range(len(channel_arr)):
            if get_stop_flag():
                set_laser_state("INTERRUPTED")
                safe_send(conn, "INTERRUPTED")
                return

            channel = int(channel_arr[i])
            wavelength = str(wavelength_arr[i])
            power = str(power_percentage_arr[i])

            print(f"[TASK] wavelength step: channel={channel}, lambda={wavelength}, power={power}")

            on_coord = get_coord(grid, channel, "on")
            change_lambda_function(grid, channel, wavelength)
            change_power_function(grid, channel, power)

            # turn on
            move_and_click(on_coord)
            # allow smaller sleep slices to be interruptible
            for _ in range(int(max(1, on_time))):
                if get_stop_flag(): break
                time.sleep(1)

            # turn off
            move_and_click(on_coord)
            for _ in range(int(max(1, off_time))):
                if get_stop_flag(): break
                time.sleep(1)

        if get_stop_flag():
            set_laser_state("INTERRUPTED")
            safe_send(conn, "INTERRUPTED")
        else:
            set_laser_state("DONE")
            safe_send(conn, "DONE")
    except Exception as e:
        print(f"[ERROR] Exception in time_dependent_wavelength: {e}")
        set_laser_state("ERROR")
        safe_send(conn, "ERROR")


def time_dependent_power(conn: Connection, grid, channel, power_values, on_time=10, off_time=60):
    set_laser_state("power")
    safe_send(conn, "power")
    try:
        for power in power_values:
            if get_stop_flag():
                set_laser_state("INTERRUPTED")
                safe_send(conn, "INTERRUPTED")
                return

            on_coord = get_coord(grid, channel, "on")
            change_power_function(grid, channel, power)
            move_and_click(on_coord)

            for _ in range(int(max(1, on_time))):
                if get_stop_flag(): break
                time.sleep(1)

            move_and_click(on_coord)
            for _ in range(int(max(1, off_time))):
                if get_stop_flag(): break
                time.sleep(1)

        if get_stop_flag():
            set_laser_state("INTERRUPTED")
            safe_send(conn, "INTERRUPTED")
        else:
            set_laser_state("DONE")
            safe_send(conn, "DONE")
    except Exception as e:
        print(f"[ERROR] Exception in time_dependent_power: {e}")
        set_laser_state("ERROR")
        safe_send(conn, "ERROR")


def single_on_off(conn: Connection, grid, channel, wavelength, power, on_time=3, off_time=3):
    set_laser_state("1_on_off")
    safe_send(conn, "1_on_off")
    try:
        if get_stop_flag():
            set_laser_state("INTERRUPTED")
            safe_send(conn, "INTERRUPTED")
            return

        on_coord = get_coord(grid, channel, "on")
        time.sleep(0.5)

        change_lambda_function(grid, channel, wavelength)
        time.sleep(0.5)

        change_power_function(grid, channel, power)
        time.sleep(0.5)

        # turn on
        move_and_click(on_coord)
        for _ in range(int(max(1, on_time))):
            if get_stop_flag(): break
            time.sleep(1)

        # turn off
        move_and_click(on_coord)
        for _ in range(int(max(1, off_time))):
            if get_stop_flag(): break
            time.sleep(1)

        if get_stop_flag():
            set_laser_state("INTERRUPTED")
            safe_send(conn, "INTERRUPTED")
        else:
            set_laser_state("DONE")
            safe_send(conn, "DONE")
    except Exception as e:
        print(f"[ERROR] Exception in single_on_off: {e}")
        set_laser_state("ERROR")
        safe_send(conn, "ERROR")


def multi_on_off(conn: Connection, grid, channel, power, on_time=1, off_time=1, peaks_num=20):
    set_laser_state("multi_on_off")
    safe_send(conn, "multi_on_off")
    try:
        on_coord = get_coord(grid, channel, "on")
        time.sleep(0.5)

        change_power_function(grid, channel, power)
        time.sleep(0.5)

        for i in range(peaks_num):
            if get_stop_flag():
                set_laser_state("INTERRUPTED")
                safe_send(conn, "INTERRUPTED")
                return

            move_and_click(on_coord)
            for _ in range(int(max(1, on_time))):
                if get_stop_flag(): break
                time.sleep(1)

            move_and_click(on_coord)
            for _ in range(int(max(1, off_time))):
                if get_stop_flag(): break
                time.sleep(1)

        if get_stop_flag():
            set_laser_state("INTERRUPTED")
            safe_send(conn, "INTERRUPTED")
        else:
            set_laser_state("DONE")
            safe_send(conn, "DONE")
    except Exception as e:
        print(f"[ERROR] Exception in multi_on_off: {e}")
        set_laser_state("ERROR")
        safe_send(conn, "ERROR")


# ------------------------------------------------------------------
# CSV loader (same as before)
# ------------------------------------------------------------------
def load_wavelength_csv(path="wavelength_power.csv"):
    channel_arr = []
    wavelength_arr = []
    power_percentage_arr = []
    try:
        df = pd.read_csv(path)
        # Accept columns named exactly 'wavelength_arr', 'power_percentage_arr', 'channel'
        for index, row in df.iterrows():
            # ensure values are strings (client may send string wavelengths)
            wavelength = str(row.get("wavelength_arr", "")).strip()
            power_percentage = str(row.get("power_percentage_arr", "")).strip()
            channel = row.get("channel", "")
            # skip empty rows
            if wavelength == "" and power_percentage == "" and (channel == "" or pd.isna(channel)):
                continue
            channel_arr.append(int(channel))
            wavelength_arr.append(wavelength)
            power_percentage_arr.append(power_percentage)
    except Exception as e:
        print(f"[WARN] Failed to load CSV {path}: {e}")
    return channel_arr, wavelength_arr, power_percentage_arr


# ------------------------------------------------------------------
# Connection handler: one client at a time; client may disconnect and re-connect
# ------------------------------------------------------------------
def handle_connection(conn: Connection):
    """
    Handle a connected client. Accepts simple commands (strings).
    Commands:
      - "ON" / "OFF"                    : toggle laser (simple)
      - "1_on_off"                      : run single_on_off
      - "multi_on_off"                  : run multi_on_off
      - "wavelength"                    : run time_dependent_wavelength (uses CSV)
      - "wavelength,<value>"            : single_on_off for that wavelength
      - "power"                         : run time_dependent_power (if implemented)
      - "STOP"                          : interrupt current task
      - "STATUS"                        : returns current laser_state
      - "QUIT"                          : close this client connection
    """
    global worker_thread

    # init hardware once per process
    grid = init_AOTF()

    # load csv tables
    channel_arr, wavelength_arr, power_percentage_arr = load_wavelength_csv("wavelength_power.csv")

    print("[CONN] Client connected. Ready for commands.")
    set_laser_state("IDLE")

    try:
        while True:
            try:
                cmd = conn.receive()  # legacy text protocol
            except ConnectionError:
                print("[CONN] Client disconnected.")
                break

            if not cmd:
                # empty message, ignore
                continue

            cmd = cmd.strip()
            print(f"[RECV] {cmd}")

            # immediate commands
            if cmd == "STOP":
                stopped = stop_current_task()
                if stopped:
                    safe_send(conn, "STOPPED")
                else:
                    safe_send(conn, "NO_TASK")
                continue

            if cmd == "STATUS":
                safe_send(conn, get_laser_state())
                continue

            if cmd == "QUIT":
                # close this client, but keep server running
                safe_send(conn, "BYE")
                break

            # If busy, reject or allow STOP only
            if worker_is_busy():
                safe_send(conn, "BUSY")
                continue

            # Start various tasks
            if cmd in ["ON", "OFF"]:
                # simple toggle: change power and click once
                channel = DEFAULT_CHANNEL
                power = DEFAULT_POWER
                try:
                    change_power_function(grid, channel, power)
                    time.sleep(0.5)
                    on_coord = get_coord(grid, channel, "on")
                    move_and_click(on_coord)
                    set_laser_state(cmd)
                    safe_send(conn, cmd)
                except Exception as e:
                    print(f"[ERROR] ON/OFF command failed: {e}")
                    safe_send(conn, "ERROR")
                continue

            if cmd == "1_on_off":
                started = start_task_thread(single_on_off, conn, grid, DEFAULT_CHANNEL, DEFAULT_POWER, 1, 1)
                safe_send(conn, "STARTED" if started else "BUSY")
                continue

            if cmd == "multi_on_off":
                started = start_task_thread(multi_on_off, conn, grid, DEFAULT_CHANNEL, DEFAULT_POWER, 1, 1, 3)
                safe_send(conn, "STARTED" if started else "BUSY")
                continue

            if cmd.startswith("wavelength,"):
                # single_on_off for the given wavelength value
                parts = cmd.split(",", 1)
                if len(parts) < 2:
                    safe_send(conn, "BAD_CMD")
                    continue
                wavelength = parts[1].strip()
                # find index in CSV list
                if wavelength in wavelength_arr:
                    idx = wavelength_arr.index(wavelength)
                    channel = channel_arr[idx]
                    power = power_percentage_arr[idx]
                    started = start_task_thread(single_on_off, conn, grid, channel, wavelength, power, 3, 3)
                    safe_send(conn, "STARTED" if started else "BUSY")
                else:
                    safe_send(conn, "UNKNOWN_WAVELENGTH")
                continue

            if cmd == "wavelength":
                # launch the full sweep from CSV
                started = start_task_thread(
                    time_dependent_wavelength,
                    conn, grid, channel_arr, wavelength_arr, power_percentage_arr, 1, 10
                )
                safe_send(conn, "STARTED" if started else "BUSY")
                continue

            if cmd == "power":
                # example: use fixed values; change as needed
                channel = DEFAULT_CHANNEL
                power_values = ["30.5", "22.5", "16.8", "12.5", "9.3", "6.8", "5.3"]
                started = start_task_thread(time_dependent_power, conn, grid, channel, power_values, 1, 1)
                safe_send(conn, "STARTED" if started else "BUSY")
                continue

            # default unknown command
            safe_send(conn, "INVALID")
    finally:
        # ensure worker is requested to stop when client disconnects
        if worker_is_busy():
            print("[CONN] Client disconnected while worker running — requesting stop.")
            set_stop_flag(True)
            # give worker a little time to stop
            time.sleep(1)
        conn.close()
        set_laser_state("IDLE")
        print("[CONN] connection handler terminated.")


# ------------------------------------------------------------------
# Server entrypoint - accept connections forever, handle one client at a time
# ------------------------------------------------------------------
def main():
    server_socket = create_server(HOST, PORT)
    print(f"[SERVER] Laser control server listening on {HOST}:{PORT}")

    try:
        while True:
            conn, addr = Connection.accept(server_socket)
            print(f"[SERVER] Accepted connection from {addr}")

            # Handle this client in the main thread (we keep one client at a time for simplicity).
            # If you want multiple simultaneous controllers, run handle_connection in a thread.
            try:
                handle_connection(conn)
            except Exception as e:
                print(f"[ERROR] Exception in connection handler: {e}")
            finally:
                try:
                    conn.close()
                except:
                    pass

    finally:
        try:
            server_socket.close()
        except:
            pass
        print("[SERVER] Server socket closed.")


if __name__ == "__main__":
    main()
