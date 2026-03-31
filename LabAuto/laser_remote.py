from .network import Connection
import threading
import queue

class LaserController:
    """Asynchronous controller that never blocks the Keithley measurement loop."""
    def __init__(self, laser_ip, port=5001):
        self.conn = Connection.connect(laser_ip, port)
        self.cmd_queue = queue.Queue()
        self.running = True
        
        # Start a dedicated, invisible background thread just for network traffic
        self.worker = threading.Thread(target=self._network_worker, daemon=True)
        self.worker.start()

    def send_cmd(self, payload, wait_for_reply=True):
        """Drops the command in the queue and returns instantly if wait_for_reply=False."""
        if not wait_for_reply:
            # FIRE AND FORGET: Takes ~1 microsecond. Zero network lag!
            self.cmd_queue.put((payload, False, None))
            return None
        else:
            # SYNCHRONOUS MODE: Wait specifically for this reply
            response_container = []
            self.cmd_queue.put((payload, True, response_container))
            self.cmd_queue.join() # block main thread, wait for the background worker to finish this specific task
            # Stop here and wait until the queue's internal task counter reaches zero
            return response_container[0]
        
    def _network_worker(self):
        while self.running:
            try:
                task = self.cmd_queue.get(timeout=0.2)
                payload, wait_for_reply, response_container = task

                try:
                    self.conn.send_json(payload)
                    reply = self.conn.receive_json() # block worker thread

                    if wait_for_reply and response_container is not None:
                        response_container.append(reply)

                finally:
                    # GUARANTEED execution
                    self.cmd_queue.task_done()
                    # simply decrements an internal counter inside the Queue object. (like condition variable)
                    # The worker thread then immediately loops back to the top to wait for the next task. 
                    # It stays alive.

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Background Network Error: {e}")

    def close(self):
        self.running = False
        if self.worker.is_alive():
            self.worker.join(timeout=1.0) # Gracefully shut down the background worker
        self.conn.close()