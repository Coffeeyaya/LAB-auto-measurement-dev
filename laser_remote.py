import threading
from LabAuto.network import Connection

class LaserController:

    def __init__(self, laser_ip, port=5001):
        self.conn = Connection.connect(laser_ip, port)
        self.lock = threading.Lock()  # prevent concurrent socket use

    def _send(self, payload):
        with self.lock:
            self.conn.send_json(payload)
            return self.conn.receive_json()

    def send_async(self, payload):
        t = threading.Thread(target=self._send, args=(payload,), daemon=True)
        t.start()

    def set_wavelength(self, channel, wavelength, async_mode=False):
        cmd = {"channel": int(channel), "wavelength": str(wavelength)}
        if async_mode:
            self.send_async(cmd)
        else:
            self._send(cmd)

    def set_power(self, channel, power, async_mode=False):
        cmd = {"channel": int(channel), "power": str(power)}
        if async_mode:
            self.send_async(cmd)
        else:
            self._send(cmd)

    def toggle_light(self, channel, async_mode=False):
        # Press ON/OFF button to toggle light
        cmd = {"channel": int(channel), "on": 1}
        if async_mode:
            self.send_async(cmd)
        else:
            self._send(cmd)

    def close(self):
        self.conn.close()