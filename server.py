import picamera
import imutils
import numpy as np
import socket
import ffmpeg
import cv2

def read_send(sock):
    camera = picamera.PiCamera()
    print("camera started")


    camera.resolution = (1920,1280)
    array = np.zeros((1920,1280), dtype=np.uint8)
    while True:
        print("1")
        camera.capture(array, format='jpeg', resize = (320,240))
        #frame = imutils.resize(frame, width = 640)
        print("2")
        frame = np.array(array)
        print("3")

        grayscale_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        print("4")

        compressed_frame = ffmpeg.input(grayscale_frame).output('pipe:', format='jpeg').capture()
        print(f"sending frame of len: {len(compressed_frame)}")
        

        try:
            print("starting send")
            sock.sendto(compressed_frame, ("127.0.0.1", 5006))
            print(f"frame sent. size: {len(compressed_frame)}")
        except socket.error as e:
            print(e)
            break
    sock.close()

def start_server(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))
    return sock


if __name__ == "__main__":
    MAX_UDP_PACKET_SIZE = 65536
    sock = start_server("0.0.0.0", 5006)
    read_send(sock)
#
#micro@rasp:~/udp_server $ python3 server.py
#camera started
#1
#2
#3
#OpenCV Error: Assertion failed (scn == 3 || scn == 4) in cvtColor, file /build/opencv-L65chJ/opencv-3.2.0+dfsg/modules/imgproc/src/color.cpp, line 9748
#Traceback (most recent call last):
#  File "server.py", line 48, in <module>
#    read_send(sock)
#  File "server.py", line 23, in read_send
#    grayscale_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#cv2.error: /build/opencv










