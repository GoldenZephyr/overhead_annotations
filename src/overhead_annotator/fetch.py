import contextily as cx
import numpy as np
from pyproj import Transformer, CRS
import math

ESRI_SATELLITE = cx.providers.Esri.WorldImagery

# ---- UTM zone detection ----

def utm_epsg_from_latlon(lat, lon):
    """Return the EPSG code for the UTM zone covering (lat, lon)."""
    zone_number = int((lon + 180) / 6) + 1
    if lat >= 0:
        return 32600 + zone_number   # North
    else:
        return 32700 + zone_number   # South


def _make_transformers(utm_epsg):
    to_utm     = Transformer.from_crs("EPSG:4326", f"EPSG:{utm_epsg}", always_xy=True)
    from_utm   = Transformer.from_crs(f"EPSG:{utm_epsg}", "EPSG:4326", always_xy=True)
    merc_to_utm = Transformer.from_crs("EPSG:3857", f"EPSG:{utm_epsg}", always_xy=True)
    return to_utm, from_utm, merc_to_utm


def latlon_to_utm(lon, lat, utm_epsg):
    to_utm, _, _ = _make_transformers(utm_epsg)
    return to_utm.transform(lon, lat)


def utm_to_latlon(easting, northing, utm_epsg):
    _, from_utm, _ = _make_transformers(utm_epsg)
    return from_utm.transform(easting, northing)  # returns (lon, lat)


# ---- Tile fetching ----

def fetch_image(
    lat_south: float,
    lon_west: float,
    lat_north: float,
    lon_east: float,
    zoom="auto",
    source=ESRI_SATELLITE,
) -> tuple[np.ndarray, dict]:
    """
    Fetch tiles in Web Mercator (contextily requirement),
    then compute UTM bounds for geo-referencing.
    """
    # Auto-detect UTM zone from center of bbox
    center_lat = (lat_south + lat_north) / 2
    center_lon = (lon_west + lon_east) / 2
    utm_epsg = utm_epsg_from_latlon(center_lat, center_lon)

    # Contextily needs Web Mercator
    to_merc = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    xmin, ymin = to_merc.transform(lon_west, lat_south)
    xmax, ymax = to_merc.transform(lon_east, lat_north)

    img, extent = cx.bounds2img(
        xmin, ymin, xmax, ymax,
        zoom=zoom, source=source, ll=False,
    )
    # extent = (left, right, bottom, top) in Web Mercator
    ext_left, ext_right, ext_bottom, ext_top = extent
    h, w = img.shape[:2]

    # Convert image corners from Mercator → UTM
    _, _, merc_to_utm = _make_transformers(utm_epsg)
    utm_left,  utm_bottom = merc_to_utm.transform(ext_left,  ext_bottom)
    utm_right, utm_top    = merc_to_utm.transform(ext_right, ext_top)

    geo = {
        "utm_epsg":    utm_epsg,
        "utm_left":    utm_left,
        "utm_right":   utm_right,
        "utm_bottom":  utm_bottom,
        "utm_top":     utm_top,
        "image_width":  w,
        "image_height": h,
    }

    return img, geo


def save_image(img: np.ndarray, path: str):
    from PIL import Image
    Image.fromarray(img).save(path)
