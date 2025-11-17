import http.server
import socketserver
from pathlib import Path
import socket

PORT = 8000
DIRECTORY = Path(__file__).parent.parent / 'send_data'
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

# Force IPv4
class TCPServerV4(socketserver.TCPServer):
    address_family = socket.AF_INET
    allow_reuse_address = True

with TCPServerV4(("", PORT), Handler) as httpd:
    print(f"Serving at http://0.0.0.0:{PORT}/")
    httpd.serve_forever()

