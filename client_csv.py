import os
from LabAuto.network import Connection

SERVER_IP = "192.168.50.101"  # Windows IV machine
# SERVER_IP = '127.0.0.1'
PORT = 5002
SAVE_DIR = os.path.abspath("./receive_data/data") ###
os.makedirs(SAVE_DIR, exist_ok=True)

CHUNK_SIZE = 4096

def receive_file(conn: Connection):
    """Receive a single CSV file via JSON header and raw chunks."""
    header = conn.receive_json()
    if header.get("cmd") != "FILE":
        print("[CSV CLIENT] Unexpected message:", header)
        return

    filename = header["filename"]
    filesize = header["size"]
    filepath = os.path.join(SAVE_DIR, filename)

    # Send READY to start receiving
    conn.send_json({"status": "READY"})

    received = 0
    with open(filepath, "wb") as f:
        while received < filesize:
            chunk = conn.sock.recv(min(CHUNK_SIZE, filesize - received))
            if not chunk:
                break
            f.write(chunk)
            received += len(chunk)

    done = conn.receive_json()
    if done.get("cmd") == "FILE_DONE":
        print(f"[CSV CLIENT] Received {filename} ({filesize} bytes)")
    else:
        print(f"[CSV CLIENT] File incomplete: {filename}")

def main():
    conn = Connection.connect(SERVER_IP, PORT)
    print(f"[CSV CLIENT] Connected to {SERVER_IP}:{PORT}")

    try:
        while True:
            receive_file(conn)
    except (ConnectionError, KeyboardInterrupt):
        print("[CSV CLIENT] Server disconnected or interrupted")
    finally:
        conn.sock.close()

if __name__ == "__main__":
    main()
