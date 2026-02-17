"""Episode catalog endpoints."""

from fastapi import APIRouter, HTTPException, Query

try:
    from ..state import get_state
except ImportError:
    from state import get_state

router = APIRouter()


@router.get("")
def list_episodes(limit: int = Query(None), offset: int = Query(0)):
    """List episodes from current dataset."""
    state = get_state()
    if not state.current_dataset:
        raise HTTPException(status_code=400, detail="No dataset loaded")
    episodes = state.current_dataset.episodes
    paginated = episodes[offset : offset + limit] if limit else episodes[offset:]
    return {
        "episodes": paginated,
        "total": len(episodes),
        "offset": offset,
        "limit": limit,
    }


@router.get("/{episode_id}")
def get_episode(episode_id: str):
    """Get episode details."""
    state = get_state()
    if not state.current_dataset:
        raise HTTPException(status_code=400, detail="No dataset loaded")
    ep = state.current_dataset.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    return ep
