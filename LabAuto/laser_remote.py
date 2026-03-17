from network import Connection

# class LaserController:
#     """Simplified, lock-free controller for use in background threads."""
#     def __init__(self, laser_ip, port=5001):
#         self.conn = Connection.connect(laser_ip, port)

#     def send_cmd(self, payload, wait_for_reply=True):
#         self.conn.send_json(payload)
#         if wait_for_reply:
#             return self.conn.receive_json()

#     def close(self):
#         self.conn.close()

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

    def _network_worker(self):
        """This runs completely in the background, handling the slow network handshakes."""
        while self.running:
            try:
                # Wait for a command to appear in the queue
                task = self.cmd_queue.get(timeout=0.2)
                payload, wait_for_reply, response_container = task
                
                # Send the command and ALWAYS receive the reply to keep the TCP buffer clean!
                self.conn.send_json(payload)
                reply = self.conn.receive_json() 
                
                # If the main thread wanted to see the reply, give it back
                if wait_for_reply and response_container is not None:
                    response_container.append(reply)
                    
                self.cmd_queue.task_done()
            except queue.Empty:
                continue # No commands waiting, keep looping
            except Exception as e:
                print(f"Background Network Error: {e}")

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
            self.cmd_queue.join() # Wait for the background worker to finish this specific task
            return response_container[0]

    def close(self):
        self.running = False
        if self.worker.is_alive():
            self.worker.join(timeout=1.0) # Gracefully shut down the background worker
        self.conn.close()