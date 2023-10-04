import cv2
import imutils
import numpy as np
import socket
import ffmpeg
import sys
import cv2
import threading

def capture_send(sock, dest):
    camera = cv2.VideoCapture(0)
    print("camera started")
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    print("capture frame resized")

    while True:
        #frame = imutils.resize(frame, width = 640)
        ret,frame = camera.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, encoded_frame = cv2.imencode('.jpg', frame)
            if encoded_frame is None:
                print("Error encoding frame")
                continue
            
        if not ret:
            print("frame not found")
            continue

        try:
            sock.sendto(encoded_frame.tobytes(), dest)
            print(f"{sys.getsizeof(encoded_frame.tobytes())} bytes sent")

            
        except socket.error as e:
            frame_size = sys.getsizeof(encoded_frame.tobytes())  # Get the size of the encoded frame in bytes
            print("Frame size:", frame_size)
            print(e)
            break
    sock.close()

def start_server(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))
    print("Server started")
    return sock


if __name__ == "__main__":
    MAX_UDP_PACKET_SIZE = 65536
    sock = start_server("10.25.46.172", 49154)
    capture_send(sock, ('239.9.9.11', 49155))











