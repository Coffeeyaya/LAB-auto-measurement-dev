from LabAuto.network import Connection

HOST = "127.0.0.1"
PORT = 5000

conn = Connection.connect(HOST, PORT)
str1 = input("start iv?")
conn.send("START_IV")
reply = conn.receive()
print("Server replied:", reply)

str2 = input("stop iv?")
conn.send("STOP_IV")
reply = conn.receive()
print("Server replied:", reply)

conn.close()
