from typing import Any

from fastapi import APIRouter, Depends

from app.deps import get_store
from app.store import DataStore

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Alive check. The app calls it at launch, which also wakes a sleeping host."""
    return {"status": "ok"}


@router.get("/meta")
def meta(store: DataStore = Depends(get_store)) -> dict[str, Any]:
    """Data dates and model accuracy (for the "How risk scores work" screen)."""
    return store.meta
