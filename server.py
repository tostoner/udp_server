import cv2
import numpy as np
import socket
import ffmpeg
import sys
import threading

def capture_send(sock):
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    print("camera started")
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    print("capture frame resized")

    while True:
        data,addr = sock.recvfrom(4096)
        print(f"recieved from client: {data}")

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
            sock.sendto(encoded_frame.tobytes(), addr)
            print(f"{sys.getsizeof(encoded_frame.tobytes())} bytes sent")

            
        except socket.error as e:
            frame_size = sys.getsizeof(encoded_frame.tobytes()) 
            print("Frame size:", frame_size)
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
    MAX_UDP_PACKET_SIZE = 65536
    sock = start_server("10.25.46.172", 12395)#må ditte være samme som raspi eller kan den være random?
    capture_send(sock)
