import cv2
import numpy as np
import socket
import sys
import threading
import queue
import time
import signal
import sys
import json
import base64
import os
import RvrServer
jsonFile = '{"speed": 0, "heading": 0, "message": "video", "frame": 0}'
sys.path.append(os.path.expanduser('/home/micro/sphero-sdk-raspberrypi-python'))
try:
    from sphero_sdk import SpheroRvrObserver

    from sphero_sdk import RvrLedGroups
    from sphero_sdk import DriveFlagsBitmask

except ImportError:
    raise ImportError('Cannot import from sphero_sdk')

stopflag = threading.Event()
addr = 0

if __name__ == "__main__":
    MAX_UDP_PACKET_SIZE = 65536
    SOCK = start_server("10.25.46.172", 12395)
    
