import time
import os 
from pathlib import Path
from LabAuto.network import create_server, Connection

# act as client, connect to win 7 server
WIN_7_SERVER_IP = "192.168.50.17"
WIN_7_PORT = 5001

conn = Connection.connect(WIN_7_SERVER_IP, WIN_7_PORT)
while True:
    command = input()
    conn.send(command)