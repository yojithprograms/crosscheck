"""The CrossCheck API. Run with: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.routers import meta
from app.store import DataStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")
logger = logging.getLogger("crosscheck")


def create_app(settings: Settings | None = None) -> FastAPI:
    """App factory. Tests pass their own settings (a small fixture school instead of the real data)."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            app.state.store = DataStore.load(settings.data_dir)
            logger.info("data store ready: %d schools", len(app.state.store.schools))
        except FileNotFoundError as error:
            app.state.store = None
            logger.warning("starting without data: %s", error)
        yield

    app = FastAPI(title="CrossCheck API", lifespan=lifespan)
    app.state.settings = settings
    app.state.store = None
    app.include_router(meta.router)
    return app


app = create_app()
