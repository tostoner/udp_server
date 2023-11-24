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

sys.path.append(os.path.expanduser('/home/micro/sphero-sdk-raspberrypi-python'))
from sphero_sdk import SpheroRvrObserver, RvrLedGroups, DriveFlagsBitmask

class RvrServer:
    stopflag = False
    addr = None
    jsonFile_to_send = {"speed": 0, "heading": 0, "message": "None", "frame": 0, "videoRunning": False}
    jsonFile = {"speed": 0, "heading": 0, "message": "None"}
    DT = 1/30 # simply used to do everything at 30Hz. Trying to limit cpu use

    def __init__(self, ip, port):
        self.stopflag = threading.Event()
        self.sock = self.start_server(ip, port)
        self.reciever_queue = queue.Queue()
        self.sending_queue = queue.Queue()
        self.init_rvr()
        self.init_camera()

        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        # Start threads
        self.reciever_thread = threading.Thread(target=self.recieverMethod)
        self.sending_thread = threading.Thread(target=self.sendingMethod)
        self.driver_thread = threading.Thread(target=self.driverMethod)

    def init_rvr(self):
        self.rvr = SpheroRvrObserver()
        self.rvr.on_did_sleep_notify(handler=self.keepAwake)

        print("robot object created")

        try:
            print("waking robot")
            self.rvr.wake()
            print("robot awake")
            time.sleep(1)
            print("setting leds")
            self.rvr.set_all_leds(
                led_group=RvrLedGroups.all_lights.value,
                led_brightness_values=[color for _ in range(10) for color in [0, 255, 0]]
            )
            print("leds set")
            self.rvr.reset_yaw()
            print("yaw reset")
            def battery_percentage_handler(percentage):
                print(f"Battery Percentage: {percentage}%")
            self.rvr.get_battery_percentage(battery_percentage_handler, timeout=100)
            print("RVR initialized")
        except Exception as e:
            print(f"Error initializing RVR: {e}")

    def init_camera(self):
        self.camera = cv2.VideoCapture(0)
        print("camera started")
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        print("capture frame resized")
        

    def capture_and_compress(self):
        ret, frame = self.camera.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            success, encoded_frame = cv2.imencode('.jpg', frame)
            if not success:
                print("Error encoding frame")
                return None
            base64_frame = base64.b64encode(encoded_frame).decode('utf-8')
            return base64_frame
        else:
            print("Frame not found")
            return None

    def recieverMethod(self):

        while not self.stopflag.is_set():
            time.sleep(self.DT)
            try:
                data, self.addr = self.sock.recvfrom(4096)
                data = data.decode("utf-8")
                print(f"data recieved {data}")
                try: 
                    json_data = json.loads(data)
                    if self.reciever_queue.qsize() >= 10:
                        # This will remove the oldest item from the queue
                        self.reciever_queue.get_nowait()
                    
                    self.reciever_queue.put((json_data))
                except ValueError:
                    print("Error: Value converting to json")
                
            except OSError as e:
                print(f"Socket error: {str(e)}")
            if self.stopflag.is_set():
                break

    def run(self):
        self.reciever_thread.start()
        self.driver_thread.start()
        self.sending_thread.start()

    def driverMethod(self):
        speedInput = 0
        headingInput = 0
        print("driver thread started")
        while not self.stopflag.is_set():
            #print("driver thread running")
            self.keepAwake()

            message = None
            try:
                self.jsonFile = self.reciever_queue.get(block=False)
                
            except queue.Empty:
                #print("Queue empty")
                self.jsonFile[message] = "no input"

            if self.jsonFile.get("message") != "no input":
                speedInput = self.jsonFile.get("speed")
                headingInput = self.jsonFile.get("heading")
                message = self.jsonFile.get("message")
                #print(f"Message: {message}, Speed: {speedInput}, Heading: {headingInput}")

            if message == "start_video":
                self.jsonFile_to_send["videoRunning"] = True
                #print("self.jsonFile_to_send['videoRunning'] = True")
            elif message == "stop_video":
                self.jsonFile_to_send["video"] = False
                #print("self.jsonFile_to_send['videoRunning'] = False")
            elif message == "drive":
                self.rvr.drive_with_heading(speed = speedInput, heading = headingInput, flags=DriveFlagsBitmask.none.value)
            elif message == "drive_reverse":
                self.rvr.drive_with_heading(speed = speedInput, heading = headingInput, flags=DriveFlagsBitmask.drive_reverse.value)
            elif message =="dont_drive":
                self.rvr.drive_with_heading(speed = 0, heading = headingInput, flags=DriveFlagsBitmask.none.value)

            if self.stopflag.is_set():
                break
            time.sleep(self.DT)

    def sendingMethod(self):
        while not self.stopflag.is_set():
            videoRunning = self.jsonFile_to_send.get("videoRunning")
            if videoRunning:
                #print("video running")
                compressed_frame = self.capture_and_compress()
                self.jsonFile_to_send["frame"] = compressed_frame
                jsonBytes = json.dumps(self.jsonFile_to_send).encode('utf-8')
                #print(self.addr)
                self.UDP_send(jsonBytes)
                #print("Message sent")

            else:
                jsonBytes = json.dumps(self.jsonFile).encode('utf-8')
                self.UDP_send(jsonBytes)
                #print("Video not running, message sent")
            self.jsonFile_to_send.clear()

            time.sleep(self.DT)


    def UDP_send(self, string):
        if self.addr is not None:
            try:
                sock = self.sock
                sock.sendto(string, self.addr)
                print(f"{sys.getsizeof(string)} bytes sent")
            except socket.error as e:
                frame_size = sys.getsizeof(string) 
                print("Frame size:", frame_size)
                print(e)
                return False
            return True
        print("No address to send to")


    def start_server(self,ip, port):
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
        sock.bind((ip, port))
        print("Server started")
        return sock

    def cleanup(self):
        self.camera.release()
        self.sock.close()
        self.rvr.close()

    def signal_handler(self, signal_received, frame):
        print('Signal received, shutting down!')
        self.stopflag.set()
        self.cleanup()
        self.reciever_thread.join()
        self.driver_thread.join()
        self.sending_thread.join()
    def keepAwake(self):
        #print("RVR is trying to sleep, waking up...")
        self.rvr.wake()

        # ... [Other methods continue here]