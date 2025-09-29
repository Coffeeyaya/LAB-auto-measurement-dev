from LabAuto.network import Connection
import time

def main():
    conn = Connection.connect("192.168.50.101", 5000)

    menu = (
        "\n=== Command Menu ===\n"
        "1. RUN iv_run.py\n"
        "2. KILL iv_run.py\n"
        "3. RUN server_csv.py\n"
        "4. KILL server_csv.py\n"
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
                "1": {"cmd": "RUN", "target": "iv_run.py"},
                "2": {"cmd": "KILL", "target": "iv_run.py"},
                "3": {"cmd": "RUN", "target": "server_csv.py"},
                "4": {"cmd": "KILL", "target": "server_csv.py"},
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
