"""Road names shown to students (a copy of the pipeline's display_road_name, DESIGN §6 Step 1.5)."""


def display_road_name(name: str | None, highway: str | None) -> str:
    """The road's name if it has one, otherwise a plain-English stand-in."""
    if name and name.strip():
        return name.strip()
    if highway == "service":
        return "a driveway or parking lot aisle"
    return "an unnamed street"
