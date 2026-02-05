# Serafis "For You" Feed — V1.2 Specification

> *2-stage recommendation pipeline with blended scoring (similarity + quality + recency)*

**Version:** 1.2  
**Date:** February 5, 2026  
**Status:** Implemented  
**Parent Document:** FOR_YOU_SPEC_FINAL.html (original 3-stage design)

---

## Executive Summary

This specification defines a **2-stage recommendation architecture** with blended scoring that combines semantic similarity, quality metrics, and content recency into a unified ranking score.

**Key Features (V1.2):**
- Pre-filter candidates by quality gates and freshness (Stage A)
- Blended final scoring: `55% similarity + 30% quality + 15% recency` (Stage B)
- Credibility weighted 1.5x higher than insight in quality score
- Engagement-type weighting (bookmarks count 2x, listens 1.5x)
- Modular architecture: `recommendation_engine.py`, `data_loader.py`, `models.py`

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    V1.2 BLENDED SCORING PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STAGE A: CANDIDATE POOL PRE-SELECTION (Quality Gates)                      │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  INPUT: Full Episode Catalog (561 episodes)                            │ │
│  │                                                                         │ │
│  │  FILTERS (Applied in Order):                                           │ │
│  │    1. Credibility ≥ 2 (investor safety floor)                          │ │
│  │    2. Credibility + Insight ≥ 5 (combined quality threshold)           │ │
│  │    3. Published within 90 days (freshness window)                      │ │
│  │    4. Episode NOT in user's excluded_ids                               │ │
│  │                                                                         │ │
│  │  SORTING: By quality_score (Cred*1.5 + Insight) descending             │ │
│  │  LIMIT: Top 150 candidates                                             │ │
│  │                                                                         │ │
│  │  OUTPUT: Candidate Pool (~150 episodes)                                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  STAGE B: BLENDED SCORING (Similarity + Quality + Recency)                  │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                         │ │
│  │  For each candidate, compute:                                          │ │
│  │                                                                         │ │
│  │  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐      │ │
│  │  │ SIMILARITY (55%)│   │ QUALITY (30%)   │   │ RECENCY (15%)   │      │ │
│  │  │                 │   │                 │   │                 │      │ │
│  │  │ cosine_sim(     │   │ (C * 1.5 + I)   │   │ exp(-0.03 *     │      │ │
│  │  │   user_vector,  │   │ ─────────────   │   │   days_old)     │      │ │
│  │  │   ep_embedding) │   │      10.0       │   │                 │      │ │
│  │  └────────┬────────┘   └────────┬────────┘   └────────┬────────┘      │ │
│  │           │                     │                     │               │ │
│  │           └─────────────────────┼─────────────────────┘               │ │
│  │                                 ▼                                      │ │
│  │                    final_score = 0.55*sim + 0.30*qual + 0.15*rec      │ │
│  │                                                                         │ │
│  │  OUTPUT: Top 10 by final_score                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage A: Candidate Pool Pre-Selection

### Purpose

Create a quality-filtered, fresh pool of episodes before applying blended scoring. This ensures:
1. All candidates meet investor-grade quality thresholds
2. Search space is bounded (150 candidates vs 561)
3. Blended scoring operates on a clean, high-quality dataset

### Input

- Full episode catalog
- User's excluded_ids (seen ∪ bookmarked ∪ not_interested)

### Filters

| Order | Filter | Threshold | Rationale |
|-------|--------|-----------|-----------|
| 1 | Credibility | ≥ 2 | Investor safety floor — no unverified sources |
| 2 | Combined Quality | C + I ≥ 5 | Ensures minimum total quality |
| 3 | Freshness | ≤ 90 days | Balances freshness with content availability |
| 4 | Exclusion | NOT in excluded_ids | No re-recommendations |

### Sorting

Episodes are sorted by **quality_score** `(Credibility * 1.5 + Insight)` descending. This weights credibility higher than insight in the pre-selection phase.

### Output

Top 150 episodes that pass all filters.

### Tunable Parameters

| Parameter | Default | Range | Priority |
|-----------|---------|-------|----------|
| Credibility floor | 2 | 2-3 | Fixed |
| Combined floor | 5 | 4-6 | Medium |
| Freshness window | 90 days | 30-120 | Medium |
| Pool size | 150 | 50-200 | Low |

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| < 150 candidates pass filters | Return all that pass (may be < 150) |
| < 75 candidates in window | Expand freshness: 60 → 90 days |
| User excluded all candidates | Return empty, show "You've seen everything" |

---

## Stage B: Blended Scoring

### Purpose

Rank candidates using a weighted combination of three signals:
1. **Semantic Similarity (55%)** — How well the episode matches user interests
2. **Quality Score (30%)** — Episode credibility and insight (credibility weighted 1.5x)
3. **Recency Score (15%)** — Freshness of the content (exponential decay)

This ensures recommendations balance relevance, quality, and timeliness.

### B.1: Embedding Strategy

#### What to Embed

| Field | Include? | Rationale |
|-------|----------|-----------|
| `title` | ✅ Yes | Core semantic content, concise |
| `critical_views.key_insights` | ✅ Yes | Distilled takeaways, high signal |
| `key_insight` | ✅ Fallback | Used if key_insights unavailable |
| `series.name` | ❌ No | Would cluster by podcast, not content |
| `categories.major` | ❌ No | Already used in pre-filtering, redundant |
| `entities[].name` | ❌ No | Would over-weight company mentions |
| Full description | ❌ No | Often promotional, adds noise |

#### Embedding Formula

```python
def get_embed_text(episode: dict) -> str:
    """Generate text for embedding - same for episodes and user activity."""
    title = episode.get("title", "")
    
    # Prefer critical_views.key_insights, fallback to key_insight
    critical_views = episode.get("critical_views") or {}
    key_insights = critical_views.get("key_insights") or episode.get("key_insight") or ""
    
    # Truncate key_insights to first 500 chars to reduce noise
    if len(key_insights) > 500:
        key_insights = key_insights[:500]
    
    return f"{title}. {key_insights}"
```

#### Embedding Model

- **Model:** `text-embedding-3-small` (OpenAI)
- **Dimensions:** 1536
- **Cost:** ~$0.02 per 1M tokens (~$0.10 for 561 episodes)

### B.2: User Activity Vector

#### Engagement Types & Weights

| Engagement Type | Weight | Description |
|-----------------|--------|-------------|
| Bookmark | 2.0 | Explicit save action — strong signal |
| Listen (future) | 1.5 | Deep engagement |
| Click/Tap | 1.0 | User opened episode details — standard signal |

#### Weighted Mean Implementation (V1.2)

```python
def get_user_vector_mean(
    engagements: List[Dict],
    limit: int = 10,
    engagement_weights: Dict[str, float] = {"bookmark": 2.0, "listen": 1.5, "click": 1.0}
) -> Optional[List[float]]:
    """
    Compute user activity vector using weighted mean-pooling.
    Engagements are weighted by type (bookmarks count 2x).
    """
    if not engagements:
        return None
    
    # Sort by timestamp, most recent first
    sorted_eng = sorted(engagements, key=lambda e: e.get("timestamp", ""), reverse=True)[:limit]
    
    vectors = []
    weights = []
    
    for eng in sorted_eng:
        embedding = get_embedding(eng["episode_id"])
        if embedding:
            eng_type = eng.get("type", "click")
            weight = engagement_weights.get(eng_type, 1.0)
            vectors.append(np.array(embedding) * weight)
            weights.append(weight)
    
    if not vectors:
        return None
    
    # Weighted mean
    return list(sum(vectors) / sum(weights))
```

### B.3: Scoring Functions

#### Similarity Score (55% weight)

```python
def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    v1, v2 = np.array(v1), np.array(v2)
    dot_product = np.dot(v1, v2)
    norm_product = np.linalg.norm(v1) * np.linalg.norm(v2)
    return float(dot_product / norm_product) if norm_product > 0 else 0.0
```

#### Quality Score (30% weight)

```python
def quality_score(credibility: int, insight: int) -> float:
    """
    Compute normalized quality score with credibility weighted 1.5x higher.
    Returns value between 0 and 1.
    """
    # Max possible: 4 * 1.5 + 4 = 10
    raw_score = credibility * 1.5 + insight
    return raw_score / 10.0
```

#### Recency Score (15% weight)

```python
def recency_score(days_old: int, lambda_val: float = 0.03) -> float:
    """
    Compute recency score with exponential decay.
    λ=0.03 gives ~23 day half-life (fresher content scores higher).
    """
    return math.exp(-lambda_val * days_old)
```

### B.4: Blended Final Ranking

```python
def rank_candidates(
    user_vector: List[float],
    candidates: List[Episode],
    weights: Dict[str, float] = {"similarity": 0.55, "quality": 0.30, "recency": 0.15}
) -> List[ScoredEpisode]:
    """
    Rank candidates using blended scoring.
    
    final_score = w_sim * similarity + w_qual * quality + w_rec * recency
    """
    scored = []
    
    for ep in candidates:
        # Compute similarity
        sim = cosine_similarity(user_vector, get_embedding(ep["id"]))
        
        # Compute quality (credibility weighted 1.5x)
        qual = quality_score(ep["scores"]["credibility"], ep["scores"]["insight"])
        
        # Compute recency
        age = days_since(ep["published_at"])
        rec = recency_score(age)
        
        # Blend scores
        final = (
            weights["similarity"] * sim +
            weights["quality"] * qual +
            weights["recency"] * rec
        )
        
        scored.append(ScoredEpisode(ep, sim, qual, rec, final))
    
    scored.sort(key=lambda x: x.final_score, reverse=True)
    return scored[:10]
```

---

## Cold Start Handling

### Condition

User has 0 engagements (no clicks, no bookmarks).

### Fallback Strategy

When no engagements exist, the scoring weights shift:

```python
# Cold start scoring (no similarity signal)
final_score = 0.0 * similarity + 0.60 * quality + 0.40 * recency
```

1. **Quality dominates (60%)** — Show highest quality content first
2. **Recency matters (40%)** — Prefer fresh content
3. **Similarity neutral (0%)** — No user vector to compare against

### UI Treatment

- Label section as **"Highest Signal"** (not "For You")
- Subtitle: "Top quality episodes"
- `cold_start: true` in API response

---

## Data Flow

```
User Opens App
       │
       ▼
┌──────────────────┐
│ Load User State  │
│ - engagements[]  │
│ - excluded_ids   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────────┐
│ Stage A:         │     │ Episode Catalog  │
│ Pre-Selection    │◀────│ (561 episodes)   │
│ - Quality gates  │     └──────────────────┘
│ - Freshness ≤90d │
│ - Exclusions     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Candidate Pool   │
│ (~150 episodes)  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────────┐
│ Stage B:         │     │ User Engagements │
│ Blended Scoring  │◀────│ (last 10 clicks) │
│ - Similarity 55% │     └──────────────────┘
│ - Quality 30%    │
│ - Recency 15%    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Final Output     │
│ Top 10 episodes  │
│ (with scores)    │
└──────────────────┘
```

---

## Implementation

### Module Structure (V1.2)

```
mock_api/
├── server.py                  # FastAPI routes (~300 lines)
├── recommendation_engine.py   # Core algorithm (scoring, ranking)
├── data_loader.py            # Data loading with singleton cache
├── models.py                 # Pydantic request/response models
├── generate_embeddings.py    # One-time embedding generation
└── data/
    ├── episodes.json         # 561 episodes with metadata
    ├── embeddings.json       # Pre-computed 1536-dim vectors
    └── series.json           # Podcast series metadata
```

### V1.2 Implementation (Current)

**Scope:**
- Pre-filter to 150 candidates (90-day window)
- Embed: `title + key_insights` only
- User vector: Last 10 engagements, weighted by type
- Blended scoring: 55% similarity + 30% quality + 15% recency
- Credibility weighted 1.5x in quality score
- Recency decay: λ=0.03 (~23 day half-life)

**Key Files:**
1. `recommendation_engine.py` — `RecommendationConfig`, `rank_candidates()`, `quality_score()`, `recency_score()`
2. `data_loader.py` — `DataCache` singleton for efficient data access
3. `models.py` — `ScoredEpisode`, `SessionResponse` with full score breakdown
4. `server.py` — Clean API routes using modular components

### Future: V2.0

**Planned Scope:**
- Narrative reranking (series cap, entity diversity)
- POV boost (Consensus → Contrarian)
- Sum-of-similarities option for diverse interests
- Category overlap scoring

---

## API Specification

### POST /api/sessions/create (Primary)

**Request:**
```json
POST /api/sessions/create
Content-Type: application/json

{
  "engagements": [
    {"episode_id": "abc123", "type": "click", "timestamp": "2026-02-04T10:00:00Z"},
    {"episode_id": "def456", "type": "bookmark", "timestamp": "2026-02-03T15:30:00Z"}
  ],
  "excluded_ids": ["abc123", "def456", "ghi789"]
}
```

**Response:**
```json
{
  "session_id": "ef12c12f",
  "algorithm": "v1.2_blended",
  "cold_start": false,
  "total_in_queue": 150,
  "shown_count": 10,
  "remaining_count": 140,
  "episodes": [
    {
      "id": "xyz789",
      "content_id": "episode-slug",
      "title": "Episode Title",
      "series": {"id": "series-id", "name": "Series Name"},
      "published_at": "2026-02-01T09:00:00Z",
      "scores": {"insight": 3, "credibility": 4, "information": 3, "entertainment": 2},
      "badges": ["high_insight", "high_credibility"],
      "categories": {"major": ["Technology & AI"], "subcategories": []},
      "key_insight": "...",
      "similarity_score": 0.5945,
      "quality_score": 0.9,
      "recency_score": 0.8106,
      "final_score": 0.7185,
      "queue_position": 1
    }
  ],
  "debug": {
    "candidates_count": 150,
    "user_vector_episodes": 2,
    "embeddings_available": true,
    "top_similarity_scores": [0.594, 0.580, 0.555],
    "top_quality_scores": [0.9, 0.9, 0.9],
    "top_final_scores": [0.719, 0.711, 0.697],
    "scoring_weights": {"similarity": 0.55, "quality": 0.3, "recency": 0.15}
  }
}
```

### POST /api/recommendations/for-you (Legacy)

Same request format, returns legacy response structure for backwards compatibility.

---

## Metrics & Monitoring

### Key Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Final Score Range | Distribution of blended scores | Mean > 0.6 |
| Similarity Range | Distribution of similarity scores | Mean > 0.5 |
| Personalization Delta | Difference from cold start | Measurable difference |
| Coverage | % of candidates appearing in any user's top 10 | > 30% |
| Freshness | Avg days old of recommended episodes | < 21 days |

### Debug Logging

Every recommendation request logs via `SessionDebugInfo`:
```json
{
  "candidates_count": 150,
  "user_vector_episodes": 5,
  "embeddings_available": true,
  "top_similarity_scores": [0.59, 0.58, 0.55],
  "top_quality_scores": [0.9, 0.9, 0.85],
  "top_final_scores": [0.72, 0.71, 0.69],
  "scoring_weights": {"similarity": 0.55, "quality": 0.3, "recency": 0.15}
}
```

---

## Appendix: Parameter Reference

### Fixed Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Credibility floor | ≥ 2 | Investor safety — non-negotiable |
| Embedding model | text-embedding-3-small | Cost-effective, good quality |
| Embedding dimensions | 1536 | Standard for chosen model |

### Scoring Weights (V1.2)

| Weight | Value | Rationale |
|--------|-------|-----------|
| Similarity | 0.55 | Primary signal — relevance to user interests |
| Quality | 0.30 | Secondary signal — episode credibility & insight |
| Recency | 0.15 | Tertiary signal — freshness of content |
| Credibility multiplier | 1.5x | Weight credibility higher than insight |

### Tunable Parameters

| Parameter | Default | Range | When to Tune |
|-----------|---------|-------|--------------|
| Combined floor (C+I) | 5 | 4-6 | If pool too small/large |
| Freshness window | 90 days | 30-120 | If content feels stale/sparse |
| Pool size | 150 | 50-200 | If diversity issues |
| User vector size (N) | 10 | 5-15 | If personalization too strong/weak |
| Recency λ | 0.03 | 0.02-0.05 | If old content dominates (~23d half-life) |
| Weight similarity | 0.55 | 0.4-0.7 | If relevance vs quality imbalanced |
| Weight quality | 0.30 | 0.2-0.4 | If quality not surfacing |
| Weight recency | 0.15 | 0.1-0.25 | If freshness not valued |

### Engagement Type Weights

| Type | Weight | Rationale |
|------|--------|-----------|
| Bookmark | 2.0 | Strong explicit signal |
| Listen | 1.5 | Deep engagement |
| Click | 1.0 | Standard signal |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.2 | Feb 5, 2026 | Blended scoring (sim+qual+rec), credibility 1.5x, modular architecture |
| 1.1 | Feb 4, 2026 | Initial refined spec with 2-stage architecture |
