"""Paged downloads from ArcGIS REST feature services (used by Steps 1.2 and 1.4)."""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import requests

from crosscheck_pipeline import config


def fetch_all_features(
    layer_url: str,
    params: dict[str, Any],
    *,
    page_size: int = config.ARCGIS_PAGE_SIZE,
    pause_s: float = config.ARCGIS_PAUSE_S,
    retries: int = config.HTTP_RETRIES,
    timeout_s: float = config.HTTP_TIMEOUT_S,
    get: Callable[..., requests.Response] = requests.get,
    sleep: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    """Download every feature of a query as GeoJSON features, one page at a time.

    Requests pages (resultOffset = 0, page_size, 2*page_size, ...) until a page returns fewer
    than `page_size` features. Waits `pause_s` between requests and retries each request up to
    `retries` times. `params` should already include `where`, `outFields`, and `f=geojson`.
    `get` and `sleep` can be swapped out in tests.
    """
    features: list[dict[str, Any]] = []
    offset = 0
    while True:
        page_params = {
            **params,
            "orderByFields": "OBJECTID",
            "resultOffset": offset,
            "resultRecordCount": page_size,
        }
        page = _get_page(f"{layer_url}/query", page_params, retries, timeout_s, get, sleep)
        features.extend(page)
        if len(page) < page_size:
            return features
        offset += page_size
        sleep(pause_s)


def _get_page(
    url: str,
    params: dict[str, Any],
    retries: int,
    timeout_s: float,
    get: Callable[..., requests.Response],
    sleep: Callable[[float], None],
) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            resp = get(url, params=params, timeout=timeout_s)
            resp.raise_for_status()
            body = resp.json()
            if "error" in body:  # ArcGIS reports some failures with HTTP 200
                raise RuntimeError(f"ArcGIS error: {body['error']}")
            return body.get("features", [])
        except (requests.RequestException, RuntimeError, ValueError) as exc:
            last_error = exc
            if attempt < retries - 1:
                sleep(2 * (attempt + 1))
    raise RuntimeError(f"Request failed after {retries} tries: {last_error}")
