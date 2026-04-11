from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class GeoReference:
    """UTM-based geo-reference for the overhead image."""
    utm_epsg: int          # e.g. 32617 for UTM zone 17N
    utm_left: float        # easting of left image edge (metres)
    utm_right: float       # easting of right image edge
    utm_bottom: float      # northing of bottom image edge
    utm_top: float         # northing of top image edge
    image_width: int       # pixels
    image_height: int      # pixels

    @property
    def resolution_x(self) -> float:
        """Metres per pixel in x (easting)."""
        return (self.utm_right - self.utm_left) / self.image_width

    @property
    def resolution_y(self) -> float:
        """Metres per pixel in y (northing)."""
        return (self.utm_top - self.utm_bottom) / self.image_height



@dataclass
class Region:
    id: str
    label: str
    vertices: List[Tuple[float, float]]   # pixel coords (x, y)
    tags: List[str] = field(default_factory=list)


@dataclass
class MapAnnotation:
    image_path: str
    regions: List[Region] = field(default_factory=list)
    georef: Optional[GeoReference] = None
