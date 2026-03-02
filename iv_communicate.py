from LabAuto.network import Connection

# Connect to the Light Computer
conn = Connection.connect("192.168.1.100", 5001)

# Sequence: vg = -1, vg = 1, light on, light off

# 1. Tell Light PC we are at Vg = -1
set_hardware_vg(-1)
conn.send_json({"cmd": "UPDATE_VG", "vg": -1})
response = conn.receive_json() # Wait for ACK
measure_data()

# 2. Tell Light PC we are at Vg = 1
set_hardware_vg(1)
conn.send_json({"cmd": "UPDATE_VG", "vg": 1})
response = conn.receive_json() # Wait for ACK
measure_data()

# 3. Tell Light PC to turn ON (passing specific channel and power)
conn.send_json({"cmd": "SET_LIGHT", "state": "ON", "channel": 6, "power": "17"})
response = conn.receive_json() # Blocks until GUI clicks are finished
print(f"Light is now: {response['current_state']}")
measure_data()

# 4. Tell Light PC to turn OFF
conn.send_json({"cmd": "SET_LIGHT", "state": "OFF", "channel": 6})
response = conn.receive_json() # Blocks until GUI clicks are finished