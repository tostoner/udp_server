import cv2
import numpy as np
import socket
import sys
import threading
import queue
import time
import signal
import sys
import os

sys.path.append(os.path.expanduser('/home/micro/sphero-sdk-raspberrypi-python'))
try:
    from sphero_sdk import SpheroRvrObserver
    from sphero_sdk import RawMotorModesEnum
    from sphero_sdk import Colors
    from sphero_sdk import RvrLedGroups
    from sphero_sdk import DriveFlagsBitmask
    from sphero_sdk import DriveControlObserver

except ImportError:
    raise ImportError('Cannot import from sphero_sdk')

stopflag = threading.Event()

def init_rvr():
    rvr = SpheroRvrObserver()
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
        print(f"Battery percentage. {rvr.get_battery_percentage(battery_percentage_handler, timeout=10)}%")

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

    while not stopflag.is_set():
        try:
            data,addr = sock.recvfrom(4096)
            data = data.decode("utf-8")
            print(f"data recieved {data}")
            queue.put((data, addr))
        except OSError as e:
            print(f"Socket error: {str(e)}")
            break
        if stopflag.is_set():
            break

def handle_connection(camera, myqueue, sock, stopflag, rvr):
    startVideo = False
    heading = 0
    speedInput = 0

    while not stopflag.is_set():
        time.sleep(0.01)
        try:
            data,addr = myqueue.get(block=False)

        except queue.Empty:
            print("Queue empty")
            data = "no input"

        parts = data.split(",", 1)
        if len(parts) > 1:
            try:
                value = int(parts[1])
                data = parts[0]
            except:
                print("error value converting to int")
                continue

        if data == "video":
            startVideo = True
        elif data == "+":
            print(" recieved gas")
            speedInput = speedInput + value
            if speed > 255:
                speed = 255
        elif data == "-":
            speedInput = speedInput - value
            if speed < 0:
                speed = 0
        elif data == "stop_video":
            startVideo = False
        elif data == "forward":
            print("forward function")
            rvr.drive_with_heading(speed = speedInput, heading = heading, flags=DriveFlagsBitmask.none.value)
        elif data == "backward":
            print("backward function")
            rvr.drive_with_heading(speed = speedInput, heading = heading , flags=DriveFlagsBitmask.drive_reverse.value)
        elif data == "left":
            heading = (heading - 5) % 360
        elif data == "right":
            heading = (heading + 5) % 360
        print(f" heading is {heading}")

        if startVideo == True:
            compressed_frame = capture_and_compress(camera)
            if compressed_frame:#Kan bytte til switch case fordi det er rasksare
                send_frame(sock, compressed_frame, addr)
            if not compressed_frame:
                print("Error capturing frame")
        
        else:
            if data is not None:
                print(f"recieved from client: {data}")
        if stopflag.is_set():
            break

def send_frame(sock, frame, client):
    try:
        sock.sendto(frame, client)
        print(f"{sys.getsizeof(frame)} bytes sent")
    except socket.error as e:
        frame_size = sys.getsizeof(frame) 
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

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    stopflag.set()


if __name__ == "__main__":
    MAX_UDP_PACKET_SIZE = 65536
    SOCK = start_server("10.25.46.172", 12395)
    print(f"server touple is {SOCK.getsockname()}")
    #sock = start_server("10.25.46.172", 12395)#må ditte være samme som raspi eller kan den være random?
    camera = init_camera()
    print("camera initialized")
    rvr = init_rvr()


    q = queue.Queue()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


    reciever_thread = threading.Thread(target=recv_data, args=(SOCK,q, stopflag))
    handler_thread = threading.Thread(target=handle_connection, args=(camera, q, SOCK,stopflag, rvr))

    try:
        reciever_thread.start()
        handler_thread.start()
    except KeyboardInterrupt:
        print("Keyboard interrupt") #SIGNALS VIRKA IKKJE PÅ WINDOWS :( KANSKJE PÅ RASPI? :)
        signal_handler()
    finally:
        reciever_thread.join()
        handler_thread.join()
        cleanup(camera, SOCK, rvr)