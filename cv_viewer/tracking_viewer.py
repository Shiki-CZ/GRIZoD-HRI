import cv2
import numpy as np

from cv_viewer.utils import *
import pyzed.sl as sl
import math
from collections import deque
import keyboard

#----------------------------------------------------------------------
#       2D LEFT VIEW
#----------------------------------------------------------------------

toggle_caption = True
previous_toggle_caption = False
key_check = False

def space2plane(pt3d, img_scale):
    cx = 969.580322265625  # camera_infos.camera_configuration.calibration_parameters.left_cam.cx
    cy = 559.6625366210938  # camera_infos.camera_configuration.calibration_parameters.left_cam.cy
    fx = 1082.6632080078125  # camera_infos.camera_configuration.calibration_parameters.left_cam.fx
    fy = 1082.6632080078125  # camera_infos.camera_configuration.calibration_parameters.left_cam.fy

    u = (-pt3d[0] / pt3d[2]) * fx + cx
    v = (pt3d[1] / pt3d[2]) * fy + cy
    pt_2d = [u, v]
    cv_pt = cvt(pt_2d, img_scale)
    return cv_pt
def cvt(pt, scale):
    '''
    Function that scales point coordinates
    '''
    out = [pt[0]*scale[0], pt[1]*scale[1]]
    return out

def get_image_position(bounding_box_image, img_scale):
    out_position = np.zeros(2)
    out_position[0] = (bounding_box_image[0][0] + (bounding_box_image[2][0] - bounding_box_image[0][0])*0.5) * img_scale[0]
    out_position[1] = (bounding_box_image[0][1] + (bounding_box_image[2][1] - bounding_box_image[0][1])*0.5) * img_scale[1]
    return out_position

def render_sk(left_display, img_scale, obj, color, BODY_BONES):
    # Draw skeleton bones
    for part in BODY_BONES:
        kp_a = cvt(obj.keypoint_2d[part[0].value], img_scale)
        kp_b = cvt(obj.keypoint_2d[part[1].value], img_scale)
        # Check that the keypoints are inside the image
        if(kp_a[0] < left_display.shape[1] and kp_a[1] < left_display.shape[0]
        and kp_b[0] < left_display.shape[1] and kp_b[1] < left_display.shape[0]
        and kp_a[0] > 0 and kp_a[1] > 0 and kp_b[0] > 0 and kp_b[1] > 0 ):
            cv2.line(left_display, (int(kp_a[0]), int(kp_a[1])), (int(kp_b[0]), int(kp_b[1])), color, 1, cv2.LINE_AA)

    # Skeleton joints
    for kp in obj.keypoint_2d: # Skeleton joints
        cv_kp = cvt(kp, img_scale)
        if(cv_kp[0] < left_display.shape[1] and cv_kp[1] < left_display.shape[0]):
            cv2.circle(left_display, (int(cv_kp[0]), int(cv_kp[1])), 3, color, -1)

def render_2D_body(left_display, img_scale, objects, is_tracking_on_body, body_format, extendedObjects, is_tracking_on):
    overlay = left_display.copy()

    # Render skeleton joints and bones
    for obj in extendedObjects.extendedObjectsList:
        if obj.bodyPose is not None:
            if render_object(obj, is_tracking_on):
                if len(obj.bodyPose.keypoint_2d) > 0:
                    color = generate_color_id_u(obj.averagedClass)
                    if body_format == sl.BODY_FORMAT.BODY_18:
                        render_sk(left_display, img_scale, obj.bodyPose, color, sl.BODY_18_BONES)
                    elif body_format == sl.BODY_FORMAT.BODY_34:
                        render_sk(left_display, img_scale, obj.bodyPose, color, sl.BODY_34_BONES)
                    elif body_format == sl.BODY_FORMAT.BODY_38:
                        render_sk(left_display, img_scale, obj.bodyPose, color, sl.BODY_38_BONES)
                    elif body_format == sl.BODY_FORMAT.BODY_70:
                        render_sk(left_display, img_scale, obj.bodyPose, color, sl.BODY_70_BONES)

    cv2.addWeighted(left_display, 0.9, overlay, 0.1, 0.0, left_display)

def toggle(event):
    global toggle_caption, previous_toggle_caption, key_check
    if keyboard.is_pressed("c") == False and previous_toggle_caption == True:
        toggle_caption = not toggle_caption
    previous_toggle_caption = keyboard.is_pressed("c")

def render_2D(left_display, img_scale, objects, is_tracking_on):
    global toggle_caption,previous_toggle_caption, key_check
    overlay = left_display.copy()

    line_thickness = 2
    for obj in objects.extendedObjectsList:
        if(render_object(obj, is_tracking_on)):
            base_color = generate_color_id_u(obj.averagedClass)
            # Display image scaled 2D bounding box
            top_left_corner = cvt(obj.bounding_box_2d[0], img_scale)
            top_right_corner = cvt(obj.bounding_box_2d[1], img_scale)
            bottom_right_corner = cvt(obj.bounding_box_2d[2], img_scale)
            bottom_left_corner = cvt(obj.bounding_box_2d[3], img_scale)

            # Creation of the 2 horizontal lines
            cv2.line(left_display, (int(top_left_corner[0]), int(top_left_corner[1])), (int(top_right_corner[0]), int(top_right_corner[1])), base_color, line_thickness)
            cv2.line(left_display, (int(bottom_left_corner[0]), int(bottom_left_corner[1])), (int(bottom_right_corner[0]), int(bottom_right_corner[1])), base_color, line_thickness)
            # Creation of 2 vertical lines
            draw_vertical_line(left_display, bottom_left_corner, top_left_corner, base_color, line_thickness)
            draw_vertical_line(left_display, bottom_right_corner, top_right_corner, base_color, line_thickness)

            # Scaled ROI
            roi_height = int(top_right_corner[0] - top_left_corner[0])
            roi_width = int(bottom_left_corner[1] - top_left_corner[1])
            overlay_roi = overlay[int(top_left_corner[1]):int(top_left_corner[1] + roi_width)
                                 , int(top_left_corner[0]):int(top_left_corner[0] + roi_height)]

            overlay_roi[:,:,:] = base_color

            #keyboard.on_release_key("c", toggle)
            #previous_toggle_caption = keyboard.is_pressed("c")

            if toggle_caption:
                # Display Object label as text
                position_image = get_image_position(obj.bounding_box_2d, img_scale)
                text_position = (int(position_image[0] - 20), int(position_image[1] - 10))
                text = str(obj.label) + " " + obj.averagedClassName
                text_color = (105,225,255,255)
                cv2.putText(left_display, text, text_position, cv2.FONT_HERSHEY_DUPLEX, 0.3, text_color, 1)

                # Diplay Object distance to camera as text
                if(np.isfinite(obj.position[2])):
                    text = str(round(math.sqrt(obj.position[0]**2+obj.position[2]**2), 1)) + " Meters"
                    text_speed = str(round(math.sqrt(obj.velocity[0]**2+obj.velocity[2]**2), 1)) + " m/s"
                    text_position = (int(position_image[0] - 20), int(position_image[1]))
                    text_position_speed = (int(position_image[0] - 20), int(position_image[1]+10))
                    cv2.putText(left_display, text, text_position, cv2.FONT_HERSHEY_DUPLEX, 0.3, text_color, 1)
                    cv2.putText(left_display, text_speed, text_position_speed, cv2.FONT_HERSHEY_DUPLEX, 0.3, text_color, 1)

    # Here, overlay is as the left image, but with opaque masks on each detected objects
    cv2.addWeighted(left_display, 0.7, overlay, 0.3, 0.0, left_display)


#----------------------------------------------------------------------
#       2D TRACKING VIEW
#----------------------------------------------------------------------

class TrackingViewer:
    def __init__(self, res, fps, D_max):
        # Window size
        self.window_width = res.width
        self.window_height = res.height

        # Window Zoom
        D_max = D_max/2

        # Visualisation settings
        self.has_background_ready = False
        self.background = np.full((self.window_height, self.window_width, 4), [245, 239, 239,255], np.uint8)

        self.cv_meter = int(self.window_height/D_max)

        # Invert Z due to Y axis of ocv window
        # Show objects between [z_min, 0] (z_min < 0)
        self.z_min = -D_max
        # Show objects between [x_min, x_max]
        self.x_min = self.z_min
        self.x_max = -self.x_min

        # Conversion from world position to pixel coordinates
        self.x_step = (self.x_max - self.x_min) / self.window_width
        self.z_step = abs(self.z_min) / (self.window_height)

        self.camera_calibration = sl.CalibrationParameters()

        # List of alive tracks
        self.tracklets = []

    def set_camera_calibration(self, calib):
        self.camera_calibration = calib
        self.has_background_ready = False

    def generate_view(self, objects, current_camera_pose, tracking_view, tracking_enabled, extendedObjects):
        global toggle_caption, previous_toggle_caption, key_check
        # To get position in WORLD reference
        for obj in extendedObjects.extendedObjectsList:
            pos = obj.position
            tmp_pos = sl.Translation()
            tmp_pos.init_vector(pos[0],pos[1],pos[2])
            new_pos = (tmp_pos * current_camera_pose.get_orientation()).get() + current_camera_pose.get_translation().get()
            obj.position = np.array([new_pos[0], new_pos[1], new_pos[2]])

        # Initialize visualisation
        if(not self.has_background_ready):
            self.generate_background()

        np.copyto(tracking_view, self.background,'no')

        if(tracking_enabled):
            # First add new points and remove the ones that are too old
            current_timestamp = extendedObjects.timestamp.get_seconds()
            self.add_to_tracklets(extendedObjects,current_timestamp)
            self.prune_old_points(current_timestamp)

            # Draw all tracklets
            if toggle_caption:
                self.draw_zones(tracking_view, objects, extendedObjects, current_camera_pose) #TODO vykresleni zon sem?
            self.draw_tracklets(tracking_view, current_camera_pose)
        else:
            self.draw_points(extendedObjects.extendedObjectsList, tracking_view, current_camera_pose)

    def add_to_tracklets(self, objects, current_timestamp):
        for obj in objects.extendedObjectsList:
            if((obj.tracking_state != sl.OBJECT_TRACKING_STATE.OK) or (not np.isfinite(obj.position[0])) or (obj.id < 0)):
                continue

            new_object = True
            for i in range(len(self.tracklets)):
                if self.tracklets[i].id == obj.id:
                    new_object = False
                    self.tracklets[i].add_point(obj, current_timestamp)
                    self.tracklets[i].class_id = obj.averagedClass

            # In case this object does not belong to existing tracks
            if (new_object):
                self.tracklets.append(Tracklet(obj, obj.label, current_timestamp))

    def prune_old_points(self, ts):
        track_to_delete = []
        for it in self.tracklets:
            if((ts - it.last_timestamp) > (3)):
                track_to_delete.append(it)

        for it in track_to_delete:
            self.tracklets.remove(it)

#----------------------------------------------------------------------
#       Drawing functions
#----------------------------------------------------------------------

    def draw_points(self, objects, tracking_view, current_camera_pose):
        for obj in objects:
            if(not np.isfinite(obj.position[0])):
                continue
            clr = generate_color_id_u(obj.averagedClass)
            pt = TrackPoint(obj.position)
            cv_start_point = self.to_cv_point(pt.get_xyz(), current_camera_pose)
            cv2.circle(tracking_view, (int(cv_start_point[0]), int(cv_start_point[1])), 6, clr, 2)

    def draw_tracklets(self, tracking_view, current_camera_pose):
        zone = (0, 0, 255)
        for track in self.tracklets:
            clr = generate_color_id_u(track.class_id)
            print("Track ID: ", track.class_id)
            cv_start_point = self.to_cv_point(track.positions[0].get_xyz(), current_camera_pose)
            cv_actual_point = self.to_cv_point(track.positions[-1].get_xyz(), current_camera_pose) # aktualni pozice cloveka
            text_color = (0, 0, 0, 255)
            for point_index in range(1, len(track.positions)):
                cv_end_point = self.to_cv_point(track.positions[point_index].get_xyz(), current_camera_pose)
                cv2.line(tracking_view, (int(cv_start_point[0]), int(cv_start_point[1])), (int(cv_end_point[0]), int(cv_end_point[1])), clr, 3) #trajektorie
                cv_start_point = cv_end_point
            cv2.circle(tracking_view, (int(cv_start_point[0]), int(cv_start_point[1])), 6, clr, -1) #osoba
            cv2.putText(tracking_view, str(track.id), (int(cv_actual_point[0]-5), int(cv_actual_point[1]+5)), cv2.FONT_HERSHEY_DUPLEX, 0.3, text_color, 1)

    def draw_zones(self, tracking_view, objects, extendedObjects, current_camera_pose): #TODO pouze vykresleni, výpočet jinde!!!
        valid_ids = []


        for obj in objects.object_list:
            valid_ids.append(obj.id)
        zones_count = [0,1,2,3,4] #TODO celkový počet zón, nejde to udělat jinak?
        zone_colors = [(0, 0, 255), (0, 100, 255), (51, 153, 255), (0, 255, 255), (100, 220, 40)]

        for zone in range(len(zones_count) - 1, -1, -1):
            for person in extendedObjects.extendedObjectsList:
                if person.id not in valid_ids:
                    continue
                xyz_pos = [person.position[0],person.position[1],person.position[2]]
                if not (math.isnan(xyz_pos[0]) and math.isnan(xyz_pos[2]) and math.isnan(person.bodyMovementAngle) and math.isnan(person.zone_b)):
                    cv_position = self.to_cv_point(xyz_pos, current_camera_pose)
                    cv2.ellipse(tracking_view, (int(cv_position[0]), int(cv_position[1])), (int(person.zone_b[zone] * self.cv_meter), int(person.zone_b[zone] * self.cv_meter)), person.bodyMovementAngle, 90, 270, zone_colors[zone], -1)
                    cv2.ellipse(tracking_view, (int(cv_position[0]), int(cv_position[1])), (int(person.zone_a[zone] * self.cv_meter), int(person.zone_b[zone] * self.cv_meter)), person.bodyMovementAngle, 0, 90, zone_colors[zone],-1)
                    cv2.ellipse(tracking_view, (int(cv_position[0]), int(cv_position[1])), (int(person.zone_a[zone] * self.cv_meter), int(person.zone_b[zone] * self.cv_meter)), person.bodyMovementAngle, 270, 360, zone_colors[zone], -1)
        zone = (0, 0, 0)
        point0 = self.to_cv_point(0.0, 0.0)
        cv2.circle(tracking_view, (int(point0[0]), int(point0[1])), (self.cv_meter * 1), zone,
                   1)  # 36px je 1 metr od [0,0]
        cv2.putText(tracking_view, "1m", (int(point0[0]) - 66, int(point0[1]) - 5), cv2.FONT_HERSHEY_DUPLEX, 0.4,
                    zone, 1)
        cv2.circle(tracking_view, (int(point0[0]), int(point0[1])), (self.cv_meter * 2), zone, 1)
        cv2.putText(tracking_view, "2m", (int(point0[0]) - 138, int(point0[1]) - 5), cv2.FONT_HERSHEY_DUPLEX, 0.4,
                    zone, 1)
        cv2.circle(tracking_view, (int(point0[0]), int(point0[1])), (self.cv_meter * 3), zone, 1)
        cv2.putText(tracking_view, "3m", (int(point0[0]) - 210, int(point0[1]) - 5), cv2.FONT_HERSHEY_DUPLEX, 0.4,
                    zone, 1)
        cv2.circle(tracking_view, (int(point0[0]), int(point0[1])), (self.cv_meter * 4), zone, 1)
        cv2.putText(tracking_view, "4m", (int(point0[0]) - 282, int(point0[1]) - 5), cv2.FONT_HERSHEY_DUPLEX, 0.4,
                    zone, 1)
        cv2.circle(tracking_view, (int(point0[0]), int(point0[1])), (self.cv_meter * 5), zone, 1)
        cv2.putText(tracking_view, "5m", (int(point0[0]) - 354, int(point0[1]) - 5), cv2.FONT_HERSHEY_DUPLEX, 0.4,
                    zone, 1)
        cv2.circle(tracking_view, (int(point0[0]), int(point0[1])), (self.cv_meter * 7), zone, 1)
        cv2.putText(tracking_view, "7m", (int(point0[0]) - 498, int(point0[1]) - 210), cv2.FONT_HERSHEY_DUPLEX, 0.4,
                    zone, 1)
        cv2.circle(tracking_view, (int(point0[0]), int(point0[1])), (self.cv_meter * 10), zone, 1)
        cv2.putText(tracking_view, "10m", (int(point0[0]) - 498, int(point0[1]) - 340), cv2.FONT_HERSHEY_DUPLEX, 0.4,
                    zone, 1)

    def generate_background(self):
        camera_color = [255, 230, 204, 255]

        # Get FOV intersection with window borders
        fov = 2.0 * math.atan(self.camera_calibration.left_cam.image_size.width / (2.0 *  self.camera_calibration.left_cam.fx))

        z_at_x_max = self.x_max / math.tan(fov / 2.0)
        left_intersection_pt = self.to_cv_point(self.x_min, -z_at_x_max)
        right_intersection_pt = self.to_cv_point(self.x_max, -z_at_x_max)

        # Drawing camera
        camera_pts = np.array([left_intersection_pt
                                , right_intersection_pt
                                , [int(self.window_width / 2), self.window_height]]
                                , dtype=np.int32)
        cv2.fillConvexPoly(self.background, camera_pts, camera_color)

        zone = (0, 0, 0)
        point0 = self.to_cv_point(0.0, 0.0)
        cv2.circle(self.background, (int(point0[0]), int(point0[1])), (self.cv_meter * 1), zone,
                   1)  # 36px je 1 metr od [0,0]
        cv2.putText(self.background, "1m", (int(point0[0]) - 66, int(point0[1]) - 5), cv2.FONT_HERSHEY_DUPLEX, 0.4,
                    zone, 1)
        cv2.circle(self.background, (int(point0[0]), int(point0[1])), (self.cv_meter * 2), zone, 1)
        cv2.putText(self.background, "2m", (int(point0[0]) - 138, int(point0[1]) - 5), cv2.FONT_HERSHEY_DUPLEX, 0.4,
                    zone, 1)
        cv2.circle(self.background, (int(point0[0]), int(point0[1])), (self.cv_meter * 3), zone, 1)
        cv2.putText(self.background, "3m", (int(point0[0]) - 210, int(point0[1]) - 5), cv2.FONT_HERSHEY_DUPLEX, 0.4,
                    zone, 1)
        cv2.circle(self.background, (int(point0[0]), int(point0[1])), (self.cv_meter * 4), zone, 1)
        cv2.putText(self.background, "4m", (int(point0[0]) - 282, int(point0[1]) - 5), cv2.FONT_HERSHEY_DUPLEX, 0.4,
                    zone, 1)
        cv2.circle(self.background, (int(point0[0]), int(point0[1])), (self.cv_meter * 5), zone, 1)
        cv2.putText(self.background, "5m", (int(point0[0]) - 354, int(point0[1]) - 5), cv2.FONT_HERSHEY_DUPLEX, 0.4,
                    zone, 1)
        cv2.circle(self.background, (int(point0[0]), int(point0[1])), (self.cv_meter * 7), zone, 1)
        cv2.putText(self.background, "7m", (int(point0[0]) - 498, int(point0[1]) - 210), cv2.FONT_HERSHEY_DUPLEX, 0.4,
                    zone, 1)
        cv2.circle(self.background, (int(point0[0]), int(point0[1])), (self.cv_meter * 10), zone, 1)
        cv2.putText(self.background, "10m", (int(point0[0]) - 498, int(point0[1]) - 340), cv2.FONT_HERSHEY_DUPLEX, 0.4,
                    zone, 1)

    def to_cv_point(self, x, z):
        out = []
        if isinstance(x, float) and isinstance(z, float):
            out = [int((x - self.x_min) / self.x_step), int((z - self.z_min) / self.z_step)]
        elif isinstance(x, list) and isinstance(z, sl.Pose):
            # Go to camera current pose
            rotation = z.get_rotation_matrix()
            rotation.inverse()
            tmp = x - (z.get_translation() * rotation.get_orientation()).get()
            new_position = sl.Translation()
            new_position.init_vector(tmp[0],tmp[1],tmp[2])
            out = [int(((new_position.get()[0] - self.x_min)/self.x_step) + 0.5), int(((new_position.get()[2] - self.z_min)/self.z_step) + 0.5)]
        elif isinstance(x, TrackPoint) and isinstance(z, sl.Pose):
            pos = x.get_xyz()
            out = self.to_cv_point(pos, z)
        else:
            print("Unhandled argument type")
        return out


class TrackPoint:
    def __init__(self, pos_):
        self.x = pos_[0]
        self.y = pos_[1]
        self.z = pos_[2]

    def get_xyz(self):
        return [self.x, self.y, self.z]

class Tracklet:
    def __init__(self, obj_, type_, timestamp_):
        self.id = obj_.id
        self.class_id = obj_.averagedClass
        self.object_type = type_
        self.positions = deque()
        self.add_point(obj_, timestamp_)

    def add_point(self, obj_, timestamp_):
        self.positions.append(TrackPoint(obj_.position))
        self.last_timestamp = timestamp_
