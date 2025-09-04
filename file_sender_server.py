import os
import socket
from utils.socket_utils import send_cmd, receive_msg, create_server, accept_client

HOST = "0.0.0.0"  # listen on all interfaces
PORT = 5002
CHUNK_SIZE = 4096
FILE_TO_SEND = r"C:\path\to\measurement.csv"  # file to send

def send_file(conn, filepath):
    filesize = os.path.getsize(filepath)
    filename = os.path.basename(filepath)

    # Send header
    send_cmd(conn, f"FILE {filename} {filesize}")
    ack = receive_msg(conn)
    if ack != "READY":
        print("Client not ready")
        return

    # Send file in chunks
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            conn.sendall(chunk)

    send_cmd(conn, "DONE")
    print(f"File {filepath} sent.")

def main():
    server_socket = create_server(HOST, PORT)
    conn, addr = accept_client(server_socket)
    print(f"Client connected: {addr}")

    send_file(conn, FILE_TO_SEND)

    conn.close()
    server_socket.close()

if __name__ == "__main__":
    main()
