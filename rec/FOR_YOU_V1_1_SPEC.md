# Serafis "For You" Feed — V1.1 Refined Specification

> *Refined 2-stage recommendation pipeline with noise-reduced embeddings*

**Version:** 1.1  
**Date:** February 4, 2026  
**Status:** Implementation Ready  
**Parent Document:** FOR_YOU_SPEC_FINAL.html (original 3-stage design)

---

## Executive Summary

This specification refines the original 3-stage recommendation pipeline into a **cleaner 2-stage architecture** that separates quality/recency filtering from semantic matching. The goal is to reduce noise, enable faster iteration, and establish a baseline before adding complexity.

**Key Changes from Original Spec:**
- Pre-filter candidates BEFORE embedding similarity (reduces search space)
- Careful embedding field selection (title + key_insights only)
- Staged implementation: Option A → B → C
- Deferred Stage 3 (narrative reranking) to V2

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    V1.1 REFINED 2-STAGE PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STAGE A: CANDIDATE POOL PRE-SELECTION (Non-Semantic Filtering)             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  INPUT: Full Episode Catalog (561 episodes)                            │ │
│  │                                                                         │ │
│  │  FILTERS (Applied in Order):                                           │ │
│  │    1. Credibility ≥ 2 (investor safety floor)                          │ │
│  │    2. Credibility + Insight ≥ 5 (combined quality threshold)           │ │
│  │    3. Published within 30 days (freshness window)                      │ │
│  │    4. Episode NOT in user's excluded_ids                               │ │
│  │                                                                         │ │
│  │  SORTING: By (Credibility + Insight) descending                        │ │
│  │  LIMIT: Top 50 candidates                                              │ │
│  │                                                                         │ │
│  │  OUTPUT: Candidate Pool (~50 episodes)                                 │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  STAGE B: SEMANTIC MATCHING (Embedding-Based Similarity)                     │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                         │ │
│  │  USER ACTIVITY VECTOR                    CANDIDATE EMBEDDINGS          │ │
│  │  ┌─────────────────────┐                 ┌─────────────────────┐       │ │
│  │  │ Recent engagements: │                 │ Each candidate:     │       │ │
│  │  │ - Last N clicked    │                 │                     │       │ │
│  │  │ - Bookmarked        │                 │                     │       │ │
│  │  │                     │  ──COSINE SIM──▶│                     │       │ │
│  │  │ Embed with:         │                 │ Embed with:         │       │ │
│  │  │ - title             │                 │ - title             │       │ │
│  │  │ - key_insights      │                 │ - key_insights      │       │ │
│  │  └─────────────────────┘                 └─────────────────────┘       │ │
│  │                                                                         │ │
│  │  OUTPUT: Top 10 by cosine similarity                                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage A: Candidate Pool Pre-Selection

### Purpose

Create a quality-filtered, fresh pool of episodes before applying semantic matching. This ensures:
1. All candidates meet investor-grade quality thresholds
2. Search space is bounded (50 candidates vs 561)
3. Semantic matching operates on a clean dataset

### Input

- Full episode catalog
- User's excluded_ids (seen ∪ bookmarked ∪ not_interested)

### Filters

| Order | Filter | Threshold | Rationale |
|-------|--------|-----------|-----------|
| 1 | Credibility | ≥ 2 | Investor safety floor — no unverified sources |
| 2 | Combined Quality | C + I ≥ 5 | Ensures minimum total quality |
| 3 | Freshness | ≤ 30 days | Keeps content timely |
| 4 | Exclusion | NOT in excluded_ids | No re-recommendations |

### Sorting

Episodes are sorted by `(Credibility + Insight)` descending to ensure highest quality candidates are prioritized.

### Output

Top 50 episodes that pass all filters.

### Tunable Parameters

| Parameter | Default | Range | Priority |
|-----------|---------|-------|----------|
| Credibility floor | 2 | 2-3 | Fixed |
| Combined floor | 5 | 4-6 | Medium |
| Freshness window | 30 days | 14-60 | Medium |
| Pool size | 50 | 30-100 | Low |

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| < 50 candidates pass filters | Return all that pass (may be < 50) |
| 0 candidates in 30 days | Expand to 60 days, then 90 days |
| User excluded all candidates | Return empty, show "You've seen everything" |

---

## Stage B: Semantic Matching

### Purpose

Match user interests to candidate pool via embedding similarity. This stage finds episodes semantically similar to what the user has engaged with.

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

#### Engagement Types

| Engagement Type | Signal Strength | Description |
|-----------------|-----------------|-------------|
| Click/Tap | Standard | User opened episode details |
| Bookmark | Strong | Explicit save action |
| Listen (future) | Strong | Deep engagement |

#### Option A: Simple Mean (V1.0)

```python
def get_user_vector_simple(engagements: List[Engagement], limit: int = 5) -> Vector:
    """Simple mean of most recent engagements."""
    # Sort by recency, take most recent N
    recent = sorted(engagements, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    if not recent:
        return None  # Cold start
    
    vectors = [get_embedding(e.episode) for e in recent]
    return np.mean(vectors, axis=0)
```

#### Option B: Weighted Mean (V1.5)

```python
def get_user_vector_weighted(engagements: List[Engagement], limit: int = 10) -> Vector:
    """Weighted mean with engagement type and recency."""
    TYPE_WEIGHTS = {
        "bookmark": 2.0,
        "listen": 1.5,
        "click": 1.0
    }
    RECENCY_LAMBDA = 0.05  # ~14 day half-life
    
    recent = sorted(engagements, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    if not recent:
        return None
    
    weighted_vectors = []
    total_weight = 0
    
    for eng in recent:
        days_ago = (datetime.now() - eng.timestamp).days
        type_weight = TYPE_WEIGHTS.get(eng.type, 1.0)
        recency_weight = math.exp(-RECENCY_LAMBDA * days_ago)
        combined_weight = type_weight * recency_weight
        
        vector = get_embedding(eng.episode)
        weighted_vectors.append(vector * combined_weight)
        total_weight += combined_weight
    
    return sum(weighted_vectors) / total_weight
```

### B.3: Similarity Scoring

```python
def cosine_similarity(v1: Vector, v2: Vector) -> float:
    """Compute cosine similarity between two vectors."""
    dot_product = np.dot(v1, v2)
    norm_product = np.linalg.norm(v1) * np.linalg.norm(v2)
    return dot_product / norm_product if norm_product > 0 else 0.0
```

### B.4: Final Ranking

```python
def rank_candidates(user_vector: Vector, candidates: List[Episode]) -> List[Episode]:
    """Rank candidates by similarity to user vector."""
    scored = []
    for ep in candidates:
        ep_vector = get_embedding(ep)
        sim = cosine_similarity(user_vector, ep_vector)
        scored.append((ep, sim))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return [ep for ep, _ in scored[:10]]
```

---

## Cold Start Handling

### Condition

User has 0 engagements (no clicks, no bookmarks).

### Fallback Strategy

1. **If user has category_interests** (from onboarding):
   - Embed category names as pseudo user vector
   - `user_vector = embed("Technology & AI, Startups")`

2. **If no interests** (pure cold start):
   - Skip semantic matching
   - Return top 10 from candidate pool by (C + I) score
   - Label section as "Highest Signal" not "For You"

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
│ - Freshness      │
│ - Exclusions     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Candidate Pool   │
│ (~50 episodes)   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────────┐
│ Stage B:         │     │ User Engagements │
│ Semantic Match   │◀────│ (last 5 clicks)  │
│ - User vector    │     └──────────────────┘
│ - Cosine sim     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Final Output     │
│ Top 10 episodes  │
└──────────────────┘
```

---

## Implementation Stages

### Stage A Implementation (Option A) — V1.0

**Scope:**
- Pre-filter to 50 candidates
- Embed: `title + key_insights` only
- User vector: Last 5 engagements, simple mean
- No recency/type weighting

**Deliverables:**
1. `generate_embeddings.py` — One-time script to embed all episodes
2. `embeddings.json` — Pre-computed embeddings storage
3. Updated `server.py` — API with semantic matching

### Stage B Implementation (Option B) — V1.5

**Additional Scope:**
- User vector: Last 10 engagements
- Weighted by engagement type (bookmark=2.0, click=1.0)
- Weighted by recency (λ=0.05)

### Stage C Implementation (Option C) — V2.0

**Additional Scope:**
- Narrative reranking (series cap, entity diversity)
- POV boost (Consensus → Contrarian)
- Full Stage 3 from original spec

---

## API Specification

### GET /api/recommendations/for-you

**Request:**
```
GET /api/recommendations/for-you?limit=10
Content-Type: application/json

Body (optional):
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
  "section": "for_you",
  "title": "For You",
  "subtitle": "Based on your recent activity",
  "algorithm": "v1.1_semantic",
  "cold_start": false,
  "episodes": [
    {
      "id": "xyz789",
      "content_id": "episode-slug",
      "title": "Episode Title",
      "series": {"id": "series-id", "name": "Series Name"},
      "published_at": "2026-02-01T09:00:00Z",
      "scores": {"insight": 3, "credibility": 4, "information": 3, "entertainment": 2},
      "similarity_score": 0.847,
      "categories": {"major": ["Technology & AI"], "subcategories": []},
      "key_insight": "...",
      "critical_views": {...}
    }
  ],
  "debug": {
    "candidates_count": 50,
    "user_vector_episodes": 5,
    "filters_applied": ["credibility>=2", "c+i>=5", "freshness<=30d", "exclusions"]
  }
}
```

---

## Metrics & Monitoring

### Key Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Similarity Range | Distribution of S_sim scores | Mean > 0.5 |
| Personalization Delta | Difference from cold start | Measurable difference |
| Coverage | % of candidates appearing in any user's top 10 | > 30% |
| Freshness | Avg days old of recommended episodes | < 14 days |

### Debug Logging

Every recommendation request should log:
```json
{
  "request_id": "uuid",
  "user_engagements_count": 5,
  "candidates_after_filters": 47,
  "cold_start": false,
  "top_similarity_scores": [0.87, 0.82, 0.79, ...],
  "processing_time_ms": 45
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

### Tunable Parameters

| Parameter | Default | Range | When to Tune |
|-----------|---------|-------|--------------|
| Combined floor (C+I) | 5 | 4-6 | If pool too small/large |
| Freshness window | 30 days | 14-60 | If content feels stale/sparse |
| Pool size | 50 | 30-100 | If diversity issues |
| User vector size (N) | 5 | 3-10 | If personalization too strong/weak |
| Recency λ (Option B) | 0.05 | 0.03-0.10 | If old interests dominate |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | Feb 4, 2026 | Initial refined spec with 2-stage architecture |
