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
import pi_servo_hat
import qwiic


sys.path.append(os.path.expanduser('/home/micro/sphero-sdk-raspberrypi-python'))
from sphero_sdk import SpheroRvrObserver, RvrLedGroups, DriveFlagsBitmask

class RvrServer:
    addr = None
    jsonFile_to_send = {"speed": 0, "heading": 0,  "message": "None", "videoRunning": False, "distance": 0}
    jsonFile = {"speed": 0, "heading": 0, "tiltPosition" : 0, "panPosition" : 0, "distance": 0, "message": "None"}
    UDP_PACKET_SIZE = 60000 # a littlne smaller than 65000 to compensate for the rest of the json file
    DT = 1/30 #Simply used to do everything at 30Hz. Trying to limit cpu use


    def __init__(self, ip, port):
        self.stopflag = threading.Event()
        self.sock = self.start_server(ip, port)
        self.reciever_queue = queue.Queue()
        self.sending_queue = queue.Queue()

        # Initialize the PiServoHat object
        self.servo = pi_servo_hat.PiServoHat()
        self.servo.restart()

       # Initialize the ToF sensor
        self.tof_sensor = qwiic.QwiicVL53L1X()
        if self.tof_sensor.sensor_init() is None:
            print("ToF Sensor online!\n")
            self.tof_sensor.start_ranging()
            time.sleep(0.005)
            distance = self.tof_sensor.get_distance()
            time.sleep(0.005)
            self.tof_sensor.stop_ranging()
            distance_mm = distance
        
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

    def determine_frame_parts(self, base64_frame):
        frame_size = len(base64_frame)
        num_parts = -(-frame_size // self.UDP_PACKET_SIZE)
        frame_parts = []

        for i in range(num_parts):
            start_index = i * self.UDP_PACKET_SIZE
            end_index = start_index + self.UDP_PACKET_SIZE
            chunk = base64_frame[start_index:end_index]
            frame_parts.append(chunk)

        return frame_parts


    def capture_and_compress(self):
        ret, frame = self.camera.read()
        if ret:
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
                panInput = self.jsonFile.get("panPosition")
                tiltInput = self.jsonFile.get("tiltPosition")
                message = self.jsonFile.get("message")
                distance = self.jsonFile.get("distance")
                #print(f"Message: {message}, Speed: {speedInput}, Heading: {headingInput}")

          # Move the servo motors based on pan and tilt values
            if panInput is not None:
                # Adjust the input values to be in the range of -90 to 90
                pan_input_adjusted = max(min(panInput, 90), -90)
                # Map the adjusted input value to the servo range with 0 in the middle
                pan_servo_position = int(pan_input_adjusted * (180 / 90) + 90)
                self.servo.move_servo_position(0, pan_servo_position, 180)  # Assuming pan is on pin 0
            
            if tiltInput is not None:
                # Adjust the input values to be in the range of -90 to 90
                tilt_input_adjusted = max(min(tiltInput, 90), -90)
                # Map the adjusted input value to the servo range with 0 in the middle
                tilt_servo_position = int(tilt_input_adjusted * (180 / 90) + 90)
                self.servo.move_servo_position(1, tilt_servo_position, 180)  # Assuming tilt is on pin 1
            

            if message == "start_video":
                self.jsonFile_to_send["videoRunning"] = True
            elif message == "stop_video":
                self.jsonFile_to_send["videoRunning"] = False
            elif message == "drive":
                self.rvr.drive_with_heading(speed = speedInput, heading = headingInput, flags=DriveFlagsBitmask.none.value)
            elif message == "drive_reverse":
                self.rvr.drive_with_heading(speed = speedInput, heading = headingInput, flags=DriveFlagsBitmask.drive_reverse.value)
            elif message =="dont_drive":
                self.rvr.drive_with_heading(speed = 0, heading = headingInput, flags=DriveFlagsBitmask.none.value)
            elif message =="collision_detected":
                self.rvr.drive_with_heading(speed = 0, heading = headingInput, flags=DriveFlagsBitmask.none.value)

            if self.stopflag.is_set():
                break
            time.sleep(self.DT)

    def sendingMethod(self):
        while not self.stopflag.is_set():
            videoRunning = self.jsonFile_to_send.get("videoRunning")
            if videoRunning:
                compressed_frame = self.capture_and_compress()
                if compressed_frame:
                    frame_parts = self.determine_frame_parts(compressed_frame)
                    for i, part in enumerate(frame_parts):
                        frame_packet = {
                            "frame_part": part,
                            "part_number": i,
                            "total_parts": len(frame_parts)
                        }
                        jsonBytes = json.dumps(frame_packet).encode('utf-8')
                        self.UDP_send(jsonBytes)
            else:
                jsonBytes = json.dumps(self.jsonFile).encode('utf-8')
                self.UDP_send(jsonBytes)

        self.sendStatusInfo()
        time.sleep(self.DT)


    def sendStatusInfo(self):
        # Create a JSON message with distance and battery status
        status_packet = {
            "distance": self.jsonFile_to_send.get("distance"),
          # "battery_status": self.jsonFile.get("battery_status"),
        }
        jsonBytes = json.dumps(status_packet).encode('utf-8')
        self.UDP_send(jsonBytes)

    
    def UDP_send(self, packet):
        if self.addr is not None:
            try:
                self.sock.sendto(packet, self.addr)
                #print(f"Sent {len(packet)} bytes")
            except socket.error as e:
                print(f"Error sending packet: {e}")


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
