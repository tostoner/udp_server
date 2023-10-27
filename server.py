import cv2
import numpy as np
import socket
import threading
import queue
import time
import signal
import sys
import os

sys.path.append(os.path.expanduser('/home/micro/sphero-sdk-raspberrypi-python'))
try:
    import asyncio
    import logging.config

    from sphero_sdk.asyncio.client.toys.sphero_rvr_async import SpheroRvrAsync
    from sphero_sdk import SpheroRvrAsync
    from sphero_sdk import SerialAsyncDal

except ImportError:
    raise ImportError('Cannot import from sphero_sdk')

stopflag = threading.Event()
loop = asyncio.get_event_loop()

async def init_rvr(loop):
    rvr = SpheroRvrAsync(dal=SerialAsyncDal(loop))
    print("robot object created")

    try:
        print("waking robot")
        await rvr.wake()
        print("robot awake. Getting battery percentage")
        battery_percentage = await rvr.get_battery_percentage()
        print(f"Battery at {battery_percentage}%")
        voltage = await rvr.get_battery_voltage_in_volts()
        print(f"Voltage is {voltage}")
        print("getting main application version") 
        print("setting leds")
        await rvr.set_all_leds(
            led_group=RvrLedGroups.all_lights.value,
            led_brightness_values=[color for _ in range(10) for color in [0, 255, 0]]
        )
        print("leds set")
        await rvr.reset_yaw()
        print("yaw reset")
        print("RVR initialized")
    except Exception as e:
        print(f"Error initializing RVR: {e}")
    return rvr

async def init_camera():
    camera = cv2.VideoCapture(0)
    print("camera started")
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    print("capture frame resized")
    return camera

async def capture_and_compress(camera):
    ret, frame = camera.read()
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

async def recv_data(sock, queue, stopflag):
    while not stopflag.is_set():
        try:
            data, addr = sock.recvfrom(4096)
            data = data.decode("utf-8")
            print(f"data received {data}")
            await queue.put((data, addr))
        except OSError as e:
            print(f"Socket error: {str(e)}")
            break

async def handle_connection(camera, queue, sock, stopflag, rvr):
    startVideo = False
    heading = 0
    DRIVE_REVERSE_FLAG = 0b00000001
    BOOST_FLAG = 0b00000010
    FAST_TURN_MODE_FLAG = 0b00000100

    while not stopflag.is_set():
        try:
            data, addr = await queue.get()
            print(f"received from client: {data}")
            if data == "video":
                startVideo = True
            if data == "stop_video":
                startVideo = False
            if data == "forward":
                print("forward function")
                print(f"heading is {heading}")
                await rvr.drive_with_heading(speed = 20, heading = heading, flags = 0)
            if data == "backward":
                print("backward function")
                await rvr.drive_with_heading(speed = 20, heading = heading , flags = DRIVE_REVERSE_FLAG)
            if data == "left":
                print("left function")
                print(f"heading is {heading}")
                heading = heading - 5
            if data == "right":
                heading = heading + 5
            print(f" heading is {heading}")
        except asyncio.QueueEmpty:
            print("Queue empty")

        if startVideo:
            compressed_frame = await capture_and_compress(camera)
            if compressed_frame:
                await send_frame(sock, compressed_frame, addr)
            else:
                print("Error capturing frame")

async def send_frame(sock, frame, client):
    try:
        sock.sendto(frame, client)
        print(f"{sys.getsizeof(frame)} bytes sent")
    except socket.error as e:
        frame_size = sys.getsizeof(frame)
        print("Frame size:", frame_size)
        print(e)
        return False
    return True

async def start_server(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))
    print("Server started")
    return sock

async def main():
    SOCK = await start_server("10.25.46.172", 12395)
    print(f"server tuple is {SOCK.getsockname()}")
    camera = await init_camera()
    print("camera initialized")
    rvr = await init_rvr(asyncio.get_running_loop())
    q = asyncio.Queue()
    reciever_task = asyncio.create_task(recv_data(SOCK, q, stopflag))
    handler_task = asyncio.create_task(handle_connection(camera, q, SOCK, stopflag, rvr))
    await asyncio.gather(reciever_task, handler_task)

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    stopflag.set()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    asyncio.run(main())