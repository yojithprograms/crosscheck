from fastapi import APIRouter, Depends

from app.deps import get_store
from app.routing import compare_routes
from app.schemas import RouteComparison, RouteRequest
from app.store import DataStore

router = APIRouter()


@router.post("/routes", response_model=RouteComparison)
def post_routes(request: RouteRequest, store: DataStore = Depends(get_store)) -> RouteComparison:
    """Fastest vs. lower-risk route to school. The start point is used, then forgotten (never stored or logged)."""
    return compare_routes(store, request.school_id, request.origin.lat, request.origin.lon, request.mode)
