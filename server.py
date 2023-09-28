import picamera
import imutils
import numpy as np
import socket
import ffmpeg

def read_send(sock):
    camera = picamera.PiCamera()
    print("camera started")


    camera.resolution = (640,480)
    array = np.zeros((640, 480, 3), dtype=np.uint8)
    while True:
        frame = camera.capture(array, format='rgb')
        #frame = imutils.resize(frame, width = 640)
        frame = np.array(frame)
        compressed_frame = ffmpeg.input(frame).output('pipe:', format='png').run(pipe_stdout=True).stdout.read()
        

        try:
            print("starting send")
            sock.sendto(compressed_frame, ("127.0.0.1", 5006))
            print("frame sent")
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

    