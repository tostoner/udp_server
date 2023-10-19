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

sys.path.append('~/sphero-sdk-raspberrypi-python')
from sphero_sdk import SpheroRvrObserver
from sphero_sdk import RawMotorModesEnum

stopflag = threading.Event()


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
def drive_forward(rvr):
    rvr.raw_motors(
            left_mode=RawMotorModesEnum.forward.value,
            left_duty_cycle=128,  # Valid duty cycle range is 0-255
            right_mode=RawMotorModesEnum.forward.value,
            right_duty_cycle=128  # Valid duty cycle range is 0-255
        )

    # Delay to allow RVR to drive
    time.sleep(1)

    rvr.raw_motors(
        left_mode=RawMotorModesEnum.reverse.value,
        left_duty_cycle=64,  # Valid duty cycle range is 0-255
        right_mode=RawMotorModesEnum.reverse.value,
        right_duty_cycle=64  # Valid duty cycle range is 0-255
    )

    # Delay to allow RVR to drive
    time.sleep(1)

    rvr.raw_motors(
        left_mode=RawMotorModesEnum.reverse.value,
        left_duty_cycle=128,  # Valid duty cycle range is 0-255
        right_mode=RawMotorModesEnum.forward.value,
        right_duty_cycle=128  # Valid duty cycle range is 0-255
    )

    # Delay to allow RVR to drive
    time.sleep(1)

    rvr.raw_motors(
        left_mode=RawMotorModesEnum.forward.value,
        left_duty_cycle=128,  # Valid duty cycle range is 0-255
        right_mode=RawMotorModesEnum.forward.value,
        right_duty_cycle=128  # Valid duty cycle range is 0-255
    )

    # Delay to allow RVR to drive
    time.sleep(1)

    rvr.raw_motors(
        left_mode=RawMotorModesEnum.off.value,
        left_duty_cycle=0,  # Valid duty cycle range is 0-255
        right_mode=RawMotorModesEnum.off.value,
        right_duty_cycle=0  # Valid duty cycle range is 0-255
    )

def handle_connection(camera, myqueue, sock, stopflag):
    startVideo = False
    rvr = SpheroRvrObserver()
    try:
        rvr.wake()
        time.sleep(2)
        rvr.led_control.set_all_leds_rgb(red=0, green=255, blue=0)
        rvr.reset_yaw()
        print("RVR initialized")
    except Exception as e:
        print(f"Error initializing RVR: {e}")

    while not stopflag.is_set():
        try:
            data,addr = myqueue.get(timeout=1)
        except queue.Empty:
            print("Queue empty")
            data = "no input"

        if data == "video":
            startVideo = True
        if data == "stop_video":
            startVideo = False
        if data == "forward":
            drive_forward(rvr)

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
    sock.bind((ip, port))
    print("Server started")
    return sock

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    stopflag.set()

if __name__ == "__main__":
    MAX_UDP_PACKET_SIZE = 65536
    SOCK = start_server("10.25.46.172", 12395)
    print(f"server touple is {SOCK.getsockname()}")
    #sock = start_server("10.25.46.172", 12395)#må ditte være samme som raspi eller kan den være random?
    camera = init_camera()

    q = queue.Queue()

    

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


    reciever_thread = threading.Thread(target=recv_data, args=(SOCK,q, stopflag))
    handler_thread = threading.Thread(target=handle_connection, args=(camera, q, SOCK,stopflag))

    

    try:
        reciever_thread.start()
        handler_thread.start()


        reciever_thread.join()
        handler_thread.join()
    except KeyboardInterrupt:
        print("Keyboard interrupt") #SIGNALS VIRKA IKKJE PÅ WINDOWS :( KANSKJE PÅ RASPI? :)
    finally:
        camera.release()
        SOCK.close()
        rvr.close()


            
    