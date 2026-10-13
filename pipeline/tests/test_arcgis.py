from typing import Any

import pytest
import requests

from crosscheck_pipeline.utils.arcgis import fetch_all_features


class FakeResponse:
    def __init__(self, body: dict[str, Any], status: int = 200) -> None:
        self._body = body
        self.status_code = status

    def json(self) -> dict[str, Any]:
        return self._body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeServer:
    """Pretends to be an ArcGIS layer holding `n_features` features; records every request."""

    def __init__(self, n_features: int, fail_first: int = 0, error_body: bool = False) -> None:
        self.n_features = n_features
        self.fail_first = fail_first
        self.error_body = error_body
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, params: dict[str, Any], timeout: float) -> FakeResponse:
        self.calls.append(params)
        if len(self.calls) <= self.fail_first:
            raise requests.ConnectionError("boom")
        if self.error_body:
            return FakeResponse({"error": {"code": 400, "message": "bad query"}})
        start = params["resultOffset"]
        stop = min(start + params["resultRecordCount"], self.n_features)
        return FakeResponse({"features": [{"id": i} for i in range(start, stop)]})


def run(server: FakeServer, page_size: int = 2, retries: int = 3):
    sleeps: list[float] = []
    features = fetch_all_features(
        "http://example/layer", {"where": "1=1", "f": "geojson"},
        page_size=page_size, pause_s=0.5, retries=retries, get=server.get, sleep=sleeps.append,
    )
    return features, sleeps


def test_pages_until_a_short_page() -> None:
    server = FakeServer(5)
    features, sleeps = run(server)
    assert [f["id"] for f in features] == [0, 1, 2, 3, 4]
    assert [c["resultOffset"] for c in server.calls] == [0, 2, 4]
    assert sleeps == [0.5, 0.5]  # a pause between pages, none after the last


def test_exact_multiple_ends_with_an_empty_page() -> None:
    server = FakeServer(4)
    features, _ = run(server)
    assert len(features) == 4
    assert [c["resultOffset"] for c in server.calls] == [0, 2, 4]


def test_empty_layer() -> None:
    features, _ = run(FakeServer(0))
    assert features == []


def test_query_params_are_passed_on() -> None:
    server = FakeServer(1)
    run(server)
    assert server.calls[0]["where"] == "1=1"
    assert server.calls[0]["orderByFields"] == "OBJECTID"
    assert server.calls[0]["resultRecordCount"] == 2


def test_retries_then_succeeds() -> None:
    server = FakeServer(1, fail_first=2)
    features, sleeps = run(server, retries=3)
    assert len(features) == 1
    assert len(server.calls) == 3
    assert sleeps == [2, 4]  # backoff between the failed attempts


def test_gives_up_after_retries() -> None:
    server = FakeServer(1, fail_first=10)
    with pytest.raises(RuntimeError, match="failed after 3 tries"):
        run(server, retries=3)
    assert len(server.calls) == 3


def test_arcgis_error_body_is_treated_as_failure() -> None:
    with pytest.raises(RuntimeError, match="failed after 3 tries"):
        run(FakeServer(1, error_body=True), retries=3)
