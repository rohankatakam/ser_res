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
    return {
        "loaded": True,
        "algorithm": state.current_algorithm.folder_name,
        "dataset": state.current_dataset.folder_name,
        "total_episodes": len(state.current_dataset.episodes),
        "total_embeddings": len(state.current_embeddings),
        "active_sessions": len(state.sessions),
    }
