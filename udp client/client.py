import socket
import numpy as np
import cv2
import threading
import queue

MAX_UDP_PACKET_SIZE = 65536

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("127.0.0.1", 5006))

# Initialize a buffer to store the received data.
parts = {None, None, None}
data_queue = queue.Queue()

def recieve_data(max_udp_packet_size):
    print(f"looking for data...")
    while True:

        data, addr = sock.recvfrom(max_udp_packet_size)
        if data:
            print("found data")
        if data[0] == 0:
            parts[0] = data[1]
        if data[0] == 1:
            parts[1] =data[1]
        if data[0] == 2:
            parts[2] = data[1]
        data_queue.put(parts.copy())

def combine_and_show():
    print(f"looking for data to combine...")

    while True:
        parts = data_queue.get()
        frame = np.concatenate(parts)
        cv2.imshow("Frame", frame)
        cv2.waitKey(1)


# Receive datagrams from the server.
if __name__ == "__main__":
    try:
        recieve_thread = threading.Thread(target=recieve_data, args=(MAX_UDP_PACKET_SIZE,))
        combine_and_show_thread = threading.Thread(target = combine_and_show)
        recieve_thread.start()
        combine_and_show_thread.start()  

        recieve_thread.join()
        combine_and_show_thread.join()

    finally:
        exit_flag = True
        cv2.destroyAllWindows()

        sock.close()
