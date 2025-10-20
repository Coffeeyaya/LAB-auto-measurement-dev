import os
import time
from pathlib import Path
import zmq

CSV_FOLDER = Path(__file__).parent.parent / 'send_data'
os.makedirs(CSV_FOLDER, exist_ok=True)

ZMQ_PORT = 5003  # separate port for CSV transfer

# ------------------- ZeroMQ CSV Push -------------------
class ZmqCsvPush:
    def __init__(self, socket):
        self.socket = socket

    @classmethod
    def server(cls, port):
        ctx = zmq.Context()
        sock = ctx.socket(zmq.PUSH)
        sock.bind(f"tcp://*:{port}")
        print(f"CSV PUSH server bound to port {port}")
        return cls(sock)

    def send_csv(self, filepath):
        data = open(filepath, "rb").read()
        header = {"cmd": "FILE", "filename": os.path.basename(filepath), "size": len(data)}
        self.socket.send_json(header, flags=zmq.SNDMORE)
        self.socket.send(data)
        print(f"[CSV SERVER] Sent {filepath} ({len(data)} bytes)")


# ------------------- CSV Watcher -------------------
def watch_and_send_csvs(zmq_server: ZmqCsvPush, folder: str):
    """Continuously watch folder for new CSV files and push them."""
    known_files = set()
    try:
        while True:
            current_files = {f for f in os.listdir(folder) if f.endswith(".csv")}
            new_files = sorted(current_files - known_files)
            for new_file in new_files:
                filepath = os.path.join(folder, new_file)
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    zmq_server.send_csv(filepath)
                    time.sleep(1)
                    known_files.add(new_file)
            time.sleep(1)
    except Exception as e:
        print(f"[CSV SERVER] Watcher error: {e}")

def csv_client_handler():
    try:
        zmq_server = ZmqCsvPush.server(ZMQ_PORT)
        watch_and_send_csvs(zmq_server, CSV_FOLDER)
    except ConnectionError:
        print("[CSV SERVER] Client disconnected")
    

# ------------------- Main -------------------
if __name__ == "__main__":
    csv_client_handler()
