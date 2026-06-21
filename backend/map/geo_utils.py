"""Web-Mercator tile coordinate utilities (EPSG:3857 / OSM standard)."""
import math
from typing import Tuple


def lat_lon_to_tile_float(lat: float, lon: float, zoom: int) -> Tuple[float, float]:
    """Return fractional tile (x, y) for a geographic coordinate at a zoom level."""
    n = 2.0 ** zoom
    x = (lon + 180.0) / 360.0 * n
    lat_r = math.radians(lat)
    y = (1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n
    return x, y


def tile_float_to_lat_lon(tx: float, ty: float, zoom: int) -> Tuple[float, float]:
    """Return (lat, lon) for a fractional tile coordinate."""
    n = 2.0 ** zoom
    lon = tx / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * ty / n))))
    return lat, lon


def clamp_lat(lat: float) -> float:
    return max(-85.051129, min(85.051129, lat))


def clamp_lon(lon: float) -> float:
    return max(-180.0, min(180.0, lon))


def clamp_zoom(zoom: int, lo: int = 1, hi: int = 19) -> int:
    return max(lo, min(hi, zoom))
