"""Shared FastAPI dependencies and the app-facing error shape (DESIGN §7.5)."""
from fastapi import HTTPException, Request

from app.store import DataStore


class ApiError(HTTPException):
    """Errors the app understands: {"detail": {"code": "OUTSIDE_AREA", "message": "..."}}."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


def get_store(request: Request) -> DataStore:
    store = getattr(request.app.state, "store", None)
    if store is None:
        raise ApiError(503, "DATA_NOT_READY", "The map data isn't loaded yet. Please try again in a moment.")
    return store
