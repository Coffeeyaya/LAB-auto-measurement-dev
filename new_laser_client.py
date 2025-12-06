#!/usr/bin/env python3
import time
from LabAuto.network import Connection

SERVER_IP = "192.168.50.101"  # lab computer IP
SERVER_PORT = 5001             # matches laser_control.py

def main():
    conn = None

    # Attempt to connect, retry if server is not ready
    while conn is None:
        try:
            conn = Connection.connect(SERVER_IP, SERVER_PORT)
        except Exception as e:
            print(f"[CLIENT] Failed to connect: {e}. Retrying in 3s...")
            time.sleep(3)

    menu = """
=== Laser Control Menu ===
1. Run full wavelength sweep (CSV)
2. Run single 1_on_off
3. Run multi_on_off
4. Stop current task
5. Get current status
6. Quit
Enter option: """

    try:
        while True:
            choice = input(menu).strip()

            if choice == "1":
                conn.send("wavelength")
            elif choice == "2":
                conn.send("1_on_off")
            elif choice == "3":
                conn.send("multi_on_off")
            elif choice == "4":
                conn.send("STOP")
            elif choice == "5":
                conn.send("STATUS")
            elif choice == "6":
                conn.send("QUIT")
                print("[CLIENT] Quitting...")
                break
            else:
                print("Invalid option.")
                continue

            # Receive server response (blocking)
            try:
                response = conn.receive()
                print(f"[SERVER] {response}")
            except Exception as e:
                print(f"[CLIENT] Connection lost: {e}")
                # Try reconnecting
                conn = None
                while conn is None:
                    try:
                        conn = Connection.connect(SERVER_IP, SERVER_PORT)
                    except Exception as e:
                        print(f"[CLIENT] Retry failed: {e}")
                        time.sleep(3)

    finally:
        if conn:
            conn.close()
        print("[CLIENT] Connection closed.")

if __name__ == "__main__":
    main()
