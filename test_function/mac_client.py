import socket

SERVER_IP = "192.168.0.1"  # replace with Win10 IP
PORT = 5001

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((SERVER_IP, PORT))
print(f"Connected to {SERVER_IP}:{PORT}")

while True:
    cmd = input("Enter command (RUN <path>/KILL/quit): ")
    sock.sendall(cmd.encode())
    if cmd == "quit":
        break
    response = sock.recv(1024).decode().strip()
    print("Response:", response)

sock.close()
