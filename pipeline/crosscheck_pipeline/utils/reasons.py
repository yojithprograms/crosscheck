"""Text helpers for road names and reasons (reasons themselves arrive in Step 1.8)."""


def display_road_name(name: str | None, highway: str | None) -> str:
    """The road's name if it has one, otherwise a plain-English stand-in.

    Anything that shows a road name to a student goes through this (DESIGN §6 Step 1.5).
    """
    if name and name.strip():
        return name.strip()
    if highway == "service":
        return "a driveway or parking lot aisle"
    return "an unnamed street"
