#!/usr/bin/env python3
"""
Serafis Mock Recommendation API Server

Implements the recommendation algorithms from the spec using the extracted dataset.

Usage:
    uvicorn server:app --reload --port 8000
    
Endpoints:
    GET /api/recommendations/discover?user_id=...
    GET /api/recommendations/insights-for-you?user_id=...
    GET /api/recommendations/highest-signal?user_id=...
    GET /api/recommendations/non-consensus?user_id=...
    GET /api/recommendations/new-from-shows?user_id=...
    GET /api/recommendations/trending/{category}?user_id=...
    POST /api/feedback/not-interested
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional, Set
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Query
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

# Load data at startup
EPISODES = load_episodes()
SERIES = load_series()
USERS = load_users()
SERIES_MAP = {s["id"]: s for s in SERIES}

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

class RecommendationSection(BaseModel):
    section: str
    title: str
    subtitle: str
    episodes: List[EpisodeCard]

class NotInterestedRequest(BaseModel):
    user_id: str
    episode_id: str

# ============================================================================
# Helper Functions
# ============================================================================

def get_user_context(user_id: str) -> Dict:
    """Get user context, return cold start user if not found."""
    if user_id in USERS:
        return USERS[user_id]
    return USERS.get("user_cold_start", {
        "id": user_id,
        "category_interests": [],
        "subscribed_series": [],
        "seen_episode_ids": [],
        "bookmarked_episode_ids": [],
        "not_interested_ids": []
    })

def filter_seen(episodes: List[Dict], user: Dict) -> List[Dict]:
    """Remove episodes user has already interacted with."""
    excluded = set(user.get("seen_episode_ids", [])) | \
               set(user.get("bookmarked_episode_ids", [])) | \
               set(user.get("not_interested_ids", []))
    return [ep for ep in episodes if ep["id"] not in excluded]

def calculate_quality_score(ep: Dict) -> float:
    """
    Core quality score: Insight (45%) + Credibility (40%) + Information (15%).
    Entertainment is excluded — not relevant for research value.
    """
    scores = ep.get("scores", {})
    return (
        scores.get("insight", 0) * 0.45 +
        scores.get("credibility", 0) * 0.40 +
        scores.get("information", 0) * 0.15
    ) / 4.0  # Normalize to 0-1

def days_since(date_str: str) -> int:
    """Days since a given ISO date string."""
    try:
        dt = datetime.fromisoformat(date_str.replace('+00:00', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - dt).days
    except:
        return 0

def diversify(episodes: List[Dict], limit: int, max_per_series: int = 2) -> List[Dict]:
    """Ensure variety: max N episodes per series."""
    result = []
    series_count = defaultdict(int)
    
    for ep in episodes:
        series_id = ep.get("series", {}).get("id", "")
        if series_count[series_id] >= max_per_series:
            continue
        result.append(ep)
        series_count[series_id] += 1
        if len(result) >= limit:
            break
    
    return result

def get_badges(ep: Dict) -> List[str]:
    """Determine badges for an episode."""
    badges = []
    scores = ep.get("scores", {})
    
    # Check for non-consensus first (most distinctive)
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
    
    return badges[:2]  # Max 2 badges

def to_episode_card(ep: Dict) -> EpisodeCard:
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
        categories=ep.get("categories", {"major": [], "subcategories": []})
    )

# ============================================================================
# Recommendation Algorithms
# ============================================================================

def get_insights_for_you(user_id: str, limit: int = 10) -> List[Dict]:
    """
    Episodes matching user's category interests, weighted by quality.
    Uses: category_interests signal
    """
    user = get_user_context(user_id)
    category_interests = set(user.get("category_interests", []))
    
    if not category_interests:
        # Cold start: return highest signal
        return get_highest_signal(user_id, limit)
    
    # Get episodes matching user's category interests
    candidates = []
    for ep in EPISODES:
        ep_categories = set(ep.get("categories", {}).get("major", []))
        if ep_categories & category_interests:
            candidates.append(ep)
    
    candidates = filter_seen(candidates, user)
    
    # Score: 60% quality, 40% recency
    scored = []
    for ep in candidates:
        quality = calculate_quality_score(ep)
        recency = max(0, 1 - (days_since(ep["published_at"]) / 30))
        score = quality * 0.6 + recency * 0.4
        scored.append((ep, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return diversify([ep for ep, _ in scored], limit)


def get_highest_signal(user_id: str, limit: int = 10, days: int = 7) -> List[Dict]:
    """
    Top quality episodes from the past week (global, minimally personalized).
    """
    user = get_user_context(user_id)
    
    # Filter by recency
    recent = [ep for ep in EPISODES if days_since(ep["published_at"]) <= days]
    recent = filter_seen(recent, user)
    
    # If not enough recent, expand window
    if len(recent) < limit:
        recent = [ep for ep in EPISODES if days_since(ep["published_at"]) <= 30]
        recent = filter_seen(recent, user)
    
    # Pure quality score
    scored = [(ep, calculate_quality_score(ep)) for ep in recent]
    scored.sort(key=lambda x: x[1], reverse=True)
    
    return diversify([ep for ep, _ in scored], limit)


def get_non_consensus_ideas(user_id: str, limit: int = 10, days: int = 14) -> List[Dict]:
    """
    Episodes with genuinely contrarian/non-consensus ideas.
    
    Priority:
    1. Episodes with extracted critical_views marked as "highly_non_consensus"
    2. Episodes with critical_views marked as "non_consensus" 
    3. Fallback: high insight + credibility + low entertainment (heuristic)
    """
    user = get_user_context(user_id)
    
    # Filter by recency
    recent = [ep for ep in EPISODES if days_since(ep["published_at"]) <= days]
    recent = filter_seen(recent, user)
    
    # If not enough recent, expand window
    if len(recent) < limit:
        recent = [ep for ep in EPISODES if days_since(ep["published_at"]) <= 60]
        recent = filter_seen(recent, user)
    
    # If still not enough, expand to all time
    if len(recent) < limit:
        recent = filter_seen(EPISODES, user)
    
    # Priority 1: Episodes with extracted critical_views data marked as highly non-consensus
    highly_contrarian = [
        ep for ep in recent
        if ep.get("critical_views") and ep["critical_views"].get("non_consensus_level") == "highly_non_consensus"
    ]
    
    # Priority 2: Episodes marked as somewhat non-consensus
    somewhat_contrarian = [
        ep for ep in recent
        if ep.get("critical_views") and ep["critical_views"].get("non_consensus_level") in ["non_consensus", "somewhat_insightful"]
        and ep not in highly_contrarian
    ]
    
    # Priority 3: Heuristic fallback - high insight + credibility, lower entertainment
    heuristic_contrarian = [
        ep for ep in recent
        if ep["scores"]["credibility"] >= 3 
        and ep["scores"]["insight"] >= 3 
        and ep["scores"]["entertainment"] <= 2
        and ep not in highly_contrarian 
        and ep not in somewhat_contrarian
    ]
    
    # Combine in priority order
    contrarian = highly_contrarian + somewhat_contrarian + heuristic_contrarian
    
    # Sort within each priority by insight score
    contrarian.sort(
        key=lambda ep: (
            # Priority score: highly_non_consensus=3, non_consensus/somewhat=2, heuristic=1
            3 if (ep.get("critical_views") and ep["critical_views"].get("non_consensus_level") == "highly_non_consensus") else
            2 if (ep.get("critical_views") and ep["critical_views"].get("non_consensus_level") in ["non_consensus", "somewhat_insightful"]) else 1,
            # Then by insight + credibility
            ep["scores"]["insight"] * 0.6 + ep["scores"]["credibility"] * 0.4
        ),
        reverse=True
    )
    
    return diversify(contrarian, limit)


def get_new_from_subscriptions(user_id: str, limit: int = 10) -> List[Dict]:
    """
    Latest episodes from user's subscribed series.
    """
    user = get_user_context(user_id)
    subscribed = set(user.get("subscribed_series", []))
    
    if not subscribed:
        return []
    
    # Get episodes from subscribed series
    candidates = [
        ep for ep in EPISODES 
        if ep.get("series", {}).get("id", "") in subscribed
    ]
    
    candidates = filter_seen(candidates, user)
    
    # Sort by recency (newest first)
    candidates.sort(key=lambda ep: ep["published_at"], reverse=True)
    
    return candidates[:limit]


def get_trending_in_category(user_id: str, category: str, limit: int = 10, days: int = 14) -> List[Dict]:
    """
    Popular episodes in a specific category.
    """
    user = get_user_context(user_id)
    
    # Get recent episodes in category
    candidates = [
        ep for ep in EPISODES
        if category in ep.get("categories", {}).get("major", [])
        and days_since(ep["published_at"]) <= days
    ]
    
    candidates = filter_seen(candidates, user)
    
    # If not enough, expand window
    if len(candidates) < limit:
        candidates = [
            ep for ep in EPISODES
            if category in ep.get("categories", {}).get("major", [])
            and days_since(ep["published_at"]) <= 60
        ]
        candidates = filter_seen(candidates, user)
    
    # Score: 50% series popularity, 30% quality, 20% recency
    scored = []
    for ep in candidates:
        series_id = ep.get("series", {}).get("id", "")
        series = SERIES_MAP.get(series_id, {})
        series_popularity = series.get("popularity", 50) / 100.0
        quality = calculate_quality_score(ep)
        recency = max(0, 1 - (days_since(ep["published_at"]) / days))
        score = series_popularity * 0.5 + quality * 0.3 + recency * 0.2
        scored.append((ep, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return diversify([ep for ep, _ in scored], limit)

# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="Serafis Mock Recommendation API",
    description="Mock API for testing recommendation algorithms",
    version="1.0.0"
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
        "version": "1.0.0",
        "endpoints": [
            "/api/recommendations/discover",
            "/api/recommendations/insights-for-you",
            "/api/recommendations/highest-signal",
            "/api/recommendations/non-consensus",
            "/api/recommendations/new-from-shows",
            "/api/recommendations/trending/{category}",
        ],
        "data": {
            "episodes": len(EPISODES),
            "series": len(SERIES),
            "users": len(USERS)
        }
    }

@app.get("/api/recommendations/insights-for-you", response_model=RecommendationSection)
def insights_for_you(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(10, le=20, description="Max results")
):
    """Episodes matching user's category interests."""
    user = get_user_context(user_id)
    episodes = get_insights_for_you(user_id, limit)
    
    categories_str = ", ".join(user.get("category_interests", ["your interests"])[:2])
    return RecommendationSection(
        section="insights_for_you",
        title="📊 Insights for You",
        subtitle=f"Based on {categories_str}",
        episodes=[to_episode_card(ep) for ep in episodes]
    )

@app.get("/api/recommendations/highest-signal", response_model=RecommendationSection)
def highest_signal(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(10, le=20, description="Max results"),
    days: int = Query(7, le=30, description="Recency window in days")
):
    """Top quality episodes (global)."""
    episodes = get_highest_signal(user_id, limit, days)
    return RecommendationSection(
        section="highest_signal",
        title="💎 Highest Signal This Week",
        subtitle="Top Insight + Credibility across all topics",
        episodes=[to_episode_card(ep) for ep in episodes]
    )

@app.get("/api/recommendations/non-consensus", response_model=RecommendationSection)
def non_consensus(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(10, le=20, description="Max results"),
    days: int = Query(14, le=60, description="Recency window in days")
):
    """Contrarian views from credible speakers."""
    episodes = get_non_consensus_ideas(user_id, limit, days)
    return RecommendationSection(
        section="non_consensus",
        title="🔥 Non-Consensus Ideas",
        subtitle="Contrarian views from credible speakers",
        episodes=[to_episode_card(ep) for ep in episodes]
    )

@app.get("/api/recommendations/new-from-shows", response_model=RecommendationSection)
def new_from_shows(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(10, le=20, description="Max results")
):
    """New episodes from subscribed series."""
    episodes = get_new_from_subscriptions(user_id, limit)
    return RecommendationSection(
        section="new_from_shows",
        title="📡 New from Your Shows",
        subtitle="Latest from subscribed series",
        episodes=[to_episode_card(ep) for ep in episodes]
    )

@app.get("/api/recommendations/trending/{category}", response_model=RecommendationSection)
def trending(
    category: str,
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(10, le=20, description="Max results"),
    days: int = Query(14, le=60, description="Recency window in days")
):
    """Popular episodes in a category."""
    episodes = get_trending_in_category(user_id, category, limit, days)
    return RecommendationSection(
        section="trending",
        title=f"🌟 Trending in {category}",
        subtitle=f"Popular this week",
        episodes=[to_episode_card(ep) for ep in episodes]
    )

@app.get("/api/recommendations/discover")
def discover(user_id: str = Query(..., description="User ID")):
    """Full discover page with all sections."""
    user = get_user_context(user_id)
    
    sections = []
    
    # Insights for you
    eps = get_insights_for_you(user_id, 10)
    categories_str = ", ".join(user.get("category_interests", ["your interests"])[:2])
    sections.append(RecommendationSection(
        section="insights_for_you",
        title="📊 Insights for You",
        subtitle=f"Based on {categories_str}",
        episodes=[to_episode_card(ep) for ep in eps]
    ))
    
    # Highest signal
    eps = get_highest_signal(user_id, 10)
    sections.append(RecommendationSection(
        section="highest_signal",
        title="💎 Highest Signal This Week",
        subtitle="Top Insight + Credibility across all topics",
        episodes=[to_episode_card(ep) for ep in eps]
    ))
    
    # Non-consensus
    eps = get_non_consensus_ideas(user_id, 8)
    sections.append(RecommendationSection(
        section="non_consensus",
        title="🔥 Non-Consensus Ideas",
        subtitle="Contrarian views from credible speakers",
        episodes=[to_episode_card(ep) for ep in eps]
    ))
    
    # Add subscription section if user has subscriptions
    if user.get("subscribed_series"):
        eps = get_new_from_subscriptions(user_id, 8)
        if eps:
            sections.append(RecommendationSection(
                section="new_from_shows",
                title="📡 New from Your Shows",
                subtitle="Latest from subscribed series",
                episodes=[to_episode_card(ep) for ep in eps]
            ))
    
    # Add trending section for first category interest
    if user.get("category_interests"):
        first_cat = user["category_interests"][0]
        eps = get_trending_in_category(user_id, first_cat, 8)
        if eps:
            sections.append(RecommendationSection(
                section="trending",
                title=f"🌟 Trending in {first_cat}",
                subtitle="Popular this week",
                episodes=[to_episode_card(ep) for ep in eps]
            ))
    
    return {"sections": [s.model_dump() for s in sections]}

@app.post("/api/feedback/not-interested")
def mark_not_interested(request: NotInterestedRequest):
    """Mark an episode as not interested."""
    user_id = request.user_id
    episode_id = request.episode_id
    
    if user_id in USERS:
        if "not_interested_ids" not in USERS[user_id]:
            USERS[user_id]["not_interested_ids"] = []
        if episode_id not in USERS[user_id]["not_interested_ids"]:
            USERS[user_id]["not_interested_ids"].append(episode_id)
    
    return {"status": "ok", "user_id": user_id, "episode_id": episode_id}

@app.get("/api/users")
def list_users():
    """List available mock users."""
    return {"users": list(USERS.values())}

@app.get("/api/episodes")
def list_episodes(limit: int = Query(None)):
    """List all episodes for the recommendation tester."""
    if limit:
        return {"episodes": EPISODES[:limit], "total": len(EPISODES)}
    return {"episodes": EPISODES, "total": len(EPISODES)}

@app.get("/api/series")
def list_series():
    """List series (for debugging)."""
    return {"series": SERIES}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
