import cv2

import numpy as np
import socket

import cv2
import socket
import sys

def capture_send(sock, dest):
    camera = cv2.VideoCapture(0)
    print("camera started")
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    print("capture frame resized")

    error_count = 0
    while True:
        ret, frame = camera.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, encoded_frame = cv2.imencode('.jpg', frame)
            if encoded_frame is None:
                print("Error encoding frame")
                error_count += 1
                if error_count > 5:  
                    break
                continue
            
        if not ret:
            print("frame not found")
            continue

        data = encoded_frame.tobytes()
        if sys.getsizeof(data) > MAX_UDP_PACKET_SIZE:
            print("Encoded frame size exceeds maximum UDP packet size")
            continue

        try:
            sock.sendto(data, dest)
            print(f"{sys.getsizeof(data)} bytes sent")
        except socket.error as e:
            print("Frame size:", sys.getsizeof(data))
            print(e)
            break

    camera.release()  # Release the camera resource
    sock.close()

def start_server(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))
    print("Server started")
    return sock


if __name__ == "__main__":
    MAX_UDP_PACKET_SIZE = 65507
    IP_ADDRESS = "10.25.46.172"
    PORT = 49154
    DEST_IP_ADDRESS = '10.22.179.34'
    DEST_PORT = 49155

    sock = start_server(IP_ADDRESS, PORT)
    capture_send(sock, (DEST_IP_ADDRESS, DEST_PORT))












