from LabAuto.network import Connection #
from pm.power import zero_sensor, measure_power

LIGHT_IP = "192.168.50.17" #

conn = Connection.connect(LIGHT_IP, 5001)
conn.send_json({"channel": 6, "wavelength": "660"})
conn.receive_json() # Wait for confirmation

wavelength=660
average_count=10
measure_interval=0.2
num_points=10

zero_sensor(meter)
