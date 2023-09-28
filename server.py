import picamera
import numpy as np
import socket
import subprocess

def read_send(sock):
    camera = picamera.PiCamera()
    print("camera started")

    camera.resolution = (320, 240)
    array = np.empty((640, 480, 3), dtype=np.uint8)
    while True:
        camera.capture(array, format='rgb')
        frame = array.tobytes()
        
        try:
            print("starting send")
            ffmpeg_process = subprocess.Popen(
                [
                    "ffmpeg",
                    "-f", "rawvideo",
                    "-s", "640x480",
                    "-pix_fmt", "rgb24",
                    "-i", "-",
                    "-f", "image2pipe",
                    "-vcodec", "png",
                    "-"
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            compressed_frame, _ = ffmpeg_process.communicate(input=frame)
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
