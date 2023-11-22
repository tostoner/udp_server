import cv2
import numpy as np
import socket
import sys
import threading
import queue
import time
import signal
import json
import base64
import os

# Import Sphero RVR SDK
sys.path.append(os.path.expanduser('/home/micro/sphero-sdk-raspberrypi-python'))
from sphero_sdk import SpheroRvrObserver, RvrLedGroups, DriveFlagsBitmask


class RvrServer:
    def __init__(self, ip, port):
        self.stopflag = threading.Event()
        self.sock = self.start_server(ip, port)
        self.camera = self.init_camera()
        self.rvr = self.init_rvr()
        self.reciever_queue = queue.Queue()
        self.sending_queue = queue.Queue()

        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        # Start threads
        self.reciever_thread = threading.Thread(target=self.recv_data)
        self.sending_thread = threading.Thread(target=self.sending_thread)
        self.driver_thread = threading.Thread(target=self.handle_connection)

    # ... [Define other methods like init_camera, init_rvr, recv_data, etc. here]

    def run(self):
        try:
            self.reciever_thread.start()
            self.driver_thread.start()
            self.sending_thread.start()
        except KeyboardInterrupt:
            print("Keyboard interrupt")
        finally:
            self.reciever_thread.join()
            self.driver_thread.join()
            self.sending_thread.join()
            self.cleanup()

    def cleanup(self):
        self.camera.release()
        self.sock.close()
        self.rvr.close()

    def signal_handler(self, _):
        print('You pressed Ctrl+C!')
        self.stopflag.set()
        self.cleanup()

    # ... [Other methods continue here]


if __name__ == "__main__":
    server = RvrServer("10.25.46.172", 12395)
    server.run()
