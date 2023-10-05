import cv2
import socket
import numpy as np

def start_client(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))  # Uncomment this line
    print("Client started")
    return sock

def receive_frames(sock):
    while True:
        print("Waiting for frame")
        data, addr = sock.recvfrom(65565) 
        print("Frame received1")
        frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        print("Frame received")
        if frame is not None:
            cv2.imshow('Received Frame', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            print("Error decoding frame")

    cv2.destroyAllWindows() 
    sock.close() 

if __name__ == "__main__":
    IP_ADDRESS = "10.22.179.34"
    PORT = 49155

    client_sock = start_client(IP_ADDRESS, PORT)
    receive_frames(client_sock)
