from pyzed.sl import Objects
from collections import deque, defaultdict
import numpy as np

class ExtendedObject(Objects):
    def __init__(self):
        super().__init__()  # Initialize the base class if needed
        self.className = "None"
        self.classNumber = None
        self.classNameConf = None
        self.top5 = None
        self.top5conf = None
        self.classNumberBuffer = deque(maxlen=100)
        self.classConfBuffer = deque(maxlen=100)
        self.averagedClassName = "None"
        self.averagedClass = 0

        self.zone_a = [0.45,0.72,1.17,1.9,3.08]
        self.zone_b = [0.45,0.72,1.17,1.9,3.08]
        self.safety_zone = 0.45
        self.bodyMovementAngle = 0
        self.velocity = np.array([0,0,0])
        self.position = np.array([0,0,0])

        self.bodyPose = None


    @staticmethod
    def FromObject(source):
        result = ExtendedObject()
        # Attempt to copy attributes without using vars()
        for attr in dir(source):
            if not attr.startswith("__") and not callable(getattr(source, attr)):
                setattr(result, attr, getattr(source, attr))
        return result

    def Update(self, source):
        for attr in dir(source):
            if not attr.startswith("__") and not callable(getattr(source, attr)):
                setattr(self, attr, getattr(source, attr))
