"""Root and health endpoints."""

from fastapi import APIRouter

try:
    from ..state import get_state
    from ..services import check_openai_available, check_qdrant_available
except ImportError:
    from state import get_state
    from services import check_openai_available, check_qdrant_available

router = APIRouter()


@router.get("/")
def root():
    state = get_state()
    return {
        "name": "Serafis Evaluation Framework API",
        "version": "2.0.0",
        "status": "loaded" if state.is_loaded else "not_configured",
        "current": {
            "algorithm": state.current_algorithm.folder_name if state.current_algorithm else None,
            "dataset": state.current_dataset.folder_name if state.current_dataset else None,
            "embeddings_count": len(state.current_embeddings),
        },
        "available": {
            "algorithms": len(state.algorithm_loader.list_algorithms()),
            "datasets": len(state.dataset_loader.list_datasets()),
        },
        "endpoints": {
            "config": ["/api/config/algorithms", "/api/config/datasets", "/api/config/load"],
            "embeddings": ["/api/embeddings/status", "/api/embeddings/generate"],
            "recommendations": ["/api/sessions/create", "/api/sessions/{id}/next"],
            "evaluation": ["/api/evaluation/profiles", "/api/evaluation/test-cases", "/api/evaluation/run"],
        },
    }


@router.get("/api/health")
def health():
    state = get_state()
    openai_ok, openai_msg = check_openai_available()
    qdrant_ok, qdrant_msg = check_qdrant_available(state.config.qdrant_url)
    return {
        "status": "healthy",
        "loaded": state.is_loaded,
        "openai": {"available": openai_ok, "message": openai_msg},
        "qdrant": {"available": qdrant_ok, "message": qdrant_msg},
    }
