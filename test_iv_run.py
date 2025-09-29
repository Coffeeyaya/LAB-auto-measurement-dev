from LabAuto.network import Connection, create_server

# 1. connect to laser_control (client role)
# laser_conn = Connection.connect("192.168.151.20", 5001)

# 2. listen for Mac UI (server role)
server_socket = create_server("0.0.0.0", 6000)  # choose a free port
mac_conn, addr = Connection.accept(server_socket)
# ask Mac for parameters
mac_conn.send_json({"cmd": "REQUEST_PARAMS", "message": "Please enter parameters"})

# wait for parameters
params = mac_conn.receive_json()
print("Received parameters from Mac:", params)

material = params.get("material", "default")
device_number = params.get("device_number", "default")


# later, during measurement, send progress
mac_conn.send_json({"cmd": "PROGRESS", "progress": "Measurement started"})
# keep process alive if needed
while True:
    pass