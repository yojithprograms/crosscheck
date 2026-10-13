from typing import Any

from fastapi import APIRouter, Depends, Response

from app.deps import get_store
from app.errors import ApiError
from app.names import display_road_name
from app.schemas import School, SegmentDetail
from app.store import DataStore, SchoolData

router = APIRouter()

# Map layers only change when the pipeline is rerun, so phones may reuse them for a while.
STATIC_CACHE = "public, max-age=3600"
UNKNOWN_SCHOOL_MESSAGE = "This school's map isn't ready yet."


def get_school(school_id: str, store: DataStore) -> SchoolData:
    school = store.schools.get(school_id)
    if school is None:
        raise ApiError(404, "UNKNOWN_SCHOOL", UNKNOWN_SCHOOL_MESSAGE)
    return school


@router.get("/schools", response_model=list[School])
def list_schools(store: DataStore = Depends(get_store)) -> list[dict[str, Any]]:
    """The pilot schools."""
    return store.school_list()


@router.get("/schools/{school_id}/risk-layer")
def risk_layer(school_id: str, response: Response, store: DataStore = Depends(get_store)) -> dict[str, Any]:
    """Medium and high risk streets near the school (GeoJSON)."""
    response.headers["Cache-Control"] = STATIC_CACHE
    return get_school(school_id, store).risk_layer


@router.get("/schools/{school_id}/crashes")
def crashes(school_id: str, response: Response, store: DataStore = Depends(get_store)) -> dict[str, Any]:
    """Past pedestrian and bike crashes near the school (GeoJSON points: year, month, severity, mode)."""
    response.headers["Cache-Control"] = STATIC_CACHE
    return get_school(school_id, store).crash_layer


@router.get("/segments/{school_id}/{seg_id}", response_model=SegmentDetail)
def segment_detail(school_id: str, seg_id: str, store: DataStore = Depends(get_store)) -> SegmentDetail:
    """Details for one street: risk, plain-English reasons, and facts (for the street card)."""
    segment = get_school(school_id, store).segments.get(seg_id)
    if segment is None:
        raise ApiError(404, "UNKNOWN_SEGMENT", "We couldn't find that street.")
    return SegmentDetail(
        seg_id=seg_id,
        name=display_road_name(segment["name"], segment["highway"]),
        risk_pct=segment["risk_pct"], risk_class=segment["risk_class"], reasons=segment["reasons"],
        speed_mph=segment["speed_mph"], speed_imputed=bool(segment["speed_imputed"]), lanes=segment["lanes"],
        sidewalk_cov=segment["sidewalk_cov"], sidewalk_known=bool(segment["sidewalk_known"]),
        crashes_recent=segment["crashes_recent"], crashes_recent_ka=segment["crashes_recent_ka"],
        crashes_prelim=segment["crashes_prelim"],
        reports_recent=0,   # live report counts arrive with the reports feature (Step 5.1)
    )
