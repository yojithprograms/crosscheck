"""OSMnx helpers shared by Steps 1.3 and 1.10."""
from pathlib import Path

import osmnx as ox

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "osmnx_cache"


def configure_osmnx() -> None:
    """Keep the OSM tags we need and cache downloads, so reruns (and `run_all --from s10`) are fast."""
    ox.settings.use_cache = True
    ox.settings.cache_folder = str(CACHE_DIR)
    ox.settings.log_console = True
    for tag in ["footway", "sidewalk", "crossing", "cycleway"]:
        if tag not in ox.settings.useful_tags_way:
            ox.settings.useful_tags_way.append(tag)
    if "crossing" not in ox.settings.useful_tags_node:
        ox.settings.useful_tags_node.append("crossing")
