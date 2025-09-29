from LabAuto.network import create_server, Connection

HOST = "127.0.0.1"
PORT = 5000

server_socket = create_server(HOST, PORT)
conn, addr = Connection.accept(server_socket)

while True:
    try:
        cmd = conn.receive()
        print("Received command:", cmd)

        if cmd == "START_IV":
            conn.send("IV started")
        elif cmd == "STOP_IV":
            conn.send("IV stopped")
        else:
            conn.send(f"Unknown command: {cmd}")
    except ConnectionError:
        print("Client disconnected")
        break

conn.close()
server_socket.close()
