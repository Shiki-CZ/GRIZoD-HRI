from ultralytics import YOLO
import classification
import ZoneCalculation
import ExtendedObjectsProvider as ObjectProvider

class ImageProcessor:
    def __init__(self, yolo_model_path="best.pt", is_classificator=False):
        self.extended_objects = ObjectProvider.ExtendedObjectsProvider()
        self.is_classificator = is_classificator
        self.yolo_model = None
        if self.is_classificator:
            self.yolo_model = YOLO(yolo_model_path)

    def process_image(self, image_left_ocv, objects, bodies):
        # Update extended objects provider
        self.extended_objects.UpdateObject(objects.object_list, objects.timestamp)
        self.extended_objects.UpdateBody(bodies.body_list)

        # Classify objects if enabled
        if self.is_classificator:
            image_scale = [1, 1]  # Placeholder, adjust as needed
            classification.classify(image_left_ocv, image_scale, self.extended_objects, self.yolo_model)

        # Calculate robot speed and zone
        vx_robot, distance = ZoneCalculation.CalculateZone(self.extended_objects)
        return vx_robot, distance, self.extended_objects