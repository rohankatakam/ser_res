"""Session and recommendation endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

try:
    from ..state import get_state
    from ..utils import to_episode_card, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
    from ..models import (
        CreateSessionRequest,
        EngageRequest,
        LoadMoreRequest,
        SessionDebugInfo,
        SessionResponse,
    )
except ImportError:
    from state import get_state
    from utils import to_episode_card, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
    from models import (
        CreateSessionRequest,
        EngageRequest,
        LoadMoreRequest,
        SessionDebugInfo,
        SessionResponse,
    )

router = APIRouter()


@router.post("/create", response_model=SessionResponse)
def create_session(request: CreateSessionRequest):
    """Create a new recommendation session."""
    state = get_state()
    if not state.is_loaded:
        raise HTTPException(
            status_code=400,
            detail="No algorithm/dataset loaded. Call /api/config/load first.",
        )
    engine = state.current_algorithm.engine_module
    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Algorithm does not have a recommendation engine",
        )
    request_engagements = [e.model_dump() for e in request.engagements]
    engagements = state.engagement_store.get_engagements_for_session(None, request_engagements)
    excluded_ids = set(request.excluded_ids)
    for eng in request.engagements:
        excluded_ids.add(eng.episode_id)
    if state.current_episode_provider:
        episodes = state.current_episode_provider.get_episodes(limit=None)
        episode_by_content_id = state.current_episode_provider.get_episode_by_content_id_map()
    else:
        episodes = state.current_dataset.episodes
        episode_by_content_id = state.current_dataset.episode_by_content_id
    algo_config = None
    if state.current_algorithm.config and hasattr(engine, "RecommendationConfig"):
        algo_config = engine.RecommendationConfig.from_dict(state.current_algorithm.config)
    queue, cold_start, user_vector_episodes = engine.create_recommendation_queue(
        engagements=engagements,
        excluded_ids=excluded_ids,
        episodes=episodes,
        embeddings=state.current_embeddings,
        episode_by_content_id=episode_by_content_id,
        config=algo_config,
    )
    session_id = str(uuid.uuid4())[:8]
    session = {
        "session_id": session_id,
        "queue": queue,
        "shown_indices": set(),
        "engaged_ids": set(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cold_start": cold_start,
        "user_vector_episodes": user_vector_episodes,
        "excluded_ids": excluded_ids.copy(),
    }
    state.sessions[session_id] = session
    first_page = []
    for i, scored_ep in enumerate(queue[:DEFAULT_PAGE_SIZE]):
        first_page.append((scored_ep, i + 1))
        session["shown_indices"].add(i)
    episodes_out = [to_episode_card(scored.episode, scored, pos) for scored, pos in first_page]
    total_in_queue = len(queue)
    shown_count = len(session["shown_indices"])
    debug = SessionDebugInfo(
        candidates_count=total_in_queue,
        user_vector_episodes=user_vector_episodes,
        embeddings_available=len(state.current_embeddings) > 0,
        top_similarity_scores=[round(s.similarity_score, 3) for s, _ in first_page[:5]],
        top_quality_scores=[round(s.quality_score, 3) for s, _ in first_page[:5]],
        top_final_scores=[round(s.final_score, 3) for s, _ in first_page[:5]],
        scoring_weights={"similarity": 0.55, "quality": 0.30, "recency": 0.15},
    )
    return SessionResponse(
        session_id=session_id,
        episodes=episodes_out,
        total_in_queue=total_in_queue,
        shown_count=shown_count,
        remaining_count=total_in_queue - shown_count,
        cold_start=cold_start,
        algorithm=f"v{state.current_algorithm.manifest.version}",
        debug=debug,
    )


@router.get("/{session_id}")
def get_session_info(session_id: str):
    """Get session info."""
    state = get_state()
    session = state.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    total = len(session["queue"])
    shown = len(session["shown_indices"])
    return {
        "session_id": session_id,
        "total_in_queue": total,
        "shown_count": shown,
        "remaining_count": total - shown,
        "cold_start": session["cold_start"],
        "created_at": session["created_at"],
        "engaged_count": len(session["engaged_ids"]),
    }


@router.post("/{session_id}/next", response_model=SessionResponse)
def load_more(session_id: str, request: LoadMoreRequest = None):
    """Load more recommendations from session."""
    state = get_state()
    session = state.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    limit = min(request.limit if request else DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
    queue = session["queue"]
    shown = session["shown_indices"]
    engaged = session["engaged_ids"]
    next_page = []
    for i, scored_ep in enumerate(queue):
        if i in shown:
            continue
        ep = scored_ep.episode.model_dump() if hasattr(scored_ep.episode, "model_dump") else scored_ep.episode
        if ep["id"] in engaged or ep.get("content_id") in engaged:
            continue
        next_page.append((scored_ep, i + 1))
        shown.add(i)
        if len(next_page) >= limit:
            break
    episodes_out = [to_episode_card(scored.episode, scored, pos) for scored, pos in next_page]
    total_in_queue = len(queue)
    shown_count = len(shown)
    return SessionResponse(
        session_id=session_id,
        episodes=episodes_out,
        total_in_queue=total_in_queue,
        shown_count=shown_count,
        remaining_count=total_in_queue - shown_count,
        cold_start=session["cold_start"],
        algorithm=f"v{state.current_algorithm.manifest.version}" if state.current_algorithm else "unknown",
    )


@router.post("/{session_id}/engage")
def engage_episode(session_id: str, request: EngageRequest):
    """Record an engagement."""
    state = get_state()
    session = state.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session["engaged_ids"].add(request.episode_id)
    session["excluded_ids"].add(request.episode_id)
    state.engagement_store.record_engagement(
        None,
        request.episode_id,
        request.type,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return {
        "status": "ok",
        "session_id": session_id,
        "episode_id": request.episode_id,
        "type": request.type,
        "engaged_count": len(session["engaged_ids"]),
    }
