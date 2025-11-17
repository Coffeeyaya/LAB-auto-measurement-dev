import http.server
import socketserver
from pathlib import Path

PORT = 8000
DIRECTORY = Path(__file__).parent.parent / 'receive_data' / 'data'

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving at http://0.0.0.0:{PORT}/")
    httpd.serve_forever()

