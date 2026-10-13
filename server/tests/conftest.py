import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.mini_data import write_mini_data


@pytest.fixture
def mini_data_dir(tmp_path):
    """The default mini school (no risky edges) written into a temp folder."""
    return write_mini_data(tmp_path / "data")


@pytest.fixture
def make_client(tmp_path):
    """Build a client for a mini school with custom edges. Use as a context manager so startup runs."""
    counter = {"n": 0}

    def make(**overrides) -> TestClient:
        counter["n"] += 1
        data_dir = write_mini_data(tmp_path / f"data{counter['n']}", **overrides)
        settings = Settings(data_dir=data_dir, database_url="sqlite://", admin_token="test-admin")
        return TestClient(create_app(settings))

    return make


@pytest.fixture
def client(make_client):
    with make_client() as test_client:
        yield test_client
