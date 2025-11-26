import os
from LabAuto.script_manager import run_server, set_server_name

set_server_name(os.path.basename(__file__))

HOST = '0.0.0.0'
PORT = 7000

if __name__ == "__main__":
    run_server(HOST, PORT)


