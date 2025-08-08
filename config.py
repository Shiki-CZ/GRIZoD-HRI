import pyzed.sl as sl
import os

# Application Settings
SERVER_ENABLED = False
IS_PLAYBACK = False
IS_CLASSIFICATOR = False
YOLO_MODEL_PATH = "best.pt"
USE_BATCHING = False
WATCHDOG_TIMEOUT = 1
VIZUALIZATION_ENABLED = True

# Robot Settings
UNITREE_GO1_ENABLED = False
AGILEX_SCOUT_MINI_ENABLED = False

# Server URLs
SERVER_URL = "http://192.168.0.106:8000/report_status"
LOG_URL = "http://192.168.0.106:8000/report_log"

# ZED Camera Configuration
ZED_INIT_PARAMS = sl.InitParameters()
ZED_INIT_PARAMS.camera_resolution = sl.RESOLUTION.HD1080
ZED_INIT_PARAMS.camera_fps = 30
ZED_INIT_PARAMS.coordinate_units = sl.UNIT.METER
ZED_INIT_PARAMS.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP
ZED_INIT_PARAMS.depth_mode = sl.DEPTH_MODE.PERFORMANCE
ZED_INIT_PARAMS.depth_maximum_distance = 20
SVO_FILEPATH = "C:\\Users\\tomin\\Documents\\ZED\\test_kumar.svo"

# File Paths
RECORD_DIR = os.path.expanduser('~/Documents/Records/SVO/')
MEASUREMENTS_DIR = os.path.expanduser('~/Documents/Records/Measurements')

# Object Detection Configuration
OD_RUNTIME_CONFIDENCE = 60
BODY_TRACKING_CONFIDENCE = 40