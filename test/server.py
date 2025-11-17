from LabAuto.network import create_server, Connection

server = create_server("0.0.0.0", 5555)
conn, addr = Connection.accept(server)
msg = conn.receive()
conn.send("ok")
obj = conn.receive_json()
conn.close()

