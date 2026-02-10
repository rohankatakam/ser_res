# Architecture Overview

**Document:** 01 of 07 | Algorithm Evolution Documentation  
**Last Updated:** 2026-02-10

---

## System Architecture

The Serafis recommendation engine uses a **2-stage pipeline** architecture that balances quality filtering with personalized ranking.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RECOMMENDATION PIPELINE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │   Episode    │───▶│   Stage A    │───▶│   Stage B    │───▶│   Top N   │ │
│  │   Catalog    │    │  Pre-filter  │    │   Ranking    │    │  Results  │ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └───────────┘ │
│       909 eps            ~150 eps          Scored & Sorted      10 eps      │
│                                                                              │
│  ┌──────────────┐    ┌──────────────────────────────────────────────────┐  │
│  │    User      │───▶│              User Vector Generation               │  │
│  │ Engagements  │    │  (weighted sum of engaged episode embeddings)     │  │
│  └──────────────┘    └──────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage A: Candidate Pool Pre-Selection

**Purpose:** Filter the episode catalog to a manageable candidate pool while enforcing quality gates.

### Quality Gates

| Gate | Threshold | Rationale |
|------|-----------|-----------|
| Credibility Floor | ≥ 2 | Exclude unreliable sources |
| Combined Floor (C+I) | ≥ 5 | Ensure substantive content |
| Freshness Window | 90 days | Prioritize recent content |

### Exclusion Logic

```python
excluded_ids = set()
excluded_ids.update(engaged_episode_ids)      # Don't re-recommend
excluded_ids.update(explicit_exclusions)       # User/system exclusions
```

### Output

- **Candidate Pool Size:** ~150 episodes (configurable)
- **Guarantees:** All candidates pass quality gates

---

## Stage B: Personalized Ranking

**Purpose:** Score and rank candidates based on user preferences and content attributes.

### Scoring Formula

```
final_score = (weight_similarity × similarity_score) +
              (weight_quality × quality_score) +
              (weight_recency × recency_score)
```

**Current Weights (v1.5):**
- `weight_similarity`: 0.85 (personalization)
- `weight_quality`: 0.10 (content quality)
- `weight_recency`: 0.05 (freshness boost)

### Component Scores

#### Similarity Score

Measures alignment between candidate and user interests.

**Cold Start Mode (no engagements):**
```python
similarity_score = 0.0  # Falls back to quality + recency
```

**Personalized Mode:**

*Mean-pooling (v1.0-v1.2):*
```python
user_vector = mean(engaged_episode_embeddings)
similarity_score = cosine_similarity(user_vector, candidate_embedding)
```

*Sum-of-similarities (v1.3+):*
```python
similarities = [cosine_sim(candidate, engaged) * weight for engaged in engagements]
similarity_score = sum(similarities) / normalization_factor
```

**Engagement Weights (v1.5):**
| Action | Weight | Signal Strength |
|--------|--------|-----------------|
| Bookmark | 10.0 | Strongest intent signal |
| Listen | 1.5 | Moderate interest |
| Click | 1.0 | Baseline interest |

#### Quality Score

Normalized composite of source credibility and content insight.

```python
quality_score = (credibility / 4.0) * credibility_multiplier * (insight / 5.0)
quality_score = min(quality_score, 1.0)  # Capped at 1.0
```

#### Recency Score

Exponential decay based on publication date.

```python
days_old = (today - published_at).days
recency_score = exp(-recency_lambda * days_old)
# recency_lambda = 0.03 → half-life ≈ 23 days
```

---

## Cold Start Handling

### Detection

```python
cold_start = len(engagements) == 0 or user_vector is None
```

### Cold Start Scoring (v1.0-v1.4)

When no user vector exists:
```python
final_score = (weight_quality × quality_score) + (weight_recency × recency_score)
```

### Cold Start Category Diversity (v1.5)

**New in v1.5:** Ensures balanced representation across major content categories.

```python
def apply_cold_start_category_diversity(scored, config, top_n=10):
    """
    Round-robin selection: take min_per_category from each category,
    then fill remaining slots with highest-scoring remaining episodes.
    """
    categories = [
        "Technology & AI",
        "Startups, Growth and Founder Journeys",
        "Macro, Investing & Market Trends",
        "Crypto & Web3",
        "Regulation & Policy",
        "Venture & Private Markets",
        "Culture, Society & Wellbeing"
    ]
    # ... implementation details
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  INPUTS                           PROCESSING                    OUTPUTS      │
│  ──────                           ──────────                    ───────      │
│                                                                              │
│  ┌───────────────┐                                                          │
│  │ Episode Data  │──┐                                                       │
│  │ (909 items)   │  │         ┌─────────────────────┐                       │
│  └───────────────┘  │         │                     │                       │
│                     ├────────▶│  Stage A: Filter    │──┐                    │
│  ┌───────────────┐  │         │  (Quality Gates)    │  │                    │
│  │  Embeddings   │──┤         └─────────────────────┘  │                    │
│  │ (1536-dim)    │  │                                  │                    │
│  └───────────────┘  │                                  ▼                    │
│                     │         ┌─────────────────────┐      ┌────────────┐  │
│  ┌───────────────┐  │         │                     │      │            │  │
│  │ User Profile  │──┼────────▶│  Stage B: Rank      │─────▶│  Top 10    │  │
│  │ (engagements) │  │         │  (Scoring Formula)  │      │  Results   │  │
│  └───────────────┘  │         └─────────────────────┘      │            │  │
│                     │                  ▲                    └────────────┘  │
│  ┌───────────────┐  │                  │                                    │
│  │ Config/Params │──┘                  │                                    │
│  │ (weights)     │─────────────────────┘                                    │
│  └───────────────┘                                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Classes and Functions

| Component | Location | Purpose |
|-----------|----------|---------|
| `RecommendationConfig` | `recommendation_engine.py` | Parameter container |
| `ScoredEpisode` | `recommendation_engine.py` | Scored result dataclass |
| `rank_candidates()` | `recommendation_engine.py` | Main ranking function |
| `get_user_vector_mean()` | `recommendation_engine.py` | Mean-pooled user vector |
| `apply_cold_start_category_diversity()` | `recommendation_engine.py` (v1.5+) | Diversity reranking |

---

## Embedding Strategy

| Property | Value |
|----------|-------|
| Model | `text-embedding-3-small` |
| Dimensions | 1536 |
| Input Fields | `title + key_insight` |
| Similarity Metric | Cosine similarity |
| Storage | Qdrant vector database |

---

## API Interface

### Request

```json
POST /api/recommend
{
  "user_id": "user_123",
  "engagements": [
    {"episode_id": "ep_001", "action": "bookmark"},
    {"episode_id": "ep_002", "action": "click"}
  ],
  "excluded_ids": ["ep_003"],
  "limit": 10
}
```

### Response

```json
{
  "recommendations": [
    {
      "id": "ep_456",
      "title": "The Future of AI Infrastructure",
      "final_score": 0.923,
      "similarity_score": 0.891,
      "quality_score": 0.95,
      "recency_score": 0.87
    }
  ],
  "cold_start": false,
  "algorithm_version": "1.5"
}
```

---

## Related Documents

- [02_VERSION_CHANGELOG.md](./02_VERSION_CHANGELOG.md) - How architecture evolved
- [03_PARAMETER_REFERENCE.md](./03_PARAMETER_REFERENCE.md) - All configurable parameters
