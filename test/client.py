from LabAuto.network import Connection

conn = Connection.connect("127.0.0.1", 5555)
conn.send("hello")
reply = conn.receive()
# send JSON
conn.send_json({"cmd": "move", "steps": 100})

conn.close()
