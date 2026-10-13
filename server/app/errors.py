"""The app-facing error shape (DESIGN §7.5): {"detail": {"code": "OUTSIDE_AREA", "message": "..."}}."""
from fastapi import HTTPException


class ApiError(HTTPException):
    """An error the mobile app understands: a machine-readable code plus friendly text."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(status_code=status_code, detail={"code": code, "message": message})
