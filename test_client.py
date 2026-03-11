import socket

HOST = "10.0.0.2"   # IP of Computer 2
PORT = 5000

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
s.sendall(b"hello from computer 1")
s.close()