"""Small geometry helpers. Distances inside a school's area use "flat-earth meters", which is
accurate to well under 1% over a few kilometers and cheap enough to do with numpy."""
from __future__ import annotations

import math

import numpy as np

from app import config


def flat_distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Distance in meters between two points: dx = Δlon × cos(lat) × 111320, dy = Δlat × 110540."""
    dx = (lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2)) * config.METERS_PER_DEG_LON_AT_EQUATOR
    dy = (lat2 - lat1) * config.METERS_PER_DEG_LAT
    return math.hypot(dx, dy)


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in meters."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((phi2 - phi1) / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * config.EARTH_RADIUS_M * math.asin(math.sqrt(a))


def flat_distances_m(lons: np.ndarray, lats: np.ndarray, lon: float, lat: float) -> np.ndarray:
    """Flat-earth meters from one point to many (numpy arrays of lon and lat)."""
    dx = (lons - lon) * math.cos(math.radians(lat)) * config.METERS_PER_DEG_LON_AT_EQUATOR
    dy = (lats - lat) * config.METERS_PER_DEG_LAT
    return np.hypot(dx, dy)


def nearest_index(lons: np.ndarray, lats: np.ndarray, lon: float, lat: float) -> tuple[int, float]:
    """(position, distance in meters) of the closest point in the arrays."""
    distances = flat_distances_m(lons, lats, lon, lat)
    position = int(np.argmin(distances))
    return position, float(distances[position])
