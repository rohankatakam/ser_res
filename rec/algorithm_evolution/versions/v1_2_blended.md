# v1.2 Blended Scoring

**Created:** 2026-02-05  
**Folder:** `algorithms/v1_2_blended/`  
**Status:** Production baseline

---

## Purpose

v1.2 is the first production-ready algorithm with:
- Proper configuration loading via `config.json`
- Server-side auto-exclusion of engaged episodes
- Full test suite validation

---

## Configuration

```json
{
  "stage_a": {
    "credibility_floor": 2,
    "combined_floor": 5,
    "freshness_window_days": 90,
    "candidate_pool_size": 150
  },
  "stage_b": {
    "user_vector_limit": 10,
    "weight_similarity": 0.55,
    "weight_quality": 0.30,
    "weight_recency": 0.15,
    "credibility_multiplier": 1.5,
    "recency_lambda": 0.03,
    "use_weighted_engagements": true,
    "use_sum_similarities": false
  },
  "engagement_weights": {
    "bookmark": 2.0,
    "listen": 1.5,
    "click": 1.0
  }
}
```

---

## Architecture

### Stage A: Candidate Pre-selection
1. Filter by `credibility >= 2`
2. Filter by `credibility + insight >= 5`
3. Filter by `published_at` within 90 days
4. Exclude engaged/dismissed episodes
5. Sort by quality score, take top 150

### Stage B: Semantic Ranking
1. Compute user vector from top 10 engagements (weighted by type)
2. For each candidate: compute similarity, quality, recency scores
3. Blend: `0.55×similarity + 0.30×quality + 0.15×recency`
4. Sort by final score, return top N

---

## Key Functions

```python
# recommendation_engine.py

get_candidate_pool(excluded_ids, episodes, config)
    # Stage A filtering and quality sorting

get_user_vector_mean(engagements, embeddings, episode_by_content_id, config)
    # Weighted mean-pooling of engagement embeddings

rank_candidates(engagements, candidates, embeddings, episode_by_content_id, config)
    # Stage B blended scoring

create_recommendation_queue(engagements, excluded_ids, episodes, embeddings, ...)
    # Main entry point, orchestrates pipeline
```

---

## Bug Fixes Applied (2026-02-08)

### 1. Config Loading Fix

**Problem:** `server.py` was not passing `config.json` to the recommendation engine.

**Fix in `server.py`:**
```python
# Load algorithm-specific config
algo_config = None
if state.current_algorithm.config and hasattr(engine, 'RecommendationConfig'):
    algo_config = engine.RecommendationConfig.from_dict(state.current_algorithm.config)

queue, cold_start, user_vector_episodes = engine.create_recommendation_queue(
    ...,
    config=algo_config,  # Now properly passed
)
```

**Fix in `recommendation_engine.py`:**
```python
def create_recommendation_queue(..., config: RecommendationConfig = None):
    if config is None:
        config = DEFAULT_CONFIG  # Graceful fallback
```

### 2. Auto-Exclusion Fix

**Problem:** Engaged episodes appeared in new recommendations.

**Fix in `server.py`:**
```python
excluded_ids = set(request.excluded_ids)
# Auto-exclude engaged episodes
for eng in request.engagements:
    excluded_ids.add(eng.episode_id)
```

---

## Test Performance

| Test | Status | Score |
|------|--------|-------|
| 01 Cold Start | ✅ | 9.50 |
| 02 Personalization | ✅ | 8.61 |
| 03 Quality Gates | ✅ | 10.00 |
| 04 Exclusions | ✅ | 10.00 |
| 05 Category | ✅ | 8.75 |
| 06 Bookmark | ❌ | 4.39 |
| 07 Recency | ✅ | 7.56 |
| 08 Bookmark HQ | ❌ | 4.08 |
| **Overall** | **6/8** | **8.29** |

---

## Improvement from v1.0

- **Tests passing:** 4/8 → 6/8 (+50%)
- **Overall score:** 7.65 → 8.29 (+8.4%)
- **Key unlocks:** Tests 02 and 05 started passing due to bug fixes

---

## Files

- `manifest.json` - Algorithm metadata
- `config.json` - Runtime configuration
- `recommendation_engine.py` - Core algorithm
- `embedding_strategy.py` - Embedding text generation
