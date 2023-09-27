import picamera
import imutils
import numpy as np
import socket
import ffmpeg

MAX_UDP_PACKET_SIZE = 65536


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

sock.bind("0.0.0.0", 5006)

camera = picamera.PiCamera()


camera.resolution = (1920,1080)
while True:
    frame = camera.capture_array()
    frame = imutils.resize(frame, width = 640)
    frame = np.array(frame)
    compressed_frame = ffmpeg.input(frame).output('pipe:', format='png').run(pipe_stdout=True).stdout.read()
    parts = np.split(compressed_frame, 3)
    for i, part in enumerate(parts):
        parts[i] = (i,part)

        try:
            sock.sendto(parts[i].buffer(), ("127.0.0.1", 5006))
        except socket.error as e:
            print(e)
            break

sock.close()