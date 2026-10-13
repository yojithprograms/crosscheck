"""OSMnx helpers shared by Steps 1.3 and 1.10."""
from pathlib import Path

import osmnx as ox
import osmnx._http as osmnx_http

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "osmnx_cache"


def skip_osmnx_dns_pinning() -> None:
    """Stop OSMnx from pinning every Overpass request to one IPv4 address.

    OSMnx calls socket.gethostbyname() and forces all requests onto the single address it returns.
    overpass-api.de is a round-robin of several servers; on 2026-10-12 the first one it returned
    (162.55.144.139) was down, so every request timed out even though the other servers worked.
    Skipping the pinning lets Python try each address in turn. The cost is that OSMnx can't keep
    its server-slot checks on one machine, which doesn't matter for our handful of requests.
    """
    osmnx_http._config_dns = lambda url: None


def configure_osmnx() -> None:
    """Keep the OSM tags we need and cache downloads, so reruns (and `run_all --from s10`) are fast."""
    skip_osmnx_dns_pinning()
    ox.settings.use_cache = True
    ox.settings.cache_folder = str(CACHE_DIR)
    ox.settings.log_console = True
    for tag in ["footway", "sidewalk", "crossing", "cycleway"]:
        if tag not in ox.settings.useful_tags_way:
            ox.settings.useful_tags_way.append(tag)
    if "crossing" not in ox.settings.useful_tags_node:
        ox.settings.useful_tags_node.append("crossing")
