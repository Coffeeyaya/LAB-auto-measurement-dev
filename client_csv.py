from pathlib import Path
import zmq

SAVE_DIR = Path(__file__).parent.parent / 'receive_csv'
SAVE_DIR.mkdir(exist_ok=True)

SERVER_IP = "192.168.50.101"
ZMQ_PORT = 5003                # must match the server PUSH port


class ZmqCsvPull:
    """Client side: receive CSV files pushed by server."""
    def __init__(self, socket):
        self.socket = socket

    @classmethod
    def client(cls, host_ip, port):
        ctx = zmq.Context()
        sock = ctx.socket(zmq.PULL)
        sock.connect(f"tcp://{host_ip}:{port}")
        print(f"CSV Client connected to {host_ip}:{port}")
        return cls(sock)

    def receive_csv(self, save_dir="."):
        header = self.socket.recv_json()
        data = self.socket.recv()
        filepath = Path(save_dir) / header["filename"]
        with open(filepath, "wb") as f:
            f.write(data)
        print(f"Received {header['filename']} ({len(data)} bytes)")


def main():
    zmq_client = ZmqCsvPull.client(SERVER_IP, ZMQ_PORT)
    while True:
        zmq_client.receive_csv(SAVE_DIR)


if __name__ == "__main__":
    main()
