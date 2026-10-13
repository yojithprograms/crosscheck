"""Shared FastAPI dependencies."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

from app.errors import ApiError

if TYPE_CHECKING:
    from app.store import DataStore


def get_store(request: Request) -> DataStore:
    store = getattr(request.app.state, "store", None)
    if store is None:
        raise ApiError(503, "DATA_NOT_READY", "The map data isn't loaded yet. Please try again in a moment.")
    return store
