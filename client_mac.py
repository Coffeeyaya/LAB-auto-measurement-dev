from utils.socket_utils import send_cmd, receive_msg, wait_for
import socket

# SERVER_IP = "192.168.137.1"
SERVER_IP = "192.168.151.20" # for server_laser(Windows 7)
SERVER_IP = "" # for server_iv (Windows 10)
PORT = 5000

def connect_to_server(ip=SERVER_IP, port=PORT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    print(f"Connected to {ip}:{port}")
    return sock

def main():
    sock = connect_to_server()
    try:
        while True:
            cmd = input("Enter command (RUN <script>/KILL <script>/quit): ").strip()
            send_cmd(sock, cmd)
            if cmd.lower() == "quit":
                break
            # Wait for response using socket_utils
            response = receive_msg(sock)
            print("Response:", response)
    finally:
        sock.close()
        print("Connection closed.")

if __name__ == "__main__":
    main()
