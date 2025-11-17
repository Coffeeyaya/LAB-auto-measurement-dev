import http.server
import socketserver
import socket
import webbrowser

PORT = 8000

# Find local IPv4 addresses (LAN)
hostname = socket.gethostname()
all_ips = socket.gethostbyname_ex(hostname)[2]
lan_ips = [ip for ip in all_ips if ip.startswith("192.") or ip.startswith("10.") or ip.startswith("172.")]

if not lan_ips:
    print("No LAN IPv4 address found. Using 0.0.0.0")
    lan_ips = ["0.0.0.0"]

print("Server will be reachable at:")
for ip in lan_ips:
    print(f"  http://{ip}:{PORT}/")

# Open first reachable IP in default browser automatically
webbrowser.open(f"http://{lan_ips[0]}:{PORT}/")

# Start HTTP server on all interfaces
with socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
    print(f"Serving HTTP on port {PORT}...")
    httpd.serve_forever()
