from overhead_annotator.serde import load, save
from overhead_annotator.model import Region
import numpy as np
import cv2
import sys


def yaw_to_R(yaw: float):
    return np.array([[np.cos(yaw), -np.sin(yaw)], [np.sin(yaw), np.cos(yaw)]])


def rectangularize(r: Region):
    pts_2d = np.array(r.vertices)

    rect = cv2.minAreaRect(pts_2d.astype(np.float32))
    r.vertices = cv2.boxPoints(rect)

fn = sys.argv[1]
annotations = load(fn)
for r in annotations.regions:
    rectangularize(r)

parts = fn.split('.')
out_fn = parts[0] + '_rectangle.yaml'
save(annotations, out_fn)
