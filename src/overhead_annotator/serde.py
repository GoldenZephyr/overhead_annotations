import yaml
from model import Region, MapAnnotation, GeoReference


def _sanitize_vertex(v):
    """Ensure vertex is a plain [float, float] list — no numpy, no tuple."""
    return [float(v[0]), float(v[1])]


def _sanitize_region(r: Region) -> dict:
    return {
        "id":       str(r.id),
        "label":    str(r.label),
        "vertices": [_sanitize_vertex(v) for v in r.vertices],
        "tags":     [str(t) for t in r.tags],
    }


def _georef_to_dict(g: GeoReference) -> dict:
    return {
        "utm_epsg":     int(g.utm_epsg),
        "utm_left":     float(g.utm_left),
        "utm_right":    float(g.utm_right),
        "utm_bottom":   float(g.utm_bottom),
        "utm_top":      float(g.utm_top),
        "image_width":  int(g.image_width),
        "image_height": int(g.image_height),
    }


def _dict_to_georef(d: dict) -> GeoReference:
    return GeoReference(
        utm_epsg=int(d["utm_epsg"]),
        utm_left=float(d["utm_left"]),
        utm_right=float(d["utm_right"]),
        utm_bottom=float(d["utm_bottom"]),
        utm_top=float(d["utm_top"]),
        image_width=int(d["image_width"]),
        image_height=int(d["image_height"]),
    )


def save(annotation: MapAnnotation, path: str):
    data = {
        "image_path": str(annotation.image_path),
        "georef":     _georef_to_dict(annotation.georef) if annotation.georef else None,
        "regions":    [_sanitize_region(r) for r in annotation.regions],
    }
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def load(path: str) -> MapAnnotation:
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    regions = [
        Region(
            id=r["id"],
            label=r["label"],
            vertices=[(float(v[0]), float(v[1])) for v in r["vertices"]],
            tags=r.get("tags", []),
        )
        for r in data.get("regions", [])
    ]
    georef = _dict_to_georef(data["georef"]) if data.get("georef") else None
    return MapAnnotation(
        image_path=data["image_path"],
        regions=regions,
        georef=georef,
    )
