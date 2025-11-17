import http.server
import socketserver
import socket

PORT = 8000

# Find local IPv4 addresses
hostname = socket.gethostname()
ips = socket.gethostbyname_ex(hostname)[2]
lan_ips = [ip for ip in ips if ip.startswith("192.") or ip.startswith("10.") or ip.startswith("172.")]

print("Server will be reachable at:")
for ip in lan_ips:
    print(f"  http://{ip}:{PORT}/")

# Start HTTP server on all interfaces
with socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
    print(f"Serving HTTP on port {PORT}...")
    httpd.serve_forever()
