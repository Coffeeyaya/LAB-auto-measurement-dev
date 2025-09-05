import socket, os, time

CSV_FOLDER = r"C:\Users\mmm11\OneDrive\桌面\yun-chen\code\auto\LAB-auto-measurement\data"
HOST = "0.0.0.0"
PORT = 5001

def send_file(conn, filepath):
    filesize = os.path.getsize(filepath)
    filename = os.path.basename(filepath)
    conn.sendall(f"FILE {filename} {filesize}\n".encode())
    ack = conn.recv(1024).decode().strip()
    if ack != "READY":
        return
    with open(filepath, "rb") as f:
        while chunk := f.read(4096):
            conn.sendall(chunk)
    conn.sendall(b"FILE_DONE\n")
    print(f"Sent {filename}")

def watch_and_send(conn):
    known_files = set()
    while True:
        current_files = {f for f in os.listdir(CSV_FOLDER) if f.endswith(".csv")}
        new_files = current_files - known_files
        for f in new_files:
            send_file(conn, os.path.join(CSV_FOLDER, f))
            known_files.add(f)
        time.sleep(1)

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"CSV server listening on {HOST}:{PORT}")
    conn, addr = server.accept()
    print(f"Connected by {addr}")
    try:
        watch_and_send(conn)
    finally:
        conn.close()
        server.close()

if __name__ == "__main__":
    main()
