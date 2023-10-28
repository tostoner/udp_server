import cv2
import numpy as np
import socket
import signal
import sys
import os

sys.path.append(os.path.expanduser('/home/micro/sphero-sdk-raspberrypi-python'))
try:
    import asyncio
    from sphero_sdk import SpheroRvrTargets
    from sphero_sdk import SpheroRvrAsync
    from sphero_sdk import SerialAsyncDal
    from sphero_sdk import RvrFwCheckAsync
    from sphero_sdk import LedControlAsync
    from sphero_sdk import DriveControlAsync
    from sphero_sdk import InfraredControlAsync
    from sphero_sdk import SensorControlAsync
    import os
    import logging
    from sphero_sdk import SpheroRvrTargets
    from sphero_sdk.common.firmware.cms_fw_check_base import CmsFwCheckBase


except ImportError:
    raise ImportError('Cannot import from sphero_sdk')






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
    while not stopflag:
        try:
            data, addr = sock.recvfrom(4096)
            data = data.decode("utf-8")
            print(f"data received {data}")
            await queue.put((data, addr))
        except OSError as e:
            print(f"Socket error: {str(e)}")
            break


async def handle_inputs(camera, queue, sock, stopflag, rvr):
    startVideo = False
    heading = 0
    DRIVE_REVERSE_FLAG = 0b00000001
    BOOST_FLAG = 0b00000010
    FAST_TURN_MODE_FLAG = 0b00000100

    while not stopflag:
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

async def main(rvr):
    print("main function started")




    print("Robot object created")
    await asyncio.sleep(1)
    print("loop created")
    SOCK = await start_server("10.25.46.172", 12395)
    print(f"server tuple is {SOCK.getsockname()}")
    camera = await init_camera()

    print("camera initialized")

    try:
        print("Waking robot")
        await rvr.wake()
        print("Robot awake. Getting battery percentage")

        # Extend the timeout for debugging purposes
        battery_percentage = await rvr.get_battery_percentage(timeout=10)
        print(f"Battery at {battery_percentage}%")

        voltage = await rvr.get_battery_voltage_in_volts()
        print(f"Voltage is {voltage}")

        print("Getting main application version") 
        main_app_version = await rvr.get_main_application_version(timeout=10)
        print(f"Main application version: {main_app_version}")

        print("Setting LEDs")
        await rvr.set_all_leds(
            led_group=RvrLedGroups.all_lights.value,
            led_brightness_values=[color for _ in range(10) for color in [0, 255, 0]]
        )
        print("LEDs set")

        await rvr.reset_yaw()
        print("Yaw reset")

        print("RVR initialized")
    except Exception as e:
        print(f"Error initializing RVR: {e}")
    
    stopflag = False
    print("robot object created")

    await asyncio.sleep(5)
    q = asyncio.Queue()

    reciever_task = asyncio.create_task(recv_data(SOCK, q, stopflag))
    handler_task = asyncio.create_task(handle_inputs(camera, q, SOCK, stopflag, rvr))
    await asyncio.gather(reciever_task, handler_task)

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')

if __name__ == "__main__":
    print("main function started")
    loop = asyncio.get_event_loop()
    loop.set_debug(True)

    print("loop created")

    dal = SerialAsyncDal(loop)
    print("dal created")
    
    rvr = SpheroRvrAsync(dal=dal)
    print("Robot object created")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    asyncio.run(main(rvr))
