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

def init_rvr():
    rvr = SpheroRvrObserver()
    rvr.on_did_sleep_notify(handler=keepAwake)

    print("robot object created")

    try:
        print("waking robot")
        rvr.wake()
        print("robot awake")
        time.sleep(1)
        print("setting leds")
        rvr.set_all_leds(
            led_group=RvrLedGroups.all_lights.value,
            led_brightness_values=[color for _ in range(10) for color in [0, 255, 0]]
        )
        print("leds set")
        rvr.reset_yaw()
        print("yaw reset")
        def battery_percentage_handler(percentage):
            print(f"Battery Percentage: {percentage}%")
        rvr.get_battery_percentage(battery_percentage_handler, timeout=100)
        print("RVR initialized")
    except Exception as e:
        print(f"Error initializing RVR: {e}")
    return rvr

def init_camera():
    camera = cv2.VideoCapture(0)
    print("camera started")
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    print("capture frame resized")
    return camera

def capture_and_compress(camera):
    ret,frame = camera.read()
    if ret:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, encoded_frame = cv2.imencode('.jpg', frame)
        if encoded_frame is None:
            print("Error encoding frame")
            return None
        return encoded_frame.tobytes()
    else:
        print("frame not found")
        return None
    
def recv_data(sock,queue, stopflag):
    global addr
    while not stopflag.is_set():
        try:
            data,addr = sock.recvfrom(4096)
            data = data.decode("utf-8")
            print(f"data recieved {data}")
            try: 
                json_data = json.loads(data)
                if queue.qsize() >= 5:
                    # This will remove the oldest item from the queue
                    queue.get_nowait()
                
                queue.put((json_data, addr))
            except ValueError:
                print("Error: Value converting to json")
            
        except OSError as e:
            print(f"Socket error: {str(e)}")
        if stopflag.is_set():
            break

def handle_connection(camera, receiveQueue, sendQueue, sock, stopflag, rvr):
    startVideo = False
    speedInput = 0
    jsonString = create_json_string(0,0,0,0, False)
    while not stopflag.is_set():
        keepAwake(rvr)
        time.sleep(1/60)
        message = None
        try:
            data,addr = receiveQueue.get(block=False)

        except queue.Empty:
            #print("Queue empty")
            data = {"message": "no input"}
            message = data.get("message")
        if message != "no input":
            speedInput = data.get("speed")
            headingInput = data.get("heading")
            message = data.get("msg")
            print(f"Message: {message}, Speed: {speedInput}, Heading: {headingInput}")


        if message == "video":
            startVideo = True
        elif message == "stop_video":
            startVideo = False
        elif message == "drive":
            rvr.drive_with_heading(speed = speedInput, heading = headingInput, flags=DriveFlagsBitmask.none.value)
        elif message == "drive_reverse":
            rvr.drive_with_heading(speed = speedInput, heading = headingInput, flags=DriveFlagsBitmask.drive_reverse.value)
        elif message =="dont_drive":
            rvr.drive_with_heading(speed = 0, heading = headingInput, flags=DriveFlagsBitmask.none.value)

        if startVideo == True:
            jsonString["video"] = True
            sending_queue.put(jsonString)
        else:
            jsonString["video"] = False
            sending_queue.put(jsonString)


        if stopflag.is_set():
            break

def sendingThread(sock, myqueue, stopflag):
    global addr
    video = False
    sleepTime = 1/60
    while not stopflag.is_set():
        while video:
            jsonString = myqueue.get()
            video = jsonString.get("video")
            compressed_frame = capture_and_compress(camera)
            try:
                jsonString = edit_json_string(jsonString, "frame", compressed_frame)
                jsonBytes = encode_json_file(jsonString)
                UDP_send(sock, jsonBytes, addr)
            except queue.Empty:
                print("Queue empty")

            time.sleep(sleepTime)

        if not video:
            jsonString = myqueue.get()
            video = jsonString.get("video") #this is a bool, check if we want to send video
            jsonBytes = encode_json_file(jsonString)
            UDP_send(sock, jsonBytes, addr)
            time.sleep(sleepTime)

def create_json_string(speed, heading,frame, message):
    #convert bytes to string
    frame = base64.b64encode(frame).decode('utf-8')
    jsonFile = {"message": message, "cameraPosX": speed, "heading": heading, "frame": frame, "video": True}
    return jsonFile

def encode_json_file(jsonFile):
    jsonBytes = json.dumps(jsonFile).encode('utf-8')
    return jsonBytes

def edit_json_string(jsonFile, varToChange, value):
    if varToChange == "frame":
        value = base64.b64encode(value).decode('utf-8')
        jsonFile[varToChange] = value
    else:
        jsonFile[varToChange] = value
    return jsonFile


def UDP_send(sock, string, client):
    try:
        sock.sendto(string, client)
        print(f"{sys.getsizeof(string)} bytes sent")
    except socket.error as e:
        frame_size = sys.getsizeof(string) 
        print("Frame size:", frame_size)
        print(e)
        return False
    return True


def start_server(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
    sock.bind((ip, port))
    print("Server started")
    return sock
def cleanup(camera, SOCK, rvr):
    camera.release()
    SOCK.close()
    rvr.close()

def signal_handler(_):
    print('You pressed Ctrl+C!')
    stopflag.set()
    cleanup(camera, SOCK, rvr)
    reciever_thread.join()
    driver_thread.join()
    sendingThread.join()
def keepAwake(rvr):
    #print("RVR is trying to sleep, waking up...")
    rvr.wake()

if __name__ == "__main__":
    MAX_UDP_PACKET_SIZE = 65536
    SOCK = start_server("10.25.46.172", 12395)
    print(f"server touple is {SOCK.getsockname()}")
    camera = init_camera()
    print("camera initialized")
    rvr = init_rvr()

    reciever_queue = queue.Queue()
    sending_queue = queue.Queue()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    reciever_thread = threading.Thread(target=recv_data, args=(SOCK,reciever_queue, stopflag))
    sendingThread = threading.Thread(target=sendingThread, args=(SOCK,sending_queue, stopflag))
    driver_thread = threading.Thread(target=handle_connection, args=(camera, reciever_queue, sending_queue, SOCK,stopflag, rvr))

    try:
        reciever_thread.start()
        driver_thread.start()
        sendingThread.start()
    except KeyboardInterrupt:
        print("Keyboard interrupt")
    finally:
        reciever_thread.join()
        driver_thread.join()
        sendingThread.join()
        cleanup(camera, SOCK, rvr)
        