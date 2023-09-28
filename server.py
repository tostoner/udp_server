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
        frame = camera.capture(array, format='png', resize = (1920,1280))
        #frame = imutils.resize(frame, width = 640)
        frame = np.array(frame)
        grayscale_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        compressed_frame = ffmpeg.input(grayscale_frame).output('pipe:', format='png').capture()
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

    