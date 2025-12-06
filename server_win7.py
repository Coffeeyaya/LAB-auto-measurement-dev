# import os
# from LabAuto.script_manager import run_server, set_server_name

# set_server_name(os.path.basename(__file__))

# HOST = '0.0.0.0'
# PORT = 5000

# if __name__ == "__main__":
#     run_server(HOST, PORT)


from threading import Thread
import os
import time
from LabAuto.script_manager import run_server_threading, set_server_name

set_server_name(os.path.basename(__file__))

HOST = '0.0.0.0'
PORT1 = 5000
# PORT2 = 7000

if __name__ == "__main__":
    # Start server on port 5000
    Thread(target=run_server_threading, args=(HOST, PORT1), daemon=True).start()
    # Start server on port 7000
    # Thread(target=run_server_threading, args=(HOST, PORT2), daemon=True).start()

    print(f"[SERVER] Listening on ports {PORT1}")
    # print(f"[SERVER] Listening on ports {PORT1} and {PORT2}")

    # Keep main thread alive
    while True:
        time.sleep(1)
