from model import GeoReference
from fetch import latlon_to_utm, utm_to_latlon


def pixel_to_local_utm(px, py, georef: GeoReference):
    """Pixel (x right, y down) → Local UTM (easting, northing) relative to georef LL corner in metres."""
    easting, northing = pixel_to_utm(px, py, georef)
    local_easting = easting - georef.utm_left
    local_northing = northing - georef.utm_bottom

    return local_easting, local_northing


def pixel_to_utm(px, py, georef: GeoReference):
    """Pixel (x right, y down) → UTM (easting, northing) in metres."""
    easting = georef.utm_left + px * georef.resolution_x
    northing = georef.utm_top - py * georef.resolution_y  # y is flipped
    return easting, northing


def utm_to_pixel(easting, northing, georef: GeoReference):
    """UTM (easting, northing) → pixel (x, y)."""
    px = (easting - georef.utm_left) / georef.resolution_x
    py = (georef.utm_top - northing) / georef.resolution_y
    return px, py


def pixel_to_latlon(px, py, georef: GeoReference):
    """Pixel → (lat, lon) in degrees."""
    easting, northing = pixel_to_utm(px, py, georef)
    lon, lat = utm_to_latlon(easting, northing, georef.utm_epsg)
    return lat, lon


def latlon_to_pixel(lat, lon, georef: GeoReference):
    """(lat, lon) degrees → pixel (x, y)."""
    easting, northing = latlon_to_utm(lon, lat, georef.utm_epsg)
    return utm_to_pixel(easting, northing, georef)


def region_vertices_utm(region, georef: GeoReference):
    """Return all vertices as [(easting, northing), ...]."""
    return [pixel_to_utm(x, y, georef) for x, y in region.vertices]


def region_vertices_latlon(region, georef: GeoReference):
    """Return all vertices as [(lat, lon), ...]."""
    return [pixel_to_latlon(x, y, georef) for x, y in region.vertices]
