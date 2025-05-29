from cv_viewer.utils import *
from ExtendedObject import ExtendedObject
from typing import List

import copy

class ExtendedObjectsProvider:
    def __init__(self):
        self.extendedObjectsList: List[ExtendedObject] = []
        self.timestamp = 0

    def UpdateObject(self, objectsFromZED, timestamp):
        self.timestamp = timestamp
        for item in objectsFromZED:
            updated = False
            for person in self.extendedObjectsList:
                if(person.id == item.id):
                    person.Update(item)
                    updated = True
                    break
            if(not updated):
                self.extendedObjectsList.append(ExtendedObject.FromObject(item))

    def UpdateBody(self, objectsFromZED):

        for item in objectsFromZED:
            min_total_diff = 100
            for person in self.extendedObjectsList:
                x_diff = abs(item.position[0] - person.position[0])
                y_diff = abs(item.position[1] - person.position[1])
                z_diff = abs(item.position[2] - person.position[2])
                total_diff = x_diff+y_diff+z_diff
                if (total_diff < min_total_diff and total_diff < 0.8 and item.tracking_state.name != "TERMINATE"):
                    min_total_diff = total_diff
                    person.bodyPose = item
                else:
                    person.bodyPose = None