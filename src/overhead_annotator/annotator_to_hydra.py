from overhead_annotator.serde import load
from overhead_annotator.model import Region
from overhead_annotator.geo import pixel_to_local_utm
import numpy as np
import cv2
import yaml
from scipy.spatial.transform import Rotation as R


def yaw_to_R(yaw: float):
    return np.array([[np.cos(yaw), -np.sin(yaw)], [np.sin(yaw), np.cos(yaw)]])


def rectangularize(r: Region):
    pts_2d = np.array(r.vertices)

    rect = cv2.minAreaRect(pts_2d.astype(np.float32))
    r.vertices = cv2.boxPoints(rect)


region_id_to_rectangles = {}
region_id_to_semantic_class = {}

annotations = load("rectangular_annotations.yaml")
for r in annotations.regions:
    assert r.label.startswith("r")
    room_idx = int(r.label[1:])
    if room_idx not in region_id_to_rectangles:
        region_id_to_rectangles[room_idx] = []

    local_pts = np.array(
        [pixel_to_local_utm(*px, annotations.georef) for px in r.vertices]
    )
    center = np.mean(local_pts, axis=0)
    center_3d = np.zeros(3)
    center_3d[:2] = center

    w = float(np.linalg.norm(local_pts[1] - local_pts[0]))
    h = float(np.linalg.norm(local_pts[-1] - local_pts[0]))
    dz = 5
    extents = [w, h, dz]

    u = (local_pts[1] - local_pts[0]) / w
    yaw = np.arctan2(u[1], u[0])

    rot = R.from_euler("z", yaw)

    # Output as [x, y, z, w]
    x, y, z, w = rot.as_quat()
    quat = {"x": float(x), "y": float(y), "z": float(z), "w": float(w)}

    box = {"center": center_3d.tolist(), "extents": extents, "rotation": quat}
    region_id_to_rectangles[room_idx].append(box)


with open("gt_rooms_for_hydra.yaml", "w") as fo:
    yaml.dump(region_id_to_rectangles, fo, sort_keys=True)
