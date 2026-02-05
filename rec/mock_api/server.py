#!/usr/bin/env python3
"""
Serafis Mock Recommendation API Server — V1.1

Implements the refined 2-stage recommendation algorithm with Option C:
Session Pool with Progressive Reveal.

Session Behavior:
- Create Session: Compute user vector, rank all candidates, store as queue
- Load More: Return next N from queue (no recomputation)
- Refresh: Create new session with fresh computation
- Engage: Mark episode as engaged (excluded from future sessions)

Usage:
    uvicorn server:app --reload --port 8000
"""

import json
import math
import uuid
import hashlib
import numpy as np
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ============================================================================
# Data Loading
# ============================================================================

DATA_DIR = Path(__file__).parent / "data"

def load_episodes() -> List[Dict]:
    with open(DATA_DIR / "episodes.json") as f:
        return json.load(f)

def load_series() -> List[Dict]:
    with open(DATA_DIR / "series.json") as f:
        return json.load(f)

def load_users() -> Dict[str, Dict]:
    with open(DATA_DIR / "mock_users.json") as f:
        users = json.load(f)
        return {u["id"]: u for u in users}

def load_embeddings() -> Dict[str, List[float]]:
    """Load pre-computed embeddings if available."""
    embeddings_file = DATA_DIR / "embeddings.json"
    if embeddings_file.exists():
        with open(embeddings_file) as f:
            return json.load(f)
    return {}

# Load data at startup
EPISODES = load_episodes()
SERIES = load_series()
USERS = load_users()
EMBEDDINGS = load_embeddings()
SERIES_MAP = {s["id"]: s for s in SERIES}
EPISODE_MAP = {ep["id"]: ep for ep in EPISODES}
EPISODE_BY_CONTENT_ID = {ep["content_id"]: ep for ep in EPISODES}

print(f"Loaded {len(EPISODES)} episodes, {len(SERIES)} series, {len(EMBEDDINGS)} embeddings")

# ============================================================================
# Configuration — V1.1 Parameters
# ============================================================================

# Stage A: Candidate Pool Pre-Selection
CREDIBILITY_FLOOR = 2
COMBINED_FLOOR = 5
FRESHNESS_WINDOW_DAYS = 30
CANDIDATE_POOL_SIZE = 50

# Stage B: Semantic Matching
USER_VECTOR_LIMIT = 5
EMBEDDING_DIMENSIONS = 1536

# Session Configuration
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 20

# Engagement type weights (Option B, for future use)
ENGAGEMENT_WEIGHTS = {
    "bookmark": 2.0,
    "listen": 1.5,
    "click": 1.0,
}
RECENCY_LAMBDA = 0.05

# ============================================================================
# In-Memory Session Storage (for testing - would be Redis in production)
# ============================================================================

SESSIONS: Dict[str, Dict] = {}

# ============================================================================
# Models
# ============================================================================

class SeriesInfo(BaseModel):
    id: str
    name: str

class EpisodeScores(BaseModel):
    insight: int
    credibility: int
    information: int
    entertainment: int

class EntityInfo(BaseModel):
    name: str
    relevance: int
    context: Optional[str] = None

class CriticalViews(BaseModel):
    non_consensus_level: Optional[str] = None
    has_critical_views: Optional[bool] = None
    new_ideas_summary: Optional[str] = None
    key_insights: Optional[str] = None

class EpisodeDetail(BaseModel):
    id: str
    content_id: str
    title: str
    series: SeriesInfo
    published_at: str
    scores: EpisodeScores
    categories: Dict[str, List[str]]
    entities: List[EntityInfo]
    people: List[Dict]
    key_insight: Optional[str]
    critical_views: Optional[CriticalViews]
    search_relevance_score: Optional[float]
    aggregate_score: Optional[float]
    top_in_categories: List[str]

class EpisodeCard(BaseModel):
    id: str
    content_id: str
    title: str
    series: SeriesInfo
    published_at: str
    scores: EpisodeScores
    badges: List[str]
    key_insight: Optional[str]
    categories: Dict[str, List[str]]
    similarity_score: Optional[float] = None
    queue_position: Optional[int] = None

class Engagement(BaseModel):
    episode_id: str
    type: str = "click"
    timestamp: str

class CreateSessionRequest(BaseModel):
    engagements: List[Engagement] = []
    excluded_ids: List[str] = []

class SessionResponse(BaseModel):
    session_id: str
    episodes: List[EpisodeCard]
    total_in_queue: int
    shown_count: int
    remaining_count: int
    cold_start: bool
    algorithm: str = "v1.1_session_pool"
    debug: Optional[Dict] = None

class LoadMoreRequest(BaseModel):
    limit: int = DEFAULT_PAGE_SIZE

class EngageRequest(BaseModel):
    episode_id: str
    type: str = "click"
    timestamp: Optional[str] = None

# ============================================================================
# Helper Functions
# ============================================================================

def days_since(date_str: str) -> int:
    """Days since a given ISO date string."""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - dt).days
    except:
        return 999

def get_badges(ep: Dict) -> List[str]:
    """Determine badges for an episode."""
    badges = []
    scores = ep.get("scores", {})
    critical_views = ep.get("critical_views")
    
    if critical_views and critical_views.get("non_consensus_level") == "highly_non_consensus":
        badges.append("highly_contrarian")
    elif critical_views and critical_views.get("has_critical_views"):
        badges.append("contrarian")
    
    if scores.get("insight", 0) >= 3:
        badges.append("high_insight")
    if scores.get("credibility", 0) >= 3:
        badges.append("high_credibility")
    if scores.get("information", 0) >= 3:
        badges.append("data_rich")
    
    return badges[:2]

def to_episode_card(ep: Dict, similarity_score: float = None, queue_position: int = None) -> EpisodeCard:
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
        similarity_score=similarity_score,
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
# Stage A: Candidate Pool Pre-Selection
# ============================================================================

def get_candidate_pool(
    excluded_ids: Set[str],
    freshness_days: int = FRESHNESS_WINDOW_DAYS,
    pool_size: int = CANDIDATE_POOL_SIZE
) -> List[Dict]:
    """
    Stage A: Pre-select candidate pool using quality gates and freshness.
    """
    candidates = []
    
    for ep in EPISODES:
        ep_id = ep["id"]
        content_id = ep.get("content_id", "")
        scores = ep.get("scores", {})
        credibility = scores.get("credibility", 0)
        insight = scores.get("insight", 0)
        
        # Gate 1: Credibility floor
        if credibility < CREDIBILITY_FLOOR:
            continue
        
        # Gate 2: Combined quality floor
        if (credibility + insight) < COMBINED_FLOOR:
            continue
        
        # Gate 3: Freshness
        age = days_since(ep.get("published_at", ""))
        if age > freshness_days:
            continue
        
        # Gate 4: Exclusions (check both ID and content_id)
        if ep_id in excluded_ids or content_id in excluded_ids:
            continue
        
        candidates.append(ep)
    
    # Expand freshness if not enough candidates
    if len(candidates) < pool_size // 2 and freshness_days < 60:
        return get_candidate_pool(excluded_ids, freshness_days=60, pool_size=pool_size)
    
    if len(candidates) < pool_size // 4 and freshness_days < 90:
        return get_candidate_pool(excluded_ids, freshness_days=90, pool_size=pool_size)
    
    # Sort by combined quality
    candidates.sort(
        key=lambda ep: ep["scores"]["credibility"] + ep["scores"]["insight"],
        reverse=True
    )
    
    return candidates[:pool_size]

# ============================================================================
# Stage B: Semantic Matching
# ============================================================================

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not v1 or not v2:
        return 0.0
    
    v1 = np.array(v1)
    v2 = np.array(v2)
    
    dot_product = np.dot(v1, v2)
    norm_product = np.linalg.norm(v1) * np.linalg.norm(v2)
    
    return float(dot_product / norm_product) if norm_product > 0 else 0.0

def get_user_vector(engagements: List[Dict], limit: int = USER_VECTOR_LIMIT) -> Optional[List[float]]:
    """
    Compute user activity vector from recent engagements.
    Simple mean of most recent N engagement embeddings.
    """
    if not engagements:
        return None
    
    # Sort by timestamp, most recent first
    sorted_eng = sorted(engagements, key=lambda e: e.get("timestamp", ""), reverse=True)
    recent = sorted_eng[:limit]
    
    vectors = []
    for eng in recent:
        ep_id = eng.get("episode_id")
        
        # Try to find embedding by ID
        if ep_id in EMBEDDINGS:
            vectors.append(EMBEDDINGS[ep_id])
        elif ep_id in EPISODE_BY_CONTENT_ID:
            real_id = EPISODE_BY_CONTENT_ID[ep_id]["id"]
            if real_id in EMBEDDINGS:
                vectors.append(EMBEDDINGS[real_id])
    
    if not vectors:
        return None
    
    return list(np.mean(vectors, axis=0))

def rank_candidates_by_similarity(
    user_vector: Optional[List[float]],
    candidates: List[Dict]
) -> List[Tuple[Dict, float]]:
    """
    Rank all candidates by similarity to user vector.
    Returns list of (episode, similarity_score) tuples, sorted by score desc.
    """
    scored = []
    
    for ep in candidates:
        ep_id = ep["id"]
        
        if user_vector and ep_id in EMBEDDINGS:
            sim = cosine_similarity(user_vector, EMBEDDINGS[ep_id])
        else:
            # Fallback: use quality score (normalized to ~0.5 range)
            quality = (ep["scores"]["credibility"] + ep["scores"]["insight"]) / 8.0
            sim = quality * 0.5
        
        scored.append((ep, sim))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored

# ============================================================================
# Session Management
# ============================================================================

def create_session(
    engagements: List[Dict],
    excluded_ids: Set[str]
) -> Dict:
    """
    Create a new session with ranked queue.
    
    Returns session dict with:
    - session_id
    - queue: List of (episode, similarity_score) tuples
    - shown_indices: Set of indices already shown
    - created_at
    - cold_start
    """
    session_id = str(uuid.uuid4())[:8]
    
    # Get candidate pool
    candidates = get_candidate_pool(excluded_ids)
    
    # Compute user vector
    user_vector = get_user_vector(engagements)
    cold_start = user_vector is None or len(engagements) == 0
    
    # Rank all candidates
    ranked = rank_candidates_by_similarity(user_vector, candidates)
    
    # Create session
    session = {
        "session_id": session_id,
        "queue": ranked,  # List of (episode, score) tuples
        "shown_indices": set(),
        "engaged_ids": set(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cold_start": cold_start,
        "user_vector_episodes": min(len(engagements), USER_VECTOR_LIMIT) if engagements else 0,
        "excluded_ids": excluded_ids.copy(),
    }
    
    # Store session
    SESSIONS[session_id] = session
    
    return session

def get_session(session_id: str) -> Optional[Dict]:
    """Get session by ID."""
    return SESSIONS.get(session_id)

def get_next_from_queue(session: Dict, limit: int = DEFAULT_PAGE_SIZE) -> List[Tuple[Dict, float, int]]:
    """
    Get next N unshown episodes from queue.
    Returns list of (episode, score, queue_position) tuples.
    Marks them as shown.
    """
    queue = session["queue"]
    shown = session["shown_indices"]
    engaged = session["engaged_ids"]
    
    result = []
    
    for i, (ep, score) in enumerate(queue):
        # Skip already shown
        if i in shown:
            continue
        
        # Skip engaged (in case they engaged mid-session)
        if ep["id"] in engaged or ep.get("content_id") in engaged:
            continue
        
        result.append((ep, score, i + 1))  # 1-indexed position
        shown.add(i)
        
        if len(result) >= limit:
            break
    
    return result

def mark_engaged(session: Dict, episode_id: str):
    """Mark an episode as engaged within this session."""
    session["engaged_ids"].add(episode_id)
    
    # Also add to excluded for future sessions
    session["excluded_ids"].add(episode_id)

# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="Serafis Mock Recommendation API",
    description="V1.1 with Session Pool (Option C)",
    version="1.1.0"
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
    return {
        "name": "Serafis Mock Recommendation API",
        "version": "1.1.0",
        "algorithm": "V1.1 Session Pool (Option C)",
        "behavior": {
            "create_session": "Compute user vector, rank all candidates, create queue",
            "load_more": "Return next N from queue (no recomputation)",
            "refresh": "Create new session with fresh computation",
            "engage": "Mark episode as engaged, exclude from queue"
        },
        "endpoints": [
            "POST /api/sessions/create",
            "GET /api/sessions/{session_id}",
            "POST /api/sessions/{session_id}/next",
            "POST /api/sessions/{session_id}/engage",
            "GET /api/episodes",
            "GET /api/episodes/{id}",
        ],
        "data": {
            "episodes": len(EPISODES),
            "series": len(SERIES),
            "embeddings": len(EMBEDDINGS),
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
    
    This computes the user vector from engagements, gets the candidate pool,
    ranks all candidates by similarity, and stores the queue.
    
    Returns the first page of recommendations.
    """
    engagements = [e.model_dump() for e in request.engagements]
    excluded_ids = set(request.excluded_ids)
    
    # Create session
    session = create_session(engagements, excluded_ids)
    
    # Get first page
    first_page = get_next_from_queue(session, DEFAULT_PAGE_SIZE)
    
    episodes = [
        to_episode_card(ep, similarity_score=score, queue_position=pos)
        for ep, score, pos in first_page
    ]
    
    total_in_queue = len(session["queue"])
    shown_count = len(session["shown_indices"])
    
    # Debug info
    top_scores = [round(score, 3) for _, score, _ in first_page[:5]]
    
    return SessionResponse(
        session_id=session["session_id"],
        episodes=episodes,
        total_in_queue=total_in_queue,
        shown_count=shown_count,
        remaining_count=total_in_queue - shown_count,
        cold_start=session["cold_start"],
        debug={
            "candidates_count": total_in_queue,
            "user_vector_episodes": session["user_vector_episodes"],
            "embeddings_available": len(EMBEDDINGS) > 0,
            "top_similarity_scores": top_scores,
        }
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
    
    This returns the next N episodes from the pre-computed queue.
    NO recomputation happens - this is deterministic pagination.
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    limit = request.limit if request else DEFAULT_PAGE_SIZE
    limit = min(limit, MAX_PAGE_SIZE)
    
    # Get next page
    next_page = get_next_from_queue(session, limit)
    
    episodes = [
        to_episode_card(ep, similarity_score=score, queue_position=pos)
        for ep, score, pos in next_page
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
    )

@app.post("/api/sessions/{session_id}/engage")
def engage_episode(session_id: str, request: EngageRequest):
    """
    Record an engagement within the session.
    
    The engaged episode is removed from the queue (won't appear in load_more).
    It's also added to excluded_ids for future sessions.
    """
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
# Legacy Endpoints (kept for compatibility)
# ============================================================================

@app.post("/api/recommendations/for-you")
def for_you_legacy(request: CreateSessionRequest):
    """
    Legacy endpoint - creates a session and returns first page.
    For backwards compatibility with existing frontend.
    """
    result = create_session_endpoint(request)
    
    # Convert to legacy format
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
        "debug": result.debug,
    }

@app.get("/api/episodes")
def list_episodes(limit: int = Query(None), offset: int = Query(0)):
    """List all episodes."""
    episodes = EPISODES[offset:offset + limit] if limit else EPISODES[offset:]
    return {
        "episodes": episodes,
        "total": len(EPISODES),
        "offset": offset,
        "limit": limit
    }

@app.get("/api/episodes/{episode_id}")
def get_episode(episode_id: str):
    """Get full episode details by ID or content_id."""
    if episode_id in EPISODE_MAP:
        return to_episode_detail(EPISODE_MAP[episode_id])
    
    if episode_id in EPISODE_BY_CONTENT_ID:
        return to_episode_detail(EPISODE_BY_CONTENT_ID[episode_id])
    
    raise HTTPException(status_code=404, detail="Episode not found")

@app.get("/api/series")
def list_series():
    """List all series."""
    return {"series": SERIES}

@app.get("/api/stats")
def get_stats():
    """Get data statistics."""
    credible_count = sum(1 for ep in EPISODES if ep.get("scores", {}).get("credibility", 0) >= CREDIBILITY_FLOOR)
    high_quality = sum(1 for ep in EPISODES if (ep.get("scores", {}).get("credibility", 0) + ep.get("scores", {}).get("insight", 0)) >= COMBINED_FLOOR)
    recent_count = sum(1 for ep in EPISODES if days_since(ep.get("published_at", "")) <= FRESHNESS_WINDOW_DAYS)
    contrarian_count = sum(1 for ep in EPISODES if (ep.get("critical_views") or {}).get("has_critical_views"))
    
    return {
        "total_episodes": len(EPISODES),
        "total_series": len(SERIES),
        "total_embeddings": len(EMBEDDINGS),
        "credible_episodes": credible_count,
        "high_quality_episodes": high_quality,
        "recent_episodes": recent_count,
        "contrarian_episodes": contrarian_count,
        "active_sessions": len(SESSIONS),
        "config": {
            "credibility_floor": CREDIBILITY_FLOOR,
            "combined_floor": COMBINED_FLOOR,
            "freshness_window_days": FRESHNESS_WINDOW_DAYS,
            "candidate_pool_size": CANDIDATE_POOL_SIZE,
            "user_vector_limit": USER_VECTOR_LIMIT,
            "default_page_size": DEFAULT_PAGE_SIZE,
        }
    }

# ============================================================================
# Cleanup old sessions (simple memory management)
# ============================================================================

@app.on_event("startup")
async def startup_cleanup():
    """Clean up is handled by in-memory storage (sessions disappear on restart)."""
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
