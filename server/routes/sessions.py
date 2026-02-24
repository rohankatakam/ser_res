"""Session and recommendation endpoints."""

import asyncio
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


def _episode_dicts(episodes) -> list:
    """Normalize episodes to list of dicts for engine and get_candidate_pool_ids."""
    out = []
    for ep in episodes or []:
        if hasattr(ep, "model_dump"):
            out.append(ep.model_dump())
        elif isinstance(ep, dict):
            out.append(ep)
        else:
            out.append(dict(ep))
    return out


def _episode_by_content_id_from_list(episode_list: list) -> dict:
    """Build content_id -> episode dict from episode list. Includes id for query result lookup."""
    out = {}
    for ep in episode_list:
        if not isinstance(ep, dict):
            continue
        cid = ep.get("content_id")
        if cid:
            out[cid] = ep
        eid = ep.get("id")
        if eid and eid != cid:
            out[eid] = ep
    return out


def _log_sessions(msg: str) -> None:
    """Log to stdout with flush so Docker/capture shows it immediately."""
    print(f"[sessions] {msg}", flush=True)


@router.post("/create", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new recommendation session. Fetches engagements, user, and episodes in parallel when using Firestore."""
    _log_sessions("create_session started")
    try:
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
        user_id = getattr(request, "user_id", None)
        user_store = getattr(state, "user_store", None)
        episode_provider = state.current_episode_provider
        _log_sessions(f"gathering data: user_id={user_id!r}, has_episode_provider={episode_provider is not None}")

        async def _get_engagements():
            _log_sessions("_get_engagements started")
            store = state.engagement_store
            if not hasattr(store, "get_engagements_for_ranking_async"):
                raise RuntimeError("Engagement store must support get_engagements_for_ranking_async (async only)")
            out = await store.get_engagements_for_ranking_async(user_id, request_engagements)
            _log_sessions(f"_get_engagements done: {len(out or [])} items")
            return out

        async def _get_user():
            _log_sessions("_get_user started")
            if not user_id or not user_id.strip() or not user_store:
                _log_sessions("_get_user done: skipped (no user_id/store)")
                return None
            if not hasattr(user_store, "get_by_id_async"):
                raise RuntimeError("User store must support get_by_id_async (async only)")
            out = await user_store.get_by_id_async(user_id.strip().lower())
            _log_sessions(f"_get_user done: {out is not None}")
            return out

        async def _get_episodes():
            _log_sessions("_get_episodes started")
            if not episode_provider:
                out = state.current_dataset.episodes
                _log_sessions(f"_get_episodes done: dataset {len(out or [])} items")
                return out
            # Use in-memory dataset when we have one to avoid re-fetching full catalog from Firestore
            # (saves ~hundreds of reads per session create; dataset was loaded from file at startup)
            if state.current_dataset and (state.current_dataset.episodes or []):
                out = state.current_dataset.episodes
                _log_sessions(f"_get_episodes done: in-memory dataset {len(out)} items (skipped Firestore)")
                return out
            if not hasattr(episode_provider, "get_episodes_async"):
                raise RuntimeError("Episode provider must support get_episodes_async (async only)")
            out = await episode_provider.get_episodes_async(limit=None)
            _log_sessions(f"_get_episodes done: {len(out or [])} items")
            return out

        engagements, user, episodes = await asyncio.gather(
            _get_engagements(),
            _get_user(),
            _get_episodes(),
        )
        _log_sessions(f"data gathered: engagements={len(engagements or [])}, user={user is not None}, episodes={len(episodes or [])}")

        category_anchor_vector = user.get("category_vector") if user else None
        excluded_ids = set(request.excluded_ids or [])
        for eng in engagements:
            if eng.get("episode_id"):
                excluded_ids.add(eng["episode_id"])
        episode_list = _episode_dicts(episodes)
        if episode_provider:
            episode_by_content_id = _episode_by_content_id_from_list(episode_list)
        else:
            episode_by_content_id = state.current_dataset.episode_by_content_id
        algo_config = getattr(state.current_algorithm, "parsed_config", None)

        # Embeddings: use in-memory when loaded, else fetch (query path or fetch path)
        embeddings = state.current_embeddings
        query_results = None
        if not embeddings and hasattr(state, "vector_store") and state.vector_store:
            engagement_ids = [e.get("episode_id") for e in engagements if e.get("episode_id")]
            use_sum_sim = getattr(algo_config, "use_sum_similarities", False) if algo_config else False

            # Query path: when we have user_vector and not use_sum_similarities
            if not use_sum_sim:
                # Fetch engagement embeddings only to compute user_vector
                eng_embeddings = {}
                if engagement_ids:
                    algo_folder = state.current_algorithm.folder_name
                    strategy_ver = state.current_algorithm.strategy_version
                    dataset_folder = state.current_dataset.folder_name
                    eng_embeddings = await state.vector_store.get_embeddings_async(
                        engagement_ids, algo_folder, strategy_ver, dataset_folder
                    )
                ep_by_id = engine.ensure_episode_by_content_id(episode_by_content_id)
                engs_typed = engine.ensure_engagements(engagements)
                user_vector = engine.get_user_vector_mean(
                    engs_typed,
                    eng_embeddings,
                    ep_by_id,
                    algo_config,
                    category_anchor_vector=category_anchor_vector,
                )
                if user_vector and hasattr(state.vector_store, "query_async"):
                    # Pinecone requires native Python floats; user_vector may contain numpy.float64
                    vector_list = [float(x) for x in user_vector]
                    top_k = getattr(algo_config, "pinecone_query_top_k", 250) if algo_config else 250
                    _log_sessions(f"Pinecone query path: top_k={top_k}")
                    query_results = await state.vector_store.query_async(
                        vector=vector_list,
                        top_k=top_k,
                        algorithm_version=state.current_algorithm.folder_name,
                        strategy_version=state.current_algorithm.strategy_version,
                        dataset_version=state.current_dataset.folder_name,
                    )
                    embeddings = eng_embeddings
                    _log_sessions(f"query_async returned {len(query_results or [])} matches")

            # Fetch path: when query path not used
            if query_results is None:
                candidate_ids = engine.get_candidate_pool_ids(excluded_ids, episode_list, algo_config)
                needed_ids = list(set(engagement_ids) | set(candidate_ids))
                _log_sessions(f"fetch path: needed_ids={len(needed_ids)}")
                if needed_ids:
                    algo_folder = state.current_algorithm.folder_name
                    strategy_ver = state.current_algorithm.strategy_version
                    dataset_folder = state.current_dataset.folder_name
                    embeddings = await state.vector_store.get_embeddings_async(
                        needed_ids, algo_folder, strategy_ver, dataset_folder
                    )
                    _log_sessions(f"embeddings received: {len(embeddings)}")
                    print(
                        f"[sessions] Pinecone get_embeddings namespace algo={algo_folder!r} strategy={strategy_ver!r} "
                        f"dataset={dataset_folder!r} requested={len(needed_ids)} returned={len(embeddings)}",
                        flush=True,
                    )

        _log_sessions("calling create_recommendation_queue")
        queue, cold_start, user_vector_episodes = engine.create_recommendation_queue(
            engagements=engagements,
            excluded_ids=excluded_ids,
            episodes=episode_list,
            embeddings=embeddings or {},
            episode_by_content_id=episode_by_content_id,
            config=algo_config,
            category_anchor_vector=category_anchor_vector,
            query_results=query_results,
        )
        _log_sessions(f"queue built: len={len(queue)}, cold_start={cold_start}")
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
            embeddings_available=len(embeddings) > 0,
            top_similarity_scores=[round(s.similarity_score, 3) for s, _ in first_page[:5]],
            top_quality_scores=[round(s.quality_score, 3) for s, _ in first_page[:5]],
            top_final_scores=[round(s.final_score, 3) for s, _ in first_page[:5]],
            scoring_weights={"similarity": 0.55, "quality": 0.30, "recency": 0.15},
        )
        _log_sessions(f"create_session done: session_id={session_id}")
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
    except Exception as e:
        _log_sessions(f"create_session error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise


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
    user_id = request.user_id
    state.engagement_store.record_engagement(
        user_id,
        request.episode_id,
        request.type,
        timestamp=datetime.now(timezone.utc).isoformat(),
        episode_title=request.episode_title,
        series_name=request.series_name,
    )
    return {
        "status": "ok",
        "session_id": session_id,
        "episode_id": request.episode_id,
        "type": request.type,
        "engaged_count": len(session["engaged_ids"]),
    }
