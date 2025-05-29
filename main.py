import sys
import os
import numpy as np
import cv2
import pyzed.sl as sl
from ultralytics import YOLO
import ExtendedObjectsProvider as ObjectProvider

import cv_viewer.tracking_viewer as cv_viewer
import classification
import ZoneCalculation
from batch_system_handler import *

import signal
import requests
import time
from datetime import datetime
#import sendingMQTT

sys.path.append(os.path.expanduser('~/unitree_legged_sdk/lib/python/arm64'))
#import robot_interface as go1_sdk
#import can


def log_message(server_url, message):
    try:
        requests.post(server_url, json={"log": message})
    except Exception as e:
        print(f"Failed to send log: {e}")


def start_recording():
    global is_recording
    current_datetime = datetime.now()
    record_path = '/home/xavier/Documents/Records/SVO/' + str(current_datetime.strftime("%Y-%m-%d-%H-%M-%S")) + ".svo"
    if not is_recording:
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
        else:
            is_recording = True


def stop_recording():
    global is_recording
    if is_recording:
        zed.disable_recording()
        print("Stopping Recording")

        try:
            log_message(log_url, "RECORDING STOPED \n")
        except Exception as e:
            log_message(log_url, f"Error: {e}")
            requests.post(server_url, json={"status": "Error"})

        is_recording = False


def signal_handler(sig, frame):
    if sig == signal.SIGUSR1:
        start_recording()
    elif sig == signal.SIGUSR2:
        stop_recording()


# Odeslání CAN zprávy
def send_can_message(bus, can_id, data):
    msg = can.Message(arbitration_id=can_id, data=data, is_extended_id=False)
    try:
        bus.send(msg)
        print(f"Sent CAN message: ID={hex(can_id)}, Data={data.hex()}")
    except can.CanError:
        print("CAN message send failed")


##
# Variable to enable/disable the batch option in Object Detection module
# Batching system allows to reconstruct trajectories from the object detection module by adding Re-Identification / Appareance matching.
# For example, if an object is not seen during some time, it can be re-ID to a previous ID if the matching score is high enough
# Use with caution if image retention is activated (See batch_system_handler.py) :
#   --> Images will only appear if an object is detected since the batching system is based on OD detection.
USE_BATCHING = False

if __name__ == "__main__":

    HIGHLEVEL = 0xee
    LOWLEVEL = 0xff

    # ----------PARAMS------------------------------------
    server_enabled = False
    UnitreeGo1 = False
    AgileX_scoutMINI = False

    is_playback = False  # Defines if an SVO is used
    is_classificator = True
    yolo_model = "best.pt"
    is_recording = False

    # ----------------------------------------------------

    if UnitreeGo1:
        udp = go1_sdk.UDP(HIGHLEVEL, 8080, "192.168.123.161", 8082)
        cmd = go1_sdk.HighCmd()
        state = go1_sdk.HighState()
        udp.InitCmdData(cmd)

    if AgileX_scoutMINI:
        password = "kat354"
        os.system(f"echo {password} | sudo -S ip link set can0 up type can bitrate 500000")
        time.sleep(1)  # Počkej 1 sekundu na aktivaci
        bus = can.interface.Bus(channel='can0', bustype='socketcan')
        #  Povol CAN Command Mode
        send_can_message(bus, 0x421, bytes([0x01]))
        time.sleep(1)

    server_url = "http://192.168.0.106:8000/report_status"
    log_url = "http://192.168.0.106:8000/report_log"
    start_time = time.time()
    watchdog = time.time()
    # signal.signal(signal.SIGUSR1, signal_handler)
    # signal.signal(signal.SIGUSR2, signal_handler)
    print("Running object detection ... Press 'Esc' to quit")

    zed = sl.Camera()

    if server_enabled:
        try:
            log_message(log_url, "Camera Initialization \n")
            # Send a status update to the server
            requests.post(server_url, json={"status": "Starting"})
        except Exception as e:
            log_message(log_url, f"Error: {e}")
            requests.post(server_url, json={"status": "Init Error"})

    # Create a InitParameters object and set configuration parameters
    init_params = sl.InitParameters()
    init_params.camera_resolution = sl.RESOLUTION.HD1080
    init_params.camera_fps = 30
    init_params.coordinate_units = sl.UNIT.METER
    init_params.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP
    init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE
    init_params.depth_maximum_distance = 20

    print("ZED camera setup params")

    # If applicable, use the SVO given as parameter
    # Otherwise use ZED live stream
    if is_playback == True:
        filepath = "C:\\Users\\tomin\\Documents\\ZED\\test_kumar.svo"
        print("Using SVO file: {0}".format(filepath))
        init_params.svo_real_time_mode = True
        init_params.set_from_svo_file(filepath)
        is_playback = False

    if is_classificator == True:
        yolo_model = YOLO('best.pt')

    status = zed.open(init_params)
    print("ZED camera opened")

    # Nastavení adresáře pro ukládání souborů
    directory = os.path.expanduser('~/Documents/Records/Measurements')
    os.makedirs(directory, exist_ok=True)

    # Vytvoření názvu souboru podle aktuálního času
    filename = os.path.join(directory, time.strftime('%d_%m_%Y_%H_%M_%S') + ".txt")

    if server_enabled:
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

    # Enable positional tracking module
    positional_tracking_parameters = sl.PositionalTrackingParameters()
    # If the camera is static in space, enabling this setting below provides better depth quality and faster computation
    # positional_tracking_parameters.set_as_static = True
    zed.enable_positional_tracking(positional_tracking_parameters)

    # Enable object detection module
    batch_parameters = sl.BatchParameters()
    if USE_BATCHING:
        batch_parameters.enable = True
        batch_parameters.latency = 2.0
        batch_handler = BatchSystemHandler(batch_parameters.latency * 2)
    else:
        batch_parameters.enable = False

    obj_param = sl.ObjectDetectionParameters(batch_trajectories_parameters=batch_parameters)
    obj_param.detection_model = sl.OBJECT_DETECTION_MODEL.MULTI_CLASS_BOX_FAST
    # Defines if the object detection will track objects across images flow.
    obj_param.enable_tracking = True
    obj_param.instance_module_id = 1

    body_param = sl.BodyTrackingParameters()
    body_param.enable_tracking = True  # Track people across images flow
    body_param.enable_body_fitting = False  # Smooth skeleton move,Optimize the person joints position,more computations
    body_param.detection_model = sl.BODY_TRACKING_MODEL.HUMAN_BODY_FAST
    body_param.body_format = sl.BODY_FORMAT.BODY_18  # Choose the BODY_FORMAT you wish to use
    body_param.instance_module_id = 0

    bt_check = zed.enable_body_tracking(body_param)
    if bt_check != sl.ERROR_CODE.SUCCESS:
        print("Body tracking false")
    od_check = zed.enable_object_detection(obj_param)
    if od_check != sl.ERROR_CODE.SUCCESS:
        print("Obejct detection false")

    bodies = sl.Bodies()
    body_runtime_param = sl.BodyTrackingRuntimeParameters()
    # For outdoor scene or long range, the confidence should be lowered to avoid missing detections (~20-30)
    # For indoor scene or closer range, a higher confidence limits the risk of false positives and increase the precision (~50+)
    body_runtime_param.detection_confidence_threshold = 40

    camera_infos = zed.get_camera_information()

    # Configure object detection runtime parameters
    obj_runtime_param = sl.ObjectDetectionRuntimeParameters()
    detection_confidence = 60
    obj_runtime_param.detection_confidence_threshold = detection_confidence
    # To select a set of specific object classes
    obj_runtime_param.object_class_filter = [sl.OBJECT_CLASS.PERSON]
    # To set a specific threshold
    obj_runtime_param.object_class_detection_confidence_threshold = {sl.OBJECT_CLASS.PERSON: detection_confidence}

    # Runtime parameters
    runtime_params = sl.RuntimeParameters()
    runtime_params.confidence_threshold = 50

    # Create objects that will store SDK outputs
    objects = sl.Objects()
    image_left = sl.Mat()

    # Utilities for 2D display
    display_resolution = sl.Resolution(min(camera_infos.camera_configuration.resolution.width, 1280),
                                       min(camera_infos.camera_configuration.resolution.height, 720))
    image_scale = [display_resolution.width / camera_infos.camera_configuration.resolution.width
        , display_resolution.height / camera_infos.camera_configuration.resolution.height]
    image_left_ocv = np.full((display_resolution.height, display_resolution.width, 4), [245, 239, 239, 255], np.uint8)

    # Utilities for tracks view
    camera_config = zed.get_camera_information().camera_configuration
    tracks_resolution = sl.Resolution(1200, display_resolution.height)
    track_view_generator = cv_viewer.TrackingViewer(tracks_resolution, camera_config.fps,
                                                    init_params.depth_maximum_distance)
    track_view_generator.set_camera_calibration(camera_config.calibration_parameters)
    image_track_ocv = np.zeros((tracks_resolution.height, tracks_resolution.width, 4), np.uint8)

    # Will store the 2D image and tracklet views
    global_image = np.full((display_resolution.height, display_resolution.width + tracks_resolution.width, 4),
                           [245, 239, 239, 255], np.uint8)

    # Camera pose
    cam_w_pose = sl.Pose()
    cam_c_pose = sl.Pose()

    extendedObjects = ObjectProvider.ExtendedObjectsProvider()

    quit_app = False

    # while (viewer.is_available() and (quit_app == False)):
    while (quit_app == False):
        time1 = time.time()
        if UnitreeGo1:
            udp.Recv()
            udp.GetRecv(state)

            cmd.mode = 0  # 0:idle, default stand      1:forced stand     2:walk continuously
            cmd.gaitType = 0
            cmd.speedLevel = 0
            cmd.footRaiseHeight = 0
            cmd.bodyHeight = 0
            cmd.euler = [0, 0, 0]
            cmd.velocity = [0, 0]
            cmd.yawSpeed = 0.0
            cmd.reserve = 0

        if zed.grab(runtime_params) == sl.ERROR_CODE.SUCCESS:
            # Retrieve objects
            OD_state = zed.retrieve_objects(objects, obj_runtime_param, obj_param.instance_module_id)
            BT_state = zed.retrieve_bodies(bodies, body_runtime_param, body_param.instance_module_id)
            if (OD_state == sl.ERROR_CODE.SUCCESS and objects.is_new and BT_state == sl.ERROR_CODE.SUCCESS):
                # Retrieve image
                zed.retrieve_image(image_left, sl.VIEW.LEFT, sl.MEM.CPU, display_resolution)
                image_render_left = image_left.get_data()
                # Get camera pose
                zed.get_position(cam_c_pose, sl.REFERENCE_FRAME.CAMERA)
                zed.get_position(cam_w_pose, sl.REFERENCE_FRAME.WORLD)

                ZED_pos = cam_w_pose.get_translation().get()
                ZED_orient = cam_w_pose.get_euler_angles(radian=False)
                ZED_pose_confidence = cam_w_pose.pose_confidence

                update_render_view = True
                update_tracking_view = True

                # Detection & Tracking Merging to new Classification Object
                extendedObjects.UpdateObject(objects.object_list, objects.timestamp)
                extendedObjects.UpdateBody(bodies.body_list)

                # Classification
                np.copyto(image_left_ocv, image_render_left)
                if is_classificator:
                    classification.classify(image_left_ocv, image_scale, extendedObjects, yolo_model)

                # Robot Speed & Person Zone calculation
                vx_robot, distance = ZoneCalculation.CalculateZone(extendedObjects)

                print("v_robot", vx_robot)
                print("distance", distance)

                with open(filename, 'a') as file:
                    cas = time.time()
                    # Zapsání hodnot do souboru
                    file.write(f"{distance}, {vx_robot}, {cas}\n")

                if UnitreeGo1:
                    cmd.mode = 2
                    cmd.gaitType = 1
                    cmd.velocity = [vx_robot, 0]
                    cmd.yawSpeed = 0.0
                    cmd.bodyHeight = 0

                if AgileX_scoutMINI:
                    linear_speed = int(vx_robot * 1000)  # Převod m/s na mm/s
                    linear_speed_bytes = linear_speed.to_bytes(2, byteorder='big', signed=True)
                    command_data = linear_speed_bytes + b'\x00\x00\x00\x00\x00\x00'  # Úhlová rychlost = 0, zbytek nuly

                num_persons = len(extendedObjects.extendedObjectsList)
                actual_time = round(time.time() - start_time)

                if server_enabled:
                    try:
                        log_message(log_url, "Working for: " + str(actual_time) + " seconds and saw " + str(
                            num_persons) + " people\n")
                        # Send a status update to the server
                        requests.post(server_url, json={"status": "Running"})
                    except Exception as e:
                        log_message(log_url, f"Error: {e}")
                        requests.post(server_url, json={"status": "Failed"})

                if actual_time > 12:  # delay pro vykresleni obrazu az po chvili, jinak obcas bug pri detekci osoby moc brzo
                    # 2D rendering
                    if update_render_view:
                        cv_viewer.render_2D(image_left_ocv, image_scale, extendedObjects, obj_param.enable_tracking)
                        cv_viewer.render_2D_body(image_left_ocv, image_scale, bodies.body_list, body_param.enable_tracking, body_param.body_format, extendedObjects,obj_param.enable_tracking)
                        global_image = cv2.hconcat([image_left_ocv, image_track_ocv])  # spojeni obou obrazu do jednoho horizontalne
                        cv2.imshow("Detection", image_left_ocv)
                        cv2.waitKey(10)

                    # Tracking view
                    if update_tracking_view:
                        track_view_generator.generate_view(objects, cam_w_pose, image_track_ocv, objects.is_tracked,
                                                           extendedObjects)  # TODO plne nahradit objects -> extendedObjects
                        cv2.imshow("Tracking", image_track_ocv)
                        cv2.waitKey(10)
        if UnitreeGo1:
            udp.SetSend(cmd)
            udp.Send()

        if AgileX_scoutMINI:
            send_can_message(bus, 0x111, command_data)

        if (is_playback and (zed.get_svo_position() == zed.get_svo_number_of_frames() - 1)):
            print("End of SVO")
            quit_app = True

        looptime = time.time() - time1
        #print("loop time is: ", looptime)

    cv2.destroyAllWindows()
    # viewer.exit()
    image_left.free(sl.MEM.CPU)

    if USE_BATCHING:
        batch_handler.clear()

    # Disable modules and close camera
    zed.disable_object_detection()
    zed.disable_positional_tracking()

    zed.close()
