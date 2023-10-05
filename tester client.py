import cv2
import socket
import numpy as np


def start_client(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("10.22.179.34", 12346))#ip til client maskina?
    print("Client started")
    return sock



def receive_frames(socket, server_touple):
    while True:
        
        msg = "give me video"
        socket.sendto(msg.encode("utf-8"), server_touple)
        print("Waiting for frame")

        data, addr = socket.recvfrom(65507)
        print("Frame received1")
        frame = cv2.imdecode(np.frombuffer(
            data, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        print("Frame received")
        if frame is not None:
            cv2.imshow('Received Frame', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            print("Error decoding frame")

    cv2.destroyAllWindows()
    socket.close()


if __name__ == "__main__":
    IP_ADDRESS = "10.25.46.172"#samme som server socket
    PORT = 12395 #samme som server socket

    client_sock = start_client(IP_ADDRESS, PORT)
    receive_frames(client_sock, (IP_ADDRESS, PORT))
