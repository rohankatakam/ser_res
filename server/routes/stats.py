"""Stats endpoint."""

from fastapi import APIRouter

try:
    from ..state import get_state
except ImportError:
    from state import get_state

router = APIRouter()


@router.get("/stats")
def get_stats():
    """Get current statistics."""
    state = get_state()
    if not state.is_loaded:
        return {"loaded": False, "message": "No configuration loaded"}
    # With Pinecone we don't load embeddings into memory; get count from vector store when available
    total_embeddings = len(state.current_embeddings)
    if total_embeddings == 0 and hasattr(state.vector_store, "get_vector_count"):
        total_embeddings = state.vector_store.get_vector_count(
            state.current_algorithm.folder_name,
            state.current_algorithm.strategy_version,
            state.current_dataset.folder_name,
        )
        print(
            f"[stats] Pinecone namespace "
            f"algo={state.current_algorithm.folder_name!r} strategy={state.current_algorithm.strategy_version!r} "
            f"dataset={state.current_dataset.folder_name!r} -> total_embeddings={total_embeddings}"
        )
    return {
        "loaded": True,
        "algorithm": state.current_algorithm.folder_name,
        "dataset": state.current_dataset.folder_name,
        "total_episodes": len(state.current_dataset.episodes),
        "total_embeddings": total_embeddings,
        "active_sessions": len(state.sessions),
    }
