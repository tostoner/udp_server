import cv2
import numpy as np
import socket
import sys
import threading

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
    
def recv_data(sock):
    data,addr = sock.recvfrom(4096)
    print(f"recieved from client: {data}")
    data = data.decode("utf-8")
    return data,addr


def send_frame(sock, frame, clients):
    try:
        sock.sendto(frame, clients[0])
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


if __name__ == "__main__":
    MAX_UDP_PACKET_SIZE = 65536
    sock = start_server("10.25.46.172", 12395)#må ditte være samme som raspi eller kan den være random?
    camera = init_camera()

    while True:
        data,addr = recv_data(sock)
        print(f"recieved from client: {data}")

        if data == "video":
            while data!= "stop video":
                compressed_frame = capture_and_compress(camera)
                if compressed_frame:

                    send_frame(sock, compressed_frame, addr)
                if not compressed_frame:
                    print("Error capturing frame")

            
    
