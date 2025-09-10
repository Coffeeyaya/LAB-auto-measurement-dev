# client_mac_laser.py
from utils.socket_utils import send_cmd, receive_msg
import socket
import time

SERVER_IP = "192.168.151.20"  # Replace with server_laser IP
PORT = 5000

def connect_to_server(ip=SERVER_IP, port=PORT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    print(f"Connected to Laser server at {ip}:{port}")
    return sock

def main():
    sock = connect_to_server()
    menu = (
            "\n=== Command Menu ===\n"
            "1. RUN laser_control.py\n"
            "2. KILL laser_control.py\n"
            "3. quit \n"
            "Enter choice (1-3): \n"
        )
    try:
        while True:
            cmd = input(menu).strip()
            if not cmd:
                continue
            send_cmd(sock, cmd)
            # wait for response
            response = receive_msg(sock)
            print("[LASER RESPONSE]", response)
            if cmd.lower() == "quit":
                break
    finally:
        sock.close()
        print("Laser client connection closed.")

if __name__ == "__main__":
    main()
