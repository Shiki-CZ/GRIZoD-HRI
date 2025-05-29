import pyzed.sl as sl
from cv_viewer.utils import render_object
from cv_viewer.tracking_viewer import cvt
from collections import defaultdict

def classify(left_display, img_scale, objects, yolo_model):
    if yolo_model != None:
        for obj in objects.extendedObjectsList:
            if obj.tracking_state.name != "TERMINATE":
                # Display image scaled 2D bounding box
                top_left_corner = cvt(obj.bounding_box_2d[0], img_scale)
                bottom_right_corner = cvt(obj.bounding_box_2d[2], img_scale)

                cutout = left_display.copy()
                cutout = cutout[int(top_left_corner[1]):int(bottom_right_corner[1]), int(top_left_corner[0]):int(bottom_right_corner[0])]
                cutout = cutout[..., :3]
                class_results = yolo_model(source=cutout, show=False, device=0, verbose=False)  # predict on an image
                obj.className = class_results[0].names[class_results[0].probs.top1]
                obj.classNumber = class_results[0].probs.top1
                obj.classNameConf = class_results[0].probs.top1conf
                obj.top5 = class_results[0].probs.top5
                obj.top5conf = class_results[0].probs.top5conf
                obj.classNumberBuffer.append(obj.classNumber)
                obj.classConfBuffer.append(obj.classNameConf)
                weightedAverage(obj)

def weightedAverage(person):
    name_mapping = {0: 'adult_man', 1: 'adult_woman', 2: 'child_man', 3: 'child_woman', 4: 'old_man', 5: 'old_woman'}

    class_confidence = defaultdict(list)
    for classNumber, classConf in zip(person.classNumberBuffer, person.classConfBuffer):
        class_confidence[classNumber].append(classConf)

    weighted_conf_list = {}
    for classNumber, classConf in class_confidence.items():
        occurrence_count = len(classConf)
        average_conf = sum(classConf) / occurrence_count
        weighted_conf = average_conf * occurrence_count
        weighted_conf_list[classNumber] = weighted_conf

    person.averagedClass = int(max(weighted_conf_list, key=weighted_conf_list.get))
    person.averagedClassName = name_mapping[person.averagedClass]

