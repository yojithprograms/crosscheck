"""The API contract: request and response shapes (DESIGN §7.5). The mobile app's types mirror these."""
from typing import Literal

from pydantic import BaseModel, Field


class School(BaseModel):
    id: str
    name: str
    level: Literal["ES", "MS", "HS"]
    lat: float          # the main entrance
    lon: float
    radius_m: int
    bbox: list[float]   # [min_lon, min_lat, max_lon, max_lat] of the covered area


class LatLon(BaseModel):
    """Requests send points as objects. (Responses use GeoJSON order [lon, lat].)"""

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class RouteRequest(BaseModel):
    school_id: str
    origin: LatLon
    mode: Literal["walk", "bike"] = "walk"     # "bike" also covers scooters


class Hazard(BaseModel):
    n: int                                      # 1, 2, 3... in path order
    kind: Literal["crossing", "intersection", "along", "reported"]
    title: str
    lon: float
    lat: float
    risk_pct: float
    risk_class: Literal["low", "medium", "high"]
    reasons: list[str]
    report_count: int
    report_types: list[str]
    seg_id: str | None


class Route(BaseModel):
    distance_m: int
    duration_min: int
    polyline: list[list[float]]                 # [[lon, lat], ...]
    high_count: int
    medium_count: int
    report_spot_count: int
    mean_risk_pct: float
    hazards: list[Hazard]


class RouteComparison(BaseModel):
    school_id: str
    mode: Literal["walk", "bike"]
    same_route: bool
    fastest: Route
    lower_risk: Route
    notes: list[str]


class SegmentDetail(BaseModel):
    seg_id: str
    name: str                      # already a student-friendly name (never empty)
    risk_pct: float
    risk_class: Literal["low", "medium", "high"]
    reasons: list[str]
    speed_mph: int
    speed_imputed: bool
    lanes: int
    sidewalk_cov: float
    sidewalk_known: bool
    crashes_recent: int
    crashes_recent_ka: int
    crashes_prelim: int
    reports_recent: int            # confirmed student reports on this street in the last 6 months
