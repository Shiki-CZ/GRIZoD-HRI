import pyzed.sl as sl
from datetime import datetime
from config import ZED_INIT_PARAMS, SVO_FILEPATH, RECORD_DIR, USE_BATCHING, OD_RUNTIME_CONFIDENCE, \
    BODY_TRACKING_CONFIDENCE
from server_handler import DataLogger


class ZEDCamera:
    def __init__(self, logger: DataLogger, is_playback=False):
        self.zed = sl.Camera()
        self.logger = logger
        self.is_recording = False
        self.is_playback = is_playback

        # Initialize parameters from config
        self.init_params = ZED_INIT_PARAMS
        if self.is_playback:
            self.init_params.svo_real_time_mode = True
            self.init_params.set_from_svo_file(SVO_FILEPATH)

        self.obj_param = sl.ObjectDetectionParameters()
        self.obj_param.detection_model = sl.OBJECT_DETECTION_MODEL.MULTI_CLASS_BOX_FAST
        self.obj_param.enable_tracking = True
        self.obj_param.instance_module_id = 1

        self.body_param = sl.BodyTrackingParameters()
        self.body_param.enable_tracking = True
        self.body_param.enable_body_fitting = False
        self.body_param.detection_model = sl.BODY_TRACKING_MODEL.HUMAN_BODY_FAST
        self.body_param.body_format = sl.BODY_FORMAT.BODY_18
        self.body_param.instance_module_id = 0

    def open(self):
        self.logger.log("Opening ZED camera...")
        status = self.zed.open(self.init_params)
        if status != sl.ERROR_CODE.SUCCESS:
            self.logger.log(f"Camera failed to open: {repr(status)}")
            exit()
        self.logger.log("ZED camera opened successfully.")

        # Enable modules
        self.zed.enable_positional_tracking(sl.PositionalTrackingParameters())
        self.zed.enable_object_detection(self.obj_param)
        self.zed.enable_body_tracking(self.body_param)

    def grab_data(self, display_resolution):
        # Retrieve objects, bodies, and images
        runtime_params = sl.RuntimeParameters(confidence_threshold=50)
        obj_runtime_param = sl.ObjectDetectionRuntimeParameters(
            detection_confidence_threshold=OD_RUNTIME_CONFIDENCE,
            object_class_filter=[sl.OBJECT_CLASS.PERSON]
        )
        body_runtime_param = sl.BodyTrackingRuntimeParameters(
            detection_confidence_threshold=BODY_TRACKING_CONFIDENCE
        )

        objects = sl.Objects()
        bodies = sl.Bodies()
        image_left = sl.Mat()

        if self.zed.grab(runtime_params) == sl.ERROR_CODE.SUCCESS:
            od_state = self.zed.retrieve_objects(objects, obj_runtime_param, self.obj_param.instance_module_id)
            bt_state = self.zed.retrieve_bodies(bodies, body_runtime_param, self.body_param.instance_module_id)

            if od_state == sl.ERROR_CODE.SUCCESS and bt_state == sl.ERROR_CODE.SUCCESS and objects.is_new:
                self.zed.retrieve_image(image_left, sl.VIEW.LEFT, sl.MEM.CPU, display_resolution)
                return image_left, objects, bodies

        return None, None, None

    def start_recording(self):
        if not self.is_recording:
            current_datetime = datetime.now()
            record_path = RECORD_DIR + str(current_datetime.strftime("%Y-%m-%d-%H-%M-%S")) + ".svo"
            recording_param = sl.RecordingParameters(record_path, sl.SVO_COMPRESSION_MODE.H264)
            err = self.zed.enable_recording(recording_param)
            if err == sl.ERROR_CODE.SUCCESS:
                self.logger.log("Recording started.")
                self.is_recording = True
            else:
                self.logger.log(f"Failed to start recording: {repr(err)}")

    def stop_recording(self):
        if self.is_recording:
            self.zed.disable_recording()
            self.logger.log("Recording stopped.")
            self.is_recording = False

    def close(self):
        self.stop_recording()
        self.zed.disable_object_detection()
        self.zed.disable_positional_tracking()
        self.zed.disable_body_tracking()
        self.zed.close()
        self.logger.log("ZED camera closed.")