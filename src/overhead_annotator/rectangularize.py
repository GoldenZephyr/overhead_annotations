from overhead_annotator.serde import load, save
from overhead_annotator.model import Region
import numpy as np
import cv2


def yaw_to_R(yaw: float):
    return np.array([[np.cos(yaw), -np.sin(yaw)], [np.sin(yaw), np.cos(yaw)]])


def rectangularize(r: Region):
    pts_2d = np.array(r.vertices)

    rect = cv2.minAreaRect(pts_2d.astype(np.float32))
    r.vertices = cv2.boxPoints(rect)


annotations = load("overhead_annotations.yaml")
for r in annotations.regions:
    rectangularize(r)

save(annotations, "rectangular_annotations.yaml")
