import sys
import time
import requests
from datetime import datetime
import pyzed.sl as sl
import signal

def log_message(server_url, message):
    try:
        requests.post(server_url, json={"log": message})
    except Exception as e:
        print(f"Failed to send log: {e}")

def signal_handler(sig, frame):
    if sig == signal.SIGUSR1:
        stop_recording()

def start_recording():
    current_datetime = datetime.now()
    record_path = '/home/xavier/Documents/Records/SVO/' + str(current_datetime.strftime("%Y-%m-%d-%H-%M-%S")) + ".svo"

    recording_param = sl.RecordingParameters(record_path, sl.SVO_COMPRESSION_MODE.H264)
    err = zed.enable_recording(recording_param)
    print("Recording")

    try:
        if err == sl.ERROR_CODE.SUCCESS:
            log_message(log_url, "RECORDING STARTED \n")
	    # Send a status update to the server
            requests.post(server_url, json={"status": "Recording"})
        else:
            log_message(log_url, str(repr(status)) + "\n")
	    # Send a status update to the server
            requests.post(server_url, json={"status": "Recording Error"})
    except Exception as e:
        log_message(log_url, f"Error: {e}")
        requests.post(server_url, json={"status": "Error"})

    if err != sl.ERROR_CODE.SUCCESS:
        print(repr(status))
        exit(1)

def stop_recording():
    zed.disable_recording()
    print("Stopping Recording")

    try:
        log_message(log_url, "RECORDING STOPED \n")
        requests.post(server_url, json={"status": "Record Stop"})
    except Exception as e:
        log_message(log_url, f"Error: {e}")
        requests.post(server_url, json={"status": "Error"})
    zed.close()
    sys.exit(0)


if __name__ == "__main__":
    server_url = "http://158.196.240.211:8000/report_status"
    log_url = "http://158.196.240.211:8000/report_log"
    start_time = time.time()
    signal.signal(signal.SIGUSR1, signal_handler)

    zed = sl.Camera()

    try:
        log_message(log_url, "Camera Initialization \n")
        # Send a status update to the server
        requests.post(server_url, json={"status": "Starting"})
    except Exception as e:
        log_message(log_url, f"Error: {e}")
        requests.post(server_url, json={"status": "Init Error"})

    init_params = sl.InitParameters()
    init_params.camera_resolution = sl.RESOLUTION.HD720
    init_params.camera_fps = 30
    init_params.coordinate_units = sl.UNIT.METER
    init_params.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP
    init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE
    init_params.depth_maximum_distance = 20

    status = zed.open(init_params)

    try:
        if status == sl.ERROR_CODE.SUCCESS:
            log_message(log_url, "Camera Initialized \n")
            # Send a status update to the server
            requests.post(server_url, json={"status": "Initialized"})
        else:
            log_message(log_url, str(repr(status)) + "\n")
            # Send a status update to the server
            requests.post(server_url, json={"status": "Camera Error"})
    except Exception as e:
        log_message(log_url, f"Error: {e}")
        requests.post(server_url, json={"status": "Error"})

    if status != sl.ERROR_CODE.SUCCESS:
        print(repr(status))
        exit()

    runtime = sl.RuntimeParameters()
    
    start_recording()
    
    print("SVO is Recording, use Ctrl-C to stop.")
    frames_recorded = 0

    while True:
        if zed.grab(runtime) == sl.ERROR_CODE.SUCCESS:
            try:
                actual_time = round(time.time() - start_time)
                log_message(log_url, "Working for: " + str(actual_time) + " seconds\n")
                # Send a status update to the server
                requests.post(server_url, json={"status": "Recording"})
            except Exception as e:
                log_message(log_url, f"Error: {e}")
                requests.post(server_url, json={"status": "Failed"})
