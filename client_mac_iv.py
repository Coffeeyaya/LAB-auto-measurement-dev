# client_mac_iv.py
from utils.socket_utils import send_cmd, receive_msg
import socket

SERVER_IP = "192.168.50.101"  # Replace with server_iv IP
PORT = 5000 # command port

def connect_to_server(ip=SERVER_IP, port=PORT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    print(f"Connected to IV server at {ip}:{port}")
    return sock

def main():
    sock = connect_to_server()
    menu = (
            "\n=== Command Menu ===\n"
            "1. RUN iv_run.py\n"
            "2. KILL iv_run.py\n"
            "3. RUN server_iv_csv.py\n"
            "4. KILL server_iv_csv.py\n"
            "5. quit \n"
            "Enter command (1-5): \n"
        )
    try:
        while True:
            cmd = input(menu).strip()
            if not cmd:
                continue

            send_cmd(sock, cmd)

            if cmd.lower() == "quit":
                response = receive_msg(sock)
                print("[IV RESPONSE]", response)
                break

            # For all other commands, wait for server response
            response = receive_msg(sock)
            print("[IV RESPONSE]", response)

    finally:
        sock.close()
        print("IV client connection closed.")

if __name__ == "__main__":
    main()
