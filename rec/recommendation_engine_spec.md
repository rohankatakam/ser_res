# Serafis Recommendation Engine — Technical Specification

> *Design document for the research intelligence recommendation system powering the Serafis mobile prosumer app.*

**Date:** January 29, 2026  
**Author:** Rohan Katakam  
**Status:** Draft (Revised)  
**Stakeholder:** Rohan Sharma (CEO)

---

## 1. Framing

### 1.1 What Serafis Is

**Serafis is a research intelligence tool, not a podcast app.**

- The podcast content is the **data source**, not the product category
- Users have **professional/financial motivations**, not entertainment motivations
- Recommendations should surface **insights relevant to work**, not "podcasts to enjoy"

### 1.2 Target User: Prosumer Investor

This specification targets the **prosumer segment** for the mobile app:

| Attribute | Description |
|-----------|-------------|
| **Who** | RIA, family office analyst, active retail investor, crypto trader |
| **Motivation** | Make money, be early to trends, feel like an insider |
| **Job to be done** | "Know what smart people think before it's consensus" |
| **Time constraint** | Medium — values efficiency but has flexibility |
| **Why not Spotify** | No signal vs noise filtering; can't find credible sources; no insight extraction |
| **Success metric** | Portfolio performance, being early to trends, feeling informed |

### 1.3 Why Prosumers Choose Serafis Over Spotify/Apple

| Need | Spotify/Apple | Serafis |
|------|---------------|---------|
| Search by company mentioned | ❌ | ✅ |
| Search by person/speaker | ❌ | ✅ |
| Quality scoring (Insight, Credibility) | ❌ | ✅ |
| Claim/insight extraction | ❌ | ✅ |
| Non-consensus idea detection | ❌ | ✅ |

### 1.4 Key Differentiator

> **Spotify/Apple optimize for engagement (what's popular). Serafis optimizes for intelligence quality (what's valuable for decisions).**

---

## 2. Data Schema

### 2.1 Available User Signals

These are the signals provided by the founder for the recommendation engine:

| Signal | Fields | Description | Use in Recommendations |
|--------|--------|-------------|------------------------|
| **Activity** | `entity_type` (series/episode), `entity_id`, `visit_timestamp` | User's listening/viewing history | Implicit interest, "seen" filtering |
| **Bookmarks** | `entity_type` (series/episode), `entity_id`, `bookmark_timestamp` | Explicitly saved content | Strong interest signal |
| **Subscriptions** | `series_id`, `subscription_timestamp` | Series the user follows | "New from Your Shows" section |
| **Category Interests** | `category_name` | User's stated topic interests (AI, Crypto, etc.) | Primary personalization driver |

### 2.2 Derived User Context

From existing signals, we derive:

```python
class UserContext:
    user_id: str
    category_interests: List[str]         # From user category interests setting
    subscribed_series: List[str]          # From subscriptions
    seen_episode_ids: Set[str]            # From activity (entity_type=episode)
    bookmarked_episode_ids: Set[str]      # From bookmarks (entity_type=episode)
    not_interested_ids: Set[str]          # Future: explicit "not interested" feedback
```

**Note:** This specification uses existing signals only. A richer "Research Profile" with tracked companies/people could be added in a future phase.

### 2.3 Available Content Metadata

These fields are confirmed available from the Serafis platform:

| Field | Scope | Description | Confirmed |
|-------|-------|-------------|-----------|
| `insight_score` | Episode | Novelty and depth of ideas (1-4) | ✅ Yes |
| `credibility_score` | Episode | Speaker authority (1-4) | ✅ Yes |
| `information_score` | Episode | Data density (1-4) | ✅ Yes |
| `entertainment_score` | Episode | Engagement quality (1-4) | ✅ Yes (not used) |
| `categories` | Episode | Major themes + subcategories | ✅ Yes |
| `entities` | Episode | Companies mentioned with relevance (0-4) | ✅ Yes |
| `people` | Episode | People mentioned with relevance (0-4) | ✅ Yes |
| `summary` | Episode | AI-generated episode description | ✅ Yes |
| `key_insights` | Episode | Top 3 takeaways | ✅ Yes |
| `critical_views` | Episode | Non-consensus analysis text | ✅ Yes |
| `popularity` | Series | Series-level popularity score | ✅ Yes |
| `description` | Series/Episode | Text descriptions | ✅ Yes |

### 2.4 Key Insight Preview

For episode cards, surface a **1-sentence preview** from either:
1. First sentence of `key_insights[0]` (preferred)
2. First sentence of `summary` (fallback)

---

## 3. Interface Separation

Per the founder's guidance, the mobile app has two distinct interfaces:

| Interface | Purpose | Algorithm Focus |
|-----------|---------|-----------------|
| **Jump In / Recently Played** | Shows carousel of actual history | N/A — direct history display |
| **Recommendations** | Shows content user hasn't interacted with | **This specification** |

**Critical requirement:** Recommendations must **exclude** all episodes the user has already interacted with (from activity signals).

---

## 4. Discover Page Architecture

### 4.1 Section Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  DISCOVER                                                     🔍 Search │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  ⏱️ JUMP IN                                    [HISTORY - SEPARATE]│  │
│  │  Pick up where you left off                                       │  │
│  │  (Separate interface — not part of recommendations)               │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ════════════════════ RECOMMENDATIONS BELOW ═══════════════════════════ │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  📊 INSIGHTS FOR YOU                                              │  │
│  │  Based on AI & Machine Learning, Crypto & Web3                    │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                 │  │
│  │  │ Episode │ │ Episode │ │ Episode │ │ Episode │                 │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  💎 HIGHEST SIGNAL THIS WEEK                                      │  │
│  │  Top Insight + Credibility across all topics                      │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                 │  │
│  │  │ Episode │ │ Episode │ │ Episode │ │ Episode │                 │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  🔥 NON-CONSENSUS IDEAS                                           │  │
│  │  Contrarian views from credible speakers                          │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                 │  │
│  │  │ Episode │ │ Episode │ │ Episode │ │ Episode │                 │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  📡 NEW FROM YOUR SHOWS                                           │  │
│  │  Latest from subscribed series                                    │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                 │  │
│  │  │ Episode │ │ Episode │ │ Episode │ │ Episode │                 │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  🌟 TRENDING IN [CATEGORY]                                        │  │
│  │  Popular episodes in AI & Machine Learning                        │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                 │  │
│  │  │ Episode │ │ Episode │ │ Episode │ │ Episode │                 │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Section Definitions

| Section | Algorithm | Personalized? | Signal Used |
|---------|-----------|---------------|-------------|
| **Jump In** | Direct history | Yes | Activity (separate interface) |
| **Insights for You** | Category match + quality | Yes | Category interests |
| **Highest Signal** | Pure quality scores | No (global) | None |
| **Non-Consensus Ideas** | Critical Views + credibility | No (global) | None |
| **New from Your Shows** | Subscription-based | Yes | Subscriptions |
| **Trending in [Category]** | Popularity + category | Yes | Category interests |

### 4.3 Exclusion Rules

**All recommendation sections must exclude:**
1. Episodes the user has already viewed (from activity signals)
2. Episodes the user marked "Not Interested" (future feature)
3. Episodes the user has bookmarked (already saved = already discovered)

---

## 5. Episode Card Design

### 5.1 Layout

```
┌──────────────────────────────────────────────────────────────┐
│  ┌──────────┐                                                │
│  │          │  Episode Title (max 2 lines)                   │
│  │ [ARTWORK]│  Series Name                                   │
│  │          │  Jan 21 • 32 min                               │
│  └──────────┘  ───────────────────────────────               │
│                💎 High Insight  •  ⭐ High Credibility        │
│                                                              │
│  Key insight preview: "Jensen Huang discusses why           │
│  inference will dominate compute spend by 2027..."           │
│                                                              │
│  🏷️ AI & Machine Learning                                    │
│                                                              │
│  [🔖 Save]                                [⊘ Not Interested] │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Quality Badges

| Badge | Condition | Display |
|-------|-----------|---------|
| 💎 High Insight | `insight_score >= 3` | "💎 High Insight" |
| ⭐ High Credibility | `credibility_score >= 3` | "⭐ High Credibility" |
| 📊 Data-Rich | `information_score >= 3` | "📊 Data-Rich" |
| 🔥 Contrarian | Critical Views flags non-consensus | "🔥 Contrarian" |

Show up to 2 badges. Priority: Insight > Credibility > Information > Contrarian.

### 5.3 Key Difference from Spotify/Apple

| Element | Spotify/Apple | Serafis |
|---------|---------------|---------|
| Quality signal | None / user ratings | AI quality badges |
| Preview text | Description | Key insight extraction |
| Purpose | "Will I enjoy this?" | "Will this help my research?" |

---

## 6. Algorithm Specifications

### 6.1 Core Helper Functions

```python
from datetime import datetime, timedelta
from typing import List, Set

def get_user_context(user_id: str) -> UserContext:
    """Load user's existing signals into context object."""
    return UserContext(
        user_id=user_id,
        category_interests=get_user_category_interests(user_id),
        subscribed_series=get_user_subscriptions(user_id),
        seen_episode_ids=get_user_activity_episode_ids(user_id),
        bookmarked_episode_ids=get_user_bookmark_episode_ids(user_id),
        not_interested_ids=get_user_not_interested_ids(user_id)
    )

def filter_seen(episodes: List[Episode], user: UserContext) -> List[Episode]:
    """Remove episodes user has already interacted with."""
    excluded = user.seen_episode_ids | user.bookmarked_episode_ids | user.not_interested_ids
    return [ep for ep in episodes if ep.id not in excluded]

def calculate_quality_score(ep: Episode) -> float:
    """
    Core quality score: Insight (45%) + Credibility (40%) + Information (15%).
    Entertainment is excluded — not relevant for research value.
    """
    return (
        ep.scores.insight * 0.45 +
        ep.scores.credibility * 0.40 +
        ep.scores.information * 0.15
    ) / 4.0  # Normalize to 0-1

def days_since(dt: datetime) -> int:
    """Days since a given datetime."""
    return (datetime.utcnow() - dt).days

def diversify(episodes: List[Episode], limit: int, max_per_series: int = 2) -> List[Episode]:
    """Ensure variety: max 2 episodes per series."""
    result = []
    series_count = {}
    
    for ep in episodes:
        if series_count.get(ep.series_id, 0) >= max_per_series:
            continue
        result.append(ep)
        series_count[ep.series_id] = series_count.get(ep.series_id, 0) + 1
        if len(result) >= limit:
            break
    
    return result
```

### 6.2 "Insights for You"

Surfaces episodes matching user's category interests, weighted by quality.

```python
def get_insights_for_you(user_id: str, limit: int = 10) -> List[Episode]:
    """
    Episodes matching user's category interests, weighted by quality.
    Uses: category_interests signal
    """
    user = get_user_context(user_id)
    
    # Get episodes matching user's category interests
    candidates = []
    for category in user.category_interests:
        candidates.extend(get_episodes_by_category(category, limit=50))
    
    # Remove duplicates and filter seen
    candidates = list({ep.id: ep for ep in candidates}.values())
    candidates = filter_seen(candidates, user)
    
    # Score: 60% quality, 40% recency
    scored = []
    for ep in candidates:
        quality = calculate_quality_score(ep)
        recency = max(0, 1 - (days_since(ep.published_at) / 30))
        score = quality * 0.6 + recency * 0.4
        scored.append((ep, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return diversify([ep for ep, _ in scored], limit)
```

### 6.3 "Highest Signal This Week"

Global quality ranking — Serafis's core differentiator vs Spotify/Apple.

```python
def get_highest_signal(user_id: str, limit: int = 10, days: int = 7) -> List[Episode]:
    """
    Top quality episodes from the past week (global, minimally personalized).
    This is Serafis's unique value vs Spotify/Apple.
    """
    user = get_user_context(user_id)
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    recent = get_episodes_published_after(cutoff)
    recent = filter_seen(recent, user)
    
    # Pure quality score
    scored = [(ep, calculate_quality_score(ep)) for ep in recent]
    scored.sort(key=lambda x: x[1], reverse=True)
    
    return diversify([ep for ep, _ in scored], limit)
```

### 6.4 "Non-Consensus Ideas"

Contrarian views from credible speakers — unique Serafis value.

```python
def get_non_consensus_ideas(user_id: str, limit: int = 10, days: int = 14) -> List[Episode]:
    """
    Episodes with substantive critical_views analysis from high-credibility speakers.
    Requires: credibility_score >= 3 AND critical_views has content.
    """
    user = get_user_context(user_id)
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    recent = get_episodes_published_after(cutoff)
    recent = filter_seen(recent, user)
    
    # Filter to episodes with critical_views AND high credibility
    contrarian = [
        ep for ep in recent
        if ep.critical_views and len(ep.critical_views) > 50  # Has substantive analysis
        and ep.scores.credibility >= 3  # From credible source
    ]
    
    # Sort by insight (novel ideas) + credibility (trustworthy source)
    contrarian.sort(
        key=lambda ep: ep.scores.insight * 0.6 + ep.scores.credibility * 0.4,
        reverse=True
    )
    
    return diversify(contrarian, limit)
```

### 6.5 "New from Your Shows"

Latest episodes from user's subscribed series.

```python
def get_new_from_subscriptions(user_id: str, limit: int = 10) -> List[Episode]:
    """
    Latest episodes from user's subscribed series.
    Uses: subscriptions signal
    """
    user = get_user_context(user_id)
    
    # Get episodes from subscribed series
    candidates = []
    for series_id in user.subscribed_series:
        candidates.extend(get_episodes_by_series(series_id, limit=10))
    
    candidates = filter_seen(candidates, user)
    
    # Sort by recency (newest first), then by quality
    candidates.sort(
        key=lambda ep: (ep.published_at, calculate_quality_score(ep)),
        reverse=True
    )
    
    return candidates[:limit]
```

### 6.6 "Trending in [Category]"

Popular episodes in user's category interests.

```python
def get_trending_in_category(user_id: str, category: str, limit: int = 10, days: int = 14) -> List[Episode]:
    """
    Popular episodes in a specific category.
    Uses: category_interests signal + series popularity
    """
    user = get_user_context(user_id)
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    # Get recent episodes in category
    candidates = get_episodes_by_category(category, limit=50)
    candidates = [ep for ep in candidates if ep.published_at >= cutoff]
    candidates = filter_seen(candidates, user)
    
    # Score: 50% series popularity, 30% quality, 20% recency
    scored = []
    for ep in candidates:
        series_popularity = get_series_popularity(ep.series_id) / 100.0  # Normalize
        quality = calculate_quality_score(ep)
        recency = max(0, 1 - (days_since(ep.published_at) / days))
        score = series_popularity * 0.5 + quality * 0.3 + recency * 0.2
        scored.append((ep, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return diversify([ep for ep, _ in scored], limit)
```

### 6.7 Cold Start

For users with no category interests or subscriptions set.

```python
def get_cold_start_recommendations(user_id: str, limit: int = 10) -> List[Episode]:
    """
    Before category interests are set, show global Highest Signal.
    UI should prompt user to set preferences for personalization.
    """
    return get_highest_signal(user_id, limit)
```

### 6.8 Algorithm Weights Summary

| Algorithm | Quality Weight | Recency Weight | Other Factors |
|-----------|---------------|----------------|---------------|
| Insights for You | 60% | 40% | Category match required |
| Highest Signal | 100% | — | — |
| Non-Consensus | 60% insight, 40% cred | — | critical_views + cred >= 3 |
| New from Shows | Tiebreaker | — | Subscriptions required |
| Trending | 30% | 20% | 50% series popularity |

---

## 7. "Not Interested" Feedback

### 7.1 Data Model

```python
class NotInterested:
    user_id: str
    episode_id: str
    timestamp: datetime
```

### 7.2 Usage

- Exclude from all recommendation queries
- Future: Propagate penalty to similar content (same series, same primary entity)

---

## 8. API Specification

### 8.1 Endpoints

| Endpoint | Description | Personalized | Signals Used |
|----------|-------------|--------------|--------------|
| `GET /api/recommendations/insights-for-you` | Category-matched episodes | Yes | category_interests, activity |
| `GET /api/recommendations/highest-signal` | Top quality (global) | Minimal | activity (exclusion only) |
| `GET /api/recommendations/non-consensus` | Contrarian ideas | Minimal | activity (exclusion only) |
| `GET /api/recommendations/new-from-shows` | Subscription-based | Yes | subscriptions, activity |
| `GET /api/recommendations/trending/{category}` | Popular in category | Yes | category_interests, activity |
| `GET /api/recommendations/discover` | Full discover page | Yes | All signals |
| `POST /api/feedback/not-interested` | Mark as not interested | — | — |

### 8.2 Request Parameters

```
GET /api/recommendations/insights-for-you
  ?user_id=string       (required)
  &limit=int            (default: 10, max: 20)

GET /api/recommendations/highest-signal
  ?user_id=string       (required for exclusion)
  &limit=int            (default: 10)
  &days=int             (default: 7)

GET /api/recommendations/non-consensus
  ?user_id=string       (required for exclusion)
  &limit=int            (default: 10)
  &days=int             (default: 14)

GET /api/recommendations/new-from-shows
  ?user_id=string       (required)
  &limit=int            (default: 10)

GET /api/recommendations/trending/{category}
  ?user_id=string       (required for exclusion)
  &limit=int            (default: 10)
  &days=int             (default: 14)

GET /api/recommendations/discover
  ?user_id=string       (required)

POST /api/feedback/not-interested
  {
    "user_id": "string",
    "episode_id": "string"
  }
```

### 8.3 Response Format

```json
{
  "section": "insights_for_you",
  "title": "📊 Insights for You",
  "subtitle": "Based on AI & Machine Learning, Crypto & Web3",
  "episodes": [
    {
      "id": "ep_123",
      "title": "20VC: Sam Altman vs Elon Musk",
      "series": {
        "id": "series_456",
        "name": "The Twenty Minute VC",
        "artwork_url": "https://..."
      },
      "published_at": "2026-01-22T00:00:00Z",
      "duration_seconds": 3720,
      "key_insight": "Discusses the $100B legal battle and OpenAI's path to AGI...",
      "scores": {
        "insight": 4,
        "credibility": 4,
        "information": 3
      },
      "badges": ["high_insight", "high_credibility"],
      "categories": ["Technology & AI"]
    }
  ]
}
```

### 8.4 Discover Page Response

```json
{
  "sections": [
    {
      "section": "insights_for_you",
      "title": "📊 Insights for You",
      "subtitle": "Based on AI & Machine Learning",
      "episodes": [...]
    },
    {
      "section": "highest_signal",
      "title": "💎 Highest Signal This Week",
      "subtitle": "Top Insight + Credibility",
      "episodes": [...]
    },
    {
      "section": "non_consensus",
      "title": "🔥 Non-Consensus Ideas",
      "subtitle": "Contrarian views from credible speakers",
      "episodes": [...]
    },
    {
      "section": "new_from_shows",
      "title": "📡 New from Your Shows",
      "subtitle": "Latest from subscribed series",
      "episodes": [...]
    },
    {
      "section": "trending",
      "title": "🌟 Trending in AI & Machine Learning",
      "subtitle": "Popular this week",
      "episodes": [...]
    }
  ]
}
```

---

## 9. Implementation Approach

### 9.1 Mock Development (Recommended First)

Before integrating with production, build a mock system to validate algorithms:

| Phase | Task | Output |
|-------|------|--------|
| **Data Extraction** | Extract 50-100 episodes from Serafis website | `mock_data/episodes.json` |
| **Mock API** | Implement algorithms in FastAPI | `mock_api/` server |
| **Prototype UI** | React mobile-first prototype | Vercel deployment |
| **Validation** | Test algorithms with real data | Validated approach |

See [Mock Development Plan](./mock_development_plan.md) for detailed execution guide.

### 9.2 Production Integration

Once mock is validated:

| Task | Description |
|------|-------------|
| API Integration | Connect mobile app to production Serafis API |
| Signal Pipeline | Ensure activity/bookmark/subscription signals flow correctly |
| Algorithm Deployment | Port validated algorithms to production backend |
| A/B Testing | Compare recommendation quality vs baseline |

### 9.3 Future Enhancements (Out of Scope)

These features are valuable but not in initial scope:

| Feature | Description | Why Deferred |
|---------|-------------|--------------|
| Research Profile Onboarding | Role, tracked companies/people | Requires new UI + data model |
| Entity Tracking Sections | "Tracking: OpenAI" personalized | Requires entity watchlist feature |
| Embedding Similarity | "Related Research" | Requires embedding infrastructure |
| Not Interested Propagation | Penalize similar content | Requires similarity model |

---

## 10. Success Metrics

### 10.1 Quality-Oriented Metrics (Primary)

These metrics validate whether recommendations surface high-quality content:

| Metric | Definition | Target | Rationale |
|--------|------------|--------|-----------|
| **Avg quality of clicks** | Mean (insight + credibility) of clicked episodes | > 3.0 | Users engage with high-signal content |
| **Quality improvement** | Clicked quality vs. average corpus quality | > 1.2x | Recs surface better content than random |
| **Contrarian engagement** | CTR on Non-Consensus section | > 4% | Unique value proposition resonates |

### 10.2 Engagement Metrics (Secondary)

| Metric | Definition | Target |
|--------|------------|--------|
| **Section CTR** | Clicks / impressions per section | > 5% |
| **Not interested rate** | Not interested / impressions | < 5% |
| **Recommendation diversity** | Unique series in top 20 recs | > 8 |
| **Return rate** | Users returning within 7 days | > 30% |

### 10.3 Personalization Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Category match rate** | % of clicked episodes matching user interests | > 60% |
| **Subscription coverage** | % of subscribed series represented in recs | > 80% |
| **Seen exclusion accuracy** | % of recs that are truly unseen | 100% |

---

## 11. Design Decisions

### 11.1 Resolved Questions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Target user segment | **Prosumer only** | Mobile app focus, simpler scope |
| Personalization approach | **Use existing signals** | Activity, bookmarks, subscriptions, category interests |
| Critical Views reliability | **Assume reliable** | Per founder input |
| Key insight preview | **Use key_insights[0] or summary** | Confirmed available |
| Entertainment score | **Exclude from quality calc** | Not relevant for research value |

### 11.2 Future Decisions (Deferred)

| Question | Options | When to Decide |
|----------|---------|----------------|
| Entity tracking UI | Add to mobile app? | After MVP validation |
| Research Profile onboarding | Add professional context? | Based on user feedback |
| Collaborative filtering | "Users like you also liked"? | When user base scales |

---

## Appendix A: Serafis Intelligence Scores

| Score | Scale | Description | Weight in Recommendations |
|-------|-------|-------------|--------------------------|
| **Insight** | 1-4 | Novelty and depth of ideas | Primary (45%) |
| **Credibility** | 1-4 | Speaker authority | Primary (40%) |
| **Information** | 1-4 | Data density | Secondary (15%) |
| **Entertainment** | 1-4 | Engagement quality | Not used (entertainment ≠ research value) |

### Quality Score Calculation

```python
quality = (insight * 0.45 + credibility * 0.40 + information * 0.15) / 4.0
# Result: 0.0 to 1.0, where 1.0 = perfect scores (4, 4, 4)
```

### Badge Thresholds

| Badge | Condition | Display |
|-------|-----------|---------|
| 💎 High Insight | `insight_score >= 3` | "💎 High Insight" |
| ⭐ High Credibility | `credibility_score >= 3` | "⭐ High Credibility" |
| 📊 Data-Rich | `information_score >= 3` | "📊 Data-Rich" |
| 🔥 Contrarian | `critical_views` has substantive content | "🔥 Contrarian" |

---

## Appendix B: Prosumer User Behavior Model

This specification targets the prosumer segment. Expected behavior patterns:

| Behavior | Description | Recommendation Impact |
|----------|-------------|----------------------|
| **Category exploration** | Interested in AI, Crypto, Markets | "Insights for You" section |
| **Quality-seeking** | Wants credible, insightful content | "Highest Signal" resonates |
| **Contrarian interest** | Wants to be early to trends | "Non-Consensus" is high value |
| **Series loyalty** | Subscribes to favorite shows | "New from Shows" for retention |
| **Time-constrained** | Wants efficient discovery | Key insight previews matter |

### Sample Prosumer Profiles

| Profile | Category Interests | Subscribed Series | Behavior |
|---------|-------------------|-------------------|----------|
| **AI Prosumer** | Technology & AI, Startups | 20VC, a16z, No Priors | Tracks AI trends, OpenAI news |
| **Crypto Prosumer** | Crypto & Web3, Technology | All-In, Bankless | Tracks Bitcoin, Ethereum, DeFi |
| **Markets Prosumer** | Public Markets, Macro | Invest Like Best, Acquired | Tracks Nvidia, Tesla, macro themes |

---

## Appendix C: Available Metadata Reference

Confirmed available from Serafis platform:

| Field | Location | Use in Recommendations |
|-------|----------|------------------------|
| `insight_score` | Episode Analysis tab | Quality scoring |
| `credibility_score` | Episode Analysis tab | Quality scoring |
| `information_score` | Episode Analysis tab | Quality scoring |
| `summary` | Episode Analysis tab | Key insight preview fallback |
| `key_insights` | Episode Analysis tab | Key insight preview (primary) |
| `critical_views` | Episode Analysis tab | Non-consensus detection |
| `categories.major` | Episode Themes tab | Category matching |
| `categories.subcategories` | Episode Themes tab | Granular matching |
| `entities` | Episode Entities tab | Future: entity tracking |
| `people` | Episode People tab | Future: person tracking |
| `popularity` | Series metadata | Trending algorithm |

---

## Appendix D: Related Documents

- [Mock Development Plan](./mock_development_plan.md) — How to build and test without backend access
- [Competitor UI Research](./competitor_ui_research.md) — Spotify/Apple UI patterns
- [Strategic Positioning](./strategic_positioning.md) — Why Serafis vs alternatives
- [UI Examination](/Users/rohankatakam/Documents/serafis/ui/ui_examination.md) — Current web app features
- [Investor Memo](/Users/rohankatakam/Documents/serafis/serafis_investor_memo.md) — Company vision
