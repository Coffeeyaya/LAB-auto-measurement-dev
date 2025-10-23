from LabAuto.network import Connection
import time

def main():
    conn = Connection.connect("192.168.151.20", 5000)
    # conn = Connection.connect("127.0.0.1", 5001)

    menu = (
        "\n=== Command Menu ===\n"
        "1. RUN laser_control.py\n"
        "2. KILL laser_control.py\n"
        "3. RUN laser_test.py\n"
        "4. KILL laser_test.py\n"
        "5. quit\n"
        "Enter command (1-5): "
    )

    try:
        while True:
            cmd = input(menu).strip()
            if not cmd:
                continue

            # Map menu number to structured JSON command
            cmd_map = {
                "1": {"cmd": "RUN", "target": "laser_control.py"},
                "2": {"cmd": "KILL", "target": "laser_control.py"},
                "3": {"cmd": "RUN", "target": "laser_test.py"},
                "4": {"cmd": "KILL", "target": "laser_test.py"},
                "5": {"cmd": "QUIT"}
            }

            if cmd not in cmd_map:
                print("Invalid option, please choose 1-5.")
                continue

            # Send JSON command
            conn.send_json(cmd_map[cmd])

            # Receive JSON response
            response = conn.receive_json()
            print("[IV RESPONSE]", response)

            if cmd == "5":  # quit
                break
            time.sleep(1)

    finally:
        conn.close()
        print("IV client connection closed.")


if __name__ == "__main__":
    main()
