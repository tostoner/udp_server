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
    jsonFile_to_send = {"speed": 0, "heading": 0,  "message": "None", "videoRunning": True, "distance": 0}
    jsonFile_recieved = {"speed": 0, "heading": 0, "tiltPosition" : 0, "panPosition" : 0, "message": "None"}
    UDP_PACKET_SIZE = 64000
    DT = 1/1000 #Trying to limit cpu use by sleeping threads.
    jpeg_quality = 100 # from 0 to 100
    frame_width = 160
    frame_height = 120



    def __init__(self, ip, port):
        self.stopflag = threading.Event()
        self.sock = self.start_server(ip, port)
        self.reciever_queue = queue.Queue()

        # Initialize the PiServoHat object
        self.servo = pi_servo_hat.PiServoHat()
        self.servo.restart()

       # Initialize the ToF sensor
        self.tof_sensor = qwiic.QwiicVL53L1X()
        if self.tof_sensor.sensor_init() is None:
            self.tof_sensor.start_ranging()
            print("ToF Sensor online!\n")
            time.sleep(0.005)

        
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

            print(self.rvr.get_battery_percentage(self.battery_percentage_handler, timeout=100))
            print("RVR initialized")
        except Exception as e:
            print(f"Error initializing RVR: {e}")

    def battery_percentage_handler(self, battery_percentage):
        self.jsonFile_to_send["battery_level"] = battery_percentage['percentage']

    def update_jsonFile_to_send(self):
        self.jsonFile_to_send["distance"] = self.tof_sensor.get_distance()
        self.rvr.get_battery_percentage(self.battery_percentage_handler)


    def init_camera(self):
        self.camera = cv2.VideoCapture(0)
        print("camera started")
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
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
            success, encoded_frame = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality])
            if not success:
                print("Error encoding frame")
                return None
            base64_frame = base64.b64encode(encoded_frame).decode('utf-8')
            return base64_frame
        else:
            print("Frame not found")
            return None

    def recieverMethod(self):
            print("reciever thread started")
             
            while not self.stopflag.is_set():
                time.sleep(self.DT)
                try:
                    data, self.addr = self.sock.recvfrom(4096)
                    data = data.decode("utf-8")
                    print(f"data recieved {data}")
                    try: 
                        json_data = json.loads(data)
                        self.reciever_queue.put((json_data))

                        if self.reciever_queue.qsize() >= 10:
                            self.reciever_queue.get_nowait()
                        
                    except ValueError:
                        print("Error: Value converting to json")
                    
                except OSError as e:
                    print(f"Socket error: {str(e)}")
                if self.stopflag.is_set():
                    break

                time.sleep(1/50)


    def moveServo(self,tilt,pan): 
        # Move the servo motors based on pan and tilt values
        if pan is not None:
            # Adjust the input values to be in the range of -90 to 90
            pan_input_adjusted = max(min(pan, 90), -90)
            pan_servo_position = int(pan_input_adjusted * (180 / 90) + 90)
            self.servo.move_servo_position(0, pan_servo_position, 180)  # pan is on pin 0
        
        if tilt is not None:

            tilt_input_adjusted = max(min(tilt, 90), -90)
      
            tilt_servo_position = int(tilt_input_adjusted * (180 / 90) + 90)
            self.servo.move_servo_position(1, tilt_servo_position, 180) 

    def moveRobot(self,speed_,heading_, message):
        if (self.tof_sensor.get_distance() < 500) and message == "drive":
            speedInput = 0
        if message == "start_video":
            self.jsonFile_to_send["videoRunning"] = True
        elif message == "stop_video":
            self.jsonFile_to_send["videoRunning"] = False
        elif message == "drive":
            self.rvr.drive_with_heading(speed = speed_, heading = heading_, flags=DriveFlagsBitmask.fast_turn.value)
        elif message == "drive_reverse":
            self.rvr.drive_with_heading(speed = speed_, heading = heading_, flags=DriveFlagsBitmask.drive_reverse.value)
        elif message =="dont_drive":
            self.rvr.drive_with_heading(speed = 0, heading = heading_, flags=DriveFlagsBitmask.none.value)

    def update_jsonFile_to_send(self):
        self.jsonFile_to_send["distance"] = self.tof_sensor.get_distance()
        self.rvr.get_battery_percentage(self.battery_percentage_handler)
        
    def run(self):
        self.reciever_thread.start()
        self.driver_thread.start()
        self.sending_thread.start()

    def driverMethod(self):
       
        speedInput = 0
        headingInput = 0
        panInput = None
        tiltInput = None
         
        print("driver thread started")

        while not self.stopflag.is_set():
            #print("driver thread running")
            self.keepAwake()
            self.tof_sensor.start_ranging()
            
            message = None

            if not self.reciever_queue.empty():
                #print("reciever queue not empty")
                self.jsonFile_recieved = self.reciever_queue.get(block=False)
                speedInput = self.jsonFile_recieved.get("speed")
                headingInput = self.jsonFile_recieved.get("heading")
                panInput = self.jsonFile_recieved.get("panPosition")
                tiltInput = self.jsonFile_recieved.get("tiltPosition")
                message = self.jsonFile_recieved.get("message")
            else:
                self.jsonFile_recieved["message"] = "no input"
                message = "no input"

            self.update_jsonFile_to_send()
            self.moveServo(tiltInput,panInput)
            self.moveRobot(speedInput,headingInput, message)


            if self.stopflag.is_set():
                break

            time.sleep(self.DT)

    def dump_and_send_json(self, json_data):
        jsonBytes = json.dumps(json_data).encode('utf-8')
        self.UDP_send(jsonBytes)
        #print(f"Sent {len(jsonBytes)} bytes")

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

                        self.dump_and_send_json(frame_packet)
                        self.dump_and_send_json(self.jsonFile_to_send)

            else:
                self.dump_and_send_json(self.jsonFile_to_send)


            time.sleep(self.DT)


    def UDP_send(self, packet):
        if self.addr is not None:
            try:
                self.sock.sendto(packet, self.addr)
                print(f"Sent {len(packet)} bytes")
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
        self.tof_sensor.stop_ranging()

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
