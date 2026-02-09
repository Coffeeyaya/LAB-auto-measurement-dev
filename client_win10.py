from LabAuto.network import Connection
from LabAuto.network import ReconnectConnection
import time

def main():
    conn = ReconnectConnection.connect("192.168.50.101", 5000)

    menu = (
        "\n=== Command Menu ===\n"
        "0. quit\n"
        "1. RUN lab_iv_run.py\n"
        "2. KILL lab_iv_run.py\n"
        "3. RUN server_csv.py\n"
        "4. KILL server_csv.py\n"
        "5. RUN interface_auto.py\n"
        "6. KILL interface_auto.py\n"
        "Enter command (0-6): "
    )

    try:
        while True:
            cmd = input(menu).strip()
            if not cmd:
                continue

            # Map menu number to structured JSON command
            cmd_map = {
                "0": {"cmd": "QUIT"},
                "1": {"cmd": "RUN", "target": "lab_iv_run.py"},
                "2": {"cmd": "KILL", "target": "lab_iv_run.py"},
                "3": {"cmd": "RUN", "target": "server_csv.py"},
                "4": {"cmd": "KILL", "target": "server_csv.py"},
                "5": {"cmd": "RUN", "target": "interface_auto.py"},
                "6": {"cmd": "KILL", "target": "interface_auto.py"}
            }

            if cmd not in cmd_map:
                print("Invalid option, please choose 0-6.")
                continue

            # Send JSON command
            conn.send_json(cmd_map[cmd])

            # Receive JSON response
            response = conn.receive_json()
            print("[IV RESPONSE]", response)

            if cmd == "0":  # quit
                break
            time.sleep(1)

    finally:
        conn.close()
        print("mac client connection closed.")


if __name__ == "__main__":
    main()
