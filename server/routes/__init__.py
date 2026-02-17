"""Register all route modules on the FastAPI app."""

from fastapi import FastAPI

from .root import router as root_router
from .config import router as config_router
from .algorithm import router as algorithm_router
from .embeddings import router as embeddings_router
from .sessions import router as sessions_router
from .episodes import router as episodes_router
from .evaluation import router as evaluation_router
from .stats import router as stats_router


def register_routes(app: FastAPI) -> None:
    """Attach all API routers to the app."""
    app.include_router(root_router)
    app.include_router(config_router, prefix="/api/config", tags=["config"])
    app.include_router(algorithm_router, prefix="/api/algorithm", tags=["algorithm"])
    app.include_router(embeddings_router, prefix="/api/embeddings", tags=["embeddings"])
    app.include_router(sessions_router, prefix="/api/sessions", tags=["sessions"])
    app.include_router(episodes_router, prefix="/api/episodes", tags=["episodes"])
    app.include_router(evaluation_router, prefix="/api/evaluation", tags=["evaluation"])
    app.include_router(stats_router, prefix="/api", tags=["stats"])
