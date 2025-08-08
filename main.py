import os
import signal
import time
import cv2
import numpy as np
import requests

from config import (
    SERVER_ENABLED, IS_PLAYBACK, VIZUALIZATION_ENABLED,
    IS_CLASSIFICATOR, YOLO_MODEL_PATH, MEASUREMENTS_DIR, WATCHDOG_TIMEOUT,
    SERVER_URL, LOG_URL
)
from zed_camera import ZEDCamera
from robot_control import create_robot_controller
from server_handler import DataLogger
from image_processing import ImageProcessor
import cv_viewer.tracking_viewer as cv_viewer
import pyzed.sl as sl
from batch_system_handler import BatchSystemHandler


# --- Signal handlers ---
def signal_handler(sig, frame):
    if sig == signal.SIGUSR1:
        zed_camera.start_recording()
    elif sig == signal.SIGUSR2:
        zed_camera.stop_recording()


if __name__ == "__main__":
    # --- Initialization ---
    logger = DataLogger(LOG_URL)
    signal.signal(signal.SIGUSR1, signal_handler)
    signal.signal(signal.SIGUSR2, signal_handler)
    zed_camera = ZEDCamera(logger, is_playback=IS_PLAYBACK)
    robot_controller = create_robot_controller()
    image_processor = ImageProcessor(YOLO_MODEL_PATH, is_classificator=IS_CLASSIFICATOR)

    # Initialize robot and camera
    if robot_controller:
        robot_controller.start()

    zed_camera.open()

    if SERVER_ENABLED:
        try:
            requests.post(SERVER_URL, json={"status": "Initialized"})
        except Exception as e:
            logger.log(f"Failed to post status: {e}")

    # Set up measurement file
    os.makedirs(MEASUREMENTS_DIR, exist_ok=True)
    measurement_filename = os.path.join(MEASUREMENTS_DIR, time.strftime('%d_%m_%Y_%H_%M_%S') + ".txt")

    # Set up  2D image viewer
    camera_infos = zed_camera.zed.get_camera_information()
    camera_config = zed_camera.zed.get_camera_information().camera_configuration
    display_resolution = sl.Resolution(min(camera_infos.camera_configuration.resolution.width, 1280),
                                       min(camera_infos.camera_configuration.resolution.height, 720))
    image_left_ocv = np.full((display_resolution.height, display_resolution.width, 4), [245, 239, 239, 255], np.uint8)
    image_scale = [display_resolution.width / camera_config.resolution.width,
                   display_resolution.height / camera_config.resolution.height]

    # Set up tracking viewer
    tracks_resolution = sl.Resolution(1200, display_resolution.height)
    track_view_generator = cv_viewer.TrackingViewer(tracks_resolution, camera_config.fps,
                                                    zed_camera.init_params.depth_maximum_distance)
    track_view_generator.set_camera_calibration(camera_config.calibration_parameters)
    image_track_ocv = np.zeros((tracks_resolution.height, tracks_resolution.width, 4), np.uint8)

    # Will store the 2D image and tracklet views
    global_image = np.full((display_resolution.height, display_resolution.width + tracks_resolution.width, 4),
                           [245, 239, 239, 255], np.uint8)

    start_time = time.time()
    quit_app = False

    while not quit_app:

        image_left, objects, bodies = zed_camera.grab_data(display_resolution)
        vx_robot = 0.0
        start_timer = time.time()

        if image_left and objects and bodies:
            # Convert ZED image to OpenCV format
            np.copyto(image_left_ocv, image_left.get_data())

            # Process data
            vx_robot, distance, extended_objects = image_processor.process_image(image_left_ocv, objects, bodies)

            #print(f"Calculated vx: {vx_robot}, distance: {distance}")

            # Write to measurement file
            with open(measurement_filename, 'a') as file:
                file.write(f"{distance}, {vx_robot}, {time.time()}\n")

            # Log status to server
            if SERVER_ENABLED:
                num_persons = len(extended_objects.extendedObjectsList)
                actual_time = round(time.time() - start_time)
                logger.log(f"Working for: {actual_time} seconds and saw {num_persons} people")

                try:
                    requests.post(SERVER_URL, json={"status": "Running"})
                except Exception as e:
                    logger.log(f"Failed to post status: {e}")

            # Display images if past watchdog timeout
            if time.time() - start_time > WATCHDOG_TIMEOUT and VIZUALIZATION_ENABLED:
                cv_viewer.render_2D(image_left_ocv, image_scale, extended_objects, zed_camera.obj_param.enable_tracking)
                cv_viewer.render_2D_body(image_left_ocv, image_scale, bodies.body_list, zed_camera.body_param.enable_tracking,
                                         zed_camera.body_param.body_format, extended_objects, zed_camera.obj_param.enable_tracking)
                cam_w_pose = sl.Pose()
                track_view_generator.generate_view(objects, cam_w_pose, image_track_ocv, objects.is_tracked,
                                                   extended_objects)

                #global_image = cv2.hconcat([image_left_ocv, image_track_ocv])  # Merging images to one
                cv2.imshow("Detection", image_left_ocv)
                cv2.imshow("Tracking", image_track_ocv)
                cv2.waitKey(10)

        # Send commands to robot
        if robot_controller:
            robot_controller.send_velocity(vx_robot)

        looptime = time.time() - start_timer
        print(f"Sent robot speed: {round(vx_robot,4)}, loop time: {round(looptime,4)}")

        # Check for end of SVO file
        if zed_camera.is_playback and (
                zed_camera.zed.get_svo_position() == zed_camera.zed.get_svo_number_of_frames() - 1):
            logger.log("End of SVO file.")
            quit_app = True

    # --- Cleanup ---
    if robot_controller:
        robot_controller.stop()
    zed_camera.close()
    cv2.destroyAllWindows()