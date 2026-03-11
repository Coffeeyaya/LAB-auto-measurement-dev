import socket

HOST = "0.0.0.0"
PORT = 5000

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(1)

print("Waiting for connection...")
conn, addr = s.accept()
print("Connected from:", addr)

data = conn.recv(1024)
print("Received:", data.decode())
conn.close()