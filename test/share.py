import http.server
import socketserver
import socket
import threading
import os

PORT = 8000
DIRECTORY = os.path.join(os.path.dirname(__file__), "data")  # change folder here

# Create handler that serves the specified folder
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

# Threaded TCP Server
class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

# Find LAN IPv4 addresses
hostname = socket.gethostname()
all_ips = socket.gethostbyname_ex(hostname)[2]
lan_ips = [ip for ip in all_ips if ip.startswith("192.") or ip.startswith("10.") or ip.startswith("172.")]

if not lan_ips:
    lan_ips = ["0.0.0.0"]

print("Server will be reachable at:")
for ip in lan_ips:
    print(f"  http://{ip}:{PORT}/")

# Start server
with ThreadedTCPServer(("", PORT), Handler) as httpd:
    print(f"Serving folder '{DIRECTORY}' on port {PORT}...")
    httpd.serve_forever()
