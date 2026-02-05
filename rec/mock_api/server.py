#!/usr/bin/env python3
"""
Serafis Recommendation API Server — V1.2

A clean FastAPI server that delegates to modular components:
- data_loader.py: Data loading and caching
- models.py: Pydantic request/response models
- recommendation_engine.py: Core recommendation algorithm

Key improvements in V1.2:
- Blended scoring: similarity (55%) + quality (30%) + recency (15%)
- Credibility weighted 1.5x higher than insight
- Recency boost with exponential decay
- Clean modular architecture

Usage:
    uvicorn server:app --reload --port 8000
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Set

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Local modules
from data_loader import DataCache
from models import (
    SeriesInfo, EpisodeScores, EntityInfo, CriticalViews,
    EpisodeCard, EpisodeDetail,
    Engagement, CreateSessionRequest, LoadMoreRequest, EngageRequest,
    SessionResponse, SessionDebugInfo
)
from recommendation_engine import (
    RecommendationConfig, DEFAULT_CONFIG,
    get_candidate_pool, rank_candidates, create_recommendation_queue,
    get_badges, days_since, ScoredEpisode
)


# ============================================================================
# Configuration
# ============================================================================

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 20


# ============================================================================
# In-Memory Session Storage
# ============================================================================

SESSIONS: Dict[str, Dict] = {}


# ============================================================================
# Data Cache
# ============================================================================

# Initialize data cache at startup
data_cache = DataCache.get_instance()


# ============================================================================
# Model Converters
# ============================================================================

def to_episode_card(
    ep: Dict,
    scored: Optional[ScoredEpisode] = None,
    queue_position: int = None
) -> EpisodeCard:
    """Convert raw episode dict to EpisodeCard."""
    return EpisodeCard(
        id=ep["id"],
        content_id=ep["content_id"],
        title=ep["title"],
        series=SeriesInfo(**ep["series"]),
        published_at=ep["published_at"],
        scores=EpisodeScores(**ep["scores"]),
        badges=get_badges(ep),
        key_insight=ep.get("key_insight"),
        categories=ep.get("categories", {"major": [], "subcategories": []}),
        similarity_score=round(scored.similarity_score, 4) if scored else None,
        quality_score=round(scored.quality_score, 4) if scored else None,
        recency_score=round(scored.recency_score, 4) if scored else None,
        final_score=round(scored.final_score, 4) if scored else None,
        queue_position=queue_position
    )


def to_episode_detail(ep: Dict) -> EpisodeDetail:
    """Convert raw episode dict to full EpisodeDetail."""
    entities = [EntityInfo(**e) for e in ep.get("entities", [])]
    critical_views = None
    if ep.get("critical_views"):
        critical_views = CriticalViews(**ep["critical_views"])
    
    return EpisodeDetail(
        id=ep["id"],
        content_id=ep["content_id"],
        title=ep["title"],
        series=SeriesInfo(**ep["series"]),
        published_at=ep["published_at"],
        scores=EpisodeScores(**ep["scores"]),
        categories=ep.get("categories", {"major": [], "subcategories": []}),
        entities=entities,
        people=ep.get("people", []),
        key_insight=ep.get("key_insight"),
        critical_views=critical_views,
        search_relevance_score=ep.get("search_relevance_score"),
        aggregate_score=ep.get("aggregate_score"),
        top_in_categories=ep.get("top_in_categories", [])
    )


# ============================================================================
# Session Management
# ============================================================================

def create_session(
    engagements: list,
    excluded_ids: Set[str],
    config: RecommendationConfig = DEFAULT_CONFIG
) -> Dict:
    """
    Create a new session with ranked queue.
    """
    session_id = str(uuid.uuid4())[:8]
    
    # Create recommendation queue
    queue, cold_start, user_vector_episodes = create_recommendation_queue(
        engagements, excluded_ids, config, data_cache
    )
    
    # Create session
    session = {
        "session_id": session_id,
        "queue": queue,
        "shown_indices": set(),
        "engaged_ids": set(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cold_start": cold_start,
        "user_vector_episodes": user_vector_episodes,
        "excluded_ids": excluded_ids.copy(),
        "config": config,
    }
    
    SESSIONS[session_id] = session
    return session


def get_session(session_id: str) -> Optional[Dict]:
    """Get session by ID."""
    return SESSIONS.get(session_id)


def get_next_from_queue(session: Dict, limit: int = DEFAULT_PAGE_SIZE) -> list:
    """
    Get next N unshown episodes from queue.
    Returns list of (ScoredEpisode, queue_position) tuples.
    """
    queue = session["queue"]
    shown = session["shown_indices"]
    engaged = session["engaged_ids"]
    
    result = []
    
    for i, scored_ep in enumerate(queue):
        if i in shown:
            continue
        
        ep = scored_ep.episode
        if ep["id"] in engaged or ep.get("content_id") in engaged:
            continue
        
        result.append((scored_ep, i + 1))
        shown.add(i)
        
        if len(result) >= limit:
            break
    
    return result


def mark_engaged(session: Dict, episode_id: str):
    """Mark an episode as engaged within this session."""
    session["engaged_ids"].add(episode_id)
    session["excluded_ids"].add(episode_id)


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="Serafis Recommendation API",
    description="V1.2 with Blended Scoring (Similarity + Quality + Recency)",
    version="1.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    config = DEFAULT_CONFIG
    return {
        "name": "Serafis Recommendation API",
        "version": "1.2.0",
        "algorithm": "V1.2 Blended Scoring",
        "scoring": {
            "formula": "final = w_sim * similarity + w_qual * quality + w_rec * recency",
            "weights": {
                "similarity": config.weight_similarity,
                "quality": config.weight_quality,
                "recency": config.weight_recency,
            },
            "quality_formula": f"(credibility * {config.credibility_multiplier} + insight) / {config.max_quality_score}",
            "recency_formula": f"exp(-{config.recency_lambda} * days_old)",
        },
        "endpoints": [
            "POST /api/sessions/create",
            "GET /api/sessions/{session_id}",
            "POST /api/sessions/{session_id}/next",
            "POST /api/sessions/{session_id}/engage",
            "POST /api/recommendations/for-you",
            "GET /api/episodes",
            "GET /api/episodes/{id}",
            "GET /api/stats",
        ],
        "data": {
            "episodes": len(data_cache.episodes),
            "series": len(data_cache.series),
            "embeddings": len(data_cache.embeddings),
            "active_sessions": len(SESSIONS)
        }
    }


# ============================================================================
# Session Endpoints
# ============================================================================

@app.post("/api/sessions/create", response_model=SessionResponse)
def create_session_endpoint(request: CreateSessionRequest):
    """
    Create a new session with ranked recommendation queue.
    """
    engagements = [e.model_dump() for e in request.engagements]
    excluded_ids = set(request.excluded_ids)
    
    session = create_session(engagements, excluded_ids)
    
    first_page = get_next_from_queue(session, DEFAULT_PAGE_SIZE)
    
    episodes = [
        to_episode_card(scored.episode, scored, pos)
        for scored, pos in first_page
    ]
    
    total_in_queue = len(session["queue"])
    shown_count = len(session["shown_indices"])
    config = session["config"]
    
    # Debug info with new scoring details
    debug = SessionDebugInfo(
        candidates_count=total_in_queue,
        user_vector_episodes=session["user_vector_episodes"],
        embeddings_available=len(data_cache.embeddings) > 0,
        top_similarity_scores=[round(s.similarity_score, 3) for s, _ in first_page[:5]],
        top_quality_scores=[round(s.quality_score, 3) for s, _ in first_page[:5]],
        top_final_scores=[round(s.final_score, 3) for s, _ in first_page[:5]],
        scoring_weights={
            "similarity": config.weight_similarity,
            "quality": config.weight_quality,
            "recency": config.weight_recency,
        }
    )
    
    return SessionResponse(
        session_id=session["session_id"],
        episodes=episodes,
        total_in_queue=total_in_queue,
        shown_count=shown_count,
        remaining_count=total_in_queue - shown_count,
        cold_start=session["cold_start"],
        algorithm="v1.2_blended",
        debug=debug
    )


@app.get("/api/sessions/{session_id}")
def get_session_info(session_id: str):
    """Get session info without fetching more episodes."""
    session = get_session(session_id)
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


@app.post("/api/sessions/{session_id}/next", response_model=SessionResponse)
def load_more(session_id: str, request: LoadMoreRequest = None):
    """
    Load more recommendations from the session queue.
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    limit = request.limit if request else DEFAULT_PAGE_SIZE
    limit = min(limit, MAX_PAGE_SIZE)
    
    next_page = get_next_from_queue(session, limit)
    
    episodes = [
        to_episode_card(scored.episode, scored, pos)
        for scored, pos in next_page
    ]
    
    total_in_queue = len(session["queue"])
    shown_count = len(session["shown_indices"])
    
    return SessionResponse(
        session_id=session_id,
        episodes=episodes,
        total_in_queue=total_in_queue,
        shown_count=shown_count,
        remaining_count=total_in_queue - shown_count,
        cold_start=session["cold_start"],
        algorithm="v1.2_blended",
    )


@app.post("/api/sessions/{session_id}/engage")
def engage_episode(session_id: str, request: EngageRequest):
    """Record an engagement within the session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    mark_engaged(session, request.episode_id)
    
    return {
        "status": "ok",
        "session_id": session_id,
        "episode_id": request.episode_id,
        "type": request.type,
        "engaged_count": len(session["engaged_ids"]),
    }


# ============================================================================
# Legacy For-You Endpoint
# ============================================================================

@app.post("/api/recommendations/for-you")
def for_you_legacy(request: CreateSessionRequest):
    """
    Legacy endpoint - creates a session and returns first page.
    """
    result = create_session_endpoint(request)
    
    return {
        "section": "for_you",
        "title": "Highest Signal" if result.cold_start else "For You",
        "subtitle": "Top quality episodes" if result.cold_start else "Based on your recent activity",
        "algorithm": result.algorithm,
        "cold_start": result.cold_start,
        "episodes": [ep.model_dump() for ep in result.episodes],
        "session_id": result.session_id,
        "total_in_queue": result.total_in_queue,
        "remaining_count": result.remaining_count,
        "debug": result.debug.model_dump() if result.debug else None,
    }


# ============================================================================
# Episode Endpoints
# ============================================================================

@app.get("/api/episodes")
def list_episodes(limit: int = Query(None), offset: int = Query(0)):
    """List all episodes."""
    episodes = data_cache.episodes
    paginated = episodes[offset:offset + limit] if limit else episodes[offset:]
    return {
        "episodes": paginated,
        "total": len(episodes),
        "offset": offset,
        "limit": limit
    }


@app.get("/api/episodes/{episode_id}")
def get_episode(episode_id: str):
    """Get full episode details by ID or content_id."""
    ep = data_cache.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    return to_episode_detail(ep)


@app.get("/api/series")
def list_series():
    """List all series."""
    return {"series": data_cache.series}


# ============================================================================
# Stats & Debug Endpoints
# ============================================================================

@app.get("/api/stats")
def get_stats():
    """Get data statistics and current configuration."""
    config = DEFAULT_CONFIG
    episodes = data_cache.episodes
    
    credible_count = sum(
        1 for ep in episodes
        if ep.get("scores", {}).get("credibility", 0) >= config.credibility_floor
    )
    high_quality = sum(
        1 for ep in episodes
        if (ep.get("scores", {}).get("credibility", 0) +
            ep.get("scores", {}).get("insight", 0)) >= config.combined_floor
    )
    recent_count = sum(
        1 for ep in episodes
        if days_since(ep.get("published_at", "")) <= config.freshness_window_days
    )
    contrarian_count = sum(
        1 for ep in episodes
        if (ep.get("critical_views") or {}).get("has_critical_views")
    )
    
    return {
        "total_episodes": len(episodes),
        "total_series": len(data_cache.series),
        "total_embeddings": len(data_cache.embeddings),
        "credible_episodes": credible_count,
        "high_quality_episodes": high_quality,
        "recent_episodes": recent_count,
        "contrarian_episodes": contrarian_count,
        "active_sessions": len(SESSIONS),
        "config": {
            "credibility_floor": config.credibility_floor,
            "combined_floor": config.combined_floor,
            "freshness_window_days": config.freshness_window_days,
            "candidate_pool_size": config.candidate_pool_size,
            "user_vector_limit": config.user_vector_limit,
            "default_page_size": DEFAULT_PAGE_SIZE,
        },
        "scoring": {
            "weight_similarity": config.weight_similarity,
            "weight_quality": config.weight_quality,
            "weight_recency": config.weight_recency,
            "credibility_multiplier": config.credibility_multiplier,
            "recency_lambda": config.recency_lambda,
        }
    }


@app.get("/api/config")
def get_config():
    """Get current algorithm configuration."""
    config = DEFAULT_CONFIG
    return {
        "version": "1.2",
        "stage_a": {
            "credibility_floor": config.credibility_floor,
            "combined_floor": config.combined_floor,
            "freshness_window_days": config.freshness_window_days,
            "candidate_pool_size": config.candidate_pool_size,
        },
        "stage_b": {
            "user_vector_limit": config.user_vector_limit,
            "use_weighted_engagements": config.use_weighted_engagements,
            "engagement_weights": config.engagement_weights,
            "use_sum_similarities": config.use_sum_similarities,
        },
        "scoring": {
            "weight_similarity": config.weight_similarity,
            "weight_quality": config.weight_quality,
            "weight_recency": config.weight_recency,
            "credibility_multiplier": config.credibility_multiplier,
            "recency_lambda": config.recency_lambda,
        }
    }


# ============================================================================
# Startup
# ============================================================================

@app.on_event("startup")
async def startup():
    """Log startup info."""
    print(f"Serafis Recommendation API V1.2 starting...")
    print(f"Algorithm: Blended Scoring (Sim={DEFAULT_CONFIG.weight_similarity}, "
          f"Qual={DEFAULT_CONFIG.weight_quality}, Rec={DEFAULT_CONFIG.weight_recency})")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
