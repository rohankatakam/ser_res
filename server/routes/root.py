"""Root and health endpoints."""

from typing import Tuple

from fastapi import APIRouter

try:
    from ..state import get_state
    from ..services import check_openai_available
except ImportError:
    from state import get_state
    from services import check_openai_available

router = APIRouter()


def _pinecone_available(state) -> Tuple[bool, str]:
    """Return (available, message) for Pinecone vector store."""
    if type(state.vector_store).__name__ != "PineconeVectorStore":
        return False, "PINECONE_API_KEY not set"
    store = getattr(state.vector_store, "_store", None)
    if store is None:
        return False, "Pinecone not configured"
    try:
        ok = getattr(store, "is_available", lambda: False)()
        return ok, "connected" if ok else "not reachable"
    except Exception as e:
        return False, str(e)


def _embeddings_count(state) -> int:
    """Return embedding count (from memory or Pinecone namespace when using Pinecone)."""
    n = len(state.current_embeddings)
    if n == 0 and state.is_loaded and hasattr(state.vector_store, "get_vector_count"):
        n = state.vector_store.get_vector_count(
            state.current_algorithm.folder_name,
            state.current_algorithm.strategy_version,
            state.current_dataset.folder_name,
        )
    return n


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
            "embeddings_count": _embeddings_count(state),
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
    pinecone_ok, pinecone_msg = _pinecone_available(state)
    return {
        "status": "healthy",
        "loaded": state.is_loaded,
        "openai": {"available": openai_ok, "message": openai_msg},
        "pinecone": {"available": pinecone_ok, "message": pinecone_msg},
    }
