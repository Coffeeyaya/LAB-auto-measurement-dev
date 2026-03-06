from LabAuto.network import Connection

class LaserController:
    """Simplified, lock-free controller for use in background threads."""
    def __init__(self, laser_ip, port=5001):
        self.conn = Connection.connect(laser_ip, port)

    def send_cmd(self, payload, wait_for_reply=True):
        self.conn.send_json(payload)
        if wait_for_reply:
            return self.conn.receive_json()

    def close(self):
        self.conn.close()