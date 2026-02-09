# Original Specification → v1.0 Implementation

This document traces the translation from the original brief text to the v1.0 implementation, providing full traceability for the algorithm's design decisions.

---

## Original Brief (January 2026)

**Source:** Text message from Rohan Sharma, Founder

```
Recommendation algorithm:

- determine user-specific ranking score for an episode candidate
- for the top 10 (or whatever n) episodes in the user's activity:
  - calculate vector similarity with candidate + user episode (activity)
  - add up scores across top 10 -> overall similarity of candidate to user's interests

Recommendation params:
  - similarity to user's interests (semantic match between episode titles + descriptions)
     - for user activity, don't care as much about the publish date (focus on interaction date)
  - (v2) overlap between candidate episode categories and user aggregate category activity
  - Serafis quality score (weight credibility higher, combine with insight)
  - recency of the candidate content
 
What are the top 10 for user's activity?
  - order by recency of activity (simple to start)
  - later on, order by depth of engagement (did they listen to the full thing? bookmark? etc)
```

---

## Translation Breakdown

### 1. "For the top 10 episodes in user's activity"

**Brief:** Use top 10 episodes from user activity, ordered by recency.

**Implementation:**

```python
# recommendation_engine.py
class RecommendationConfig:
    user_vector_limit: int = 10  # Top 10 engagements
```

```python
def get_user_vector_mean(...):
    # Sort by timestamp, most recent first
    sorted_eng = sorted(
        engagements,
        key=lambda e: e.get("timestamp", ""),
        reverse=True
    )[:config.user_vector_limit]  # Limit to 10
```

**Status:** ✅ Implemented exactly as specified.

---

### 2. "Calculate vector similarity... add up scores"

**Brief:** For each candidate, calculate similarity with each activity episode, then sum.

**Implementation (v1.0-v1.2):**

Initially implemented as **mean-pooling** (average) rather than sum:

```python
def get_user_vector_mean(...):
    # Weighted average of engagement embeddings
    user_vector = np.average(vectors, weights=weights, axis=0)
    return user_vector.tolist()
```

Then similarity is computed once against the pooled vector:

```python
similarity = cosine_similarity(user_vector, candidate_embedding)
```

**v1.3 Addition:** Added `use_sum_similarities` option to match original spec more closely:

```python
def compute_similarity_sum(...):
    # Compare candidate to EACH engagement, sum weighted similarities
    for eng in sorted_eng:
        embedding = embeddings.get(eng.episode_id)
        sim = cosine_similarity(candidate_embedding, embedding)
        weight = engagement_weights.get(eng.type, 1.0)
        total_sim += sim * weight
        total_weight += weight
    return total_sim / total_weight  # Weighted average of pairwise similarities
```

**Status:** 
- v1.0-v1.2: Mean-pooling approach (simpler, faster)
- v1.3: Added sum-of-similarities option via `use_sum_similarities: true`

---

### 3. "Similarity to user's interests (semantic match)"

**Brief:** Semantic matching between episode content.

**Implementation:**

```python
# embedding_strategy.py
def get_embed_text(episode: Dict) -> str:
    """Generate text for embedding from episode data."""
    parts = []
    parts.append(episode.get("title", ""))
    if episode.get("key_insight"):
        parts.append(episode["key_insight"])
    # ... series, entities, people
    return " | ".join(filter(None, parts))
```

Uses OpenAI `text-embedding-3-small` (1536 dimensions).

**Status:** ✅ Implemented. Embeddings capture title + key_insight + context.

---

### 4. "For user activity, focus on interaction date"

**Brief:** Engagement recency matters more than episode publish date.

**Implementation:**

Engagements are sorted by `timestamp` (interaction date), not `published_at`:

```python
sorted_eng = sorted(
    engagements,
    key=lambda e: e.get("timestamp", ""),  # Interaction timestamp
    reverse=True
)[:config.user_vector_limit]
```

**Status:** ✅ Implemented exactly as specified.

---

### 5. "(v2) Category overlap"

**Brief:** Overlap between candidate categories and user category interests—deferred to v2.

**Implementation:** Not implemented in v1.0-v1.3.

**Rationale:** Embeddings capture semantic similarity which implicitly includes category relationships. Explicit category matching was deemed lower priority.

**Status:** ⏸️ Deferred. Could be added as a boost factor in future versions.

---

### 6. "Serafis quality score (weight credibility higher)"

**Brief:** Quality score combining credibility and insight, with credibility weighted higher.

**Implementation:**

```python
class RecommendationConfig:
    credibility_multiplier: float = 1.5  # Weight credibility higher

def compute_quality_score(episode, config):
    credibility = scores.get("credibility", 0)
    insight = scores.get("insight", 0)
    # Quality = (credibility * 1.5 + insight) / 10
    quality_score = (credibility * config.credibility_multiplier + insight) / config.max_quality_score
    return quality_score
```

Example: Episode with C:4, I:3 → (4*1.5 + 3) / 10 = 0.9

**Status:** ✅ Implemented with configurable multiplier.

---

### 7. "Recency of candidate content"

**Brief:** Factor in how recent the candidate episode is.

**Implementation:**

```python
class RecommendationConfig:
    recency_lambda: float = 0.03  # ~23 day half-life

def compute_recency_score(episode, config):
    days_old = days_since(episode.get("published_at", ""))
    recency_score = math.exp(-config.recency_lambda * days_old)
    return recency_score
```

Exponential decay: ~50% score at 23 days, ~25% at 46 days.

**Status:** ✅ Implemented with configurable decay rate.

---

### 8. "Depth of engagement (bookmark, listen, etc.)"

**Brief:** Later, order by depth of engagement—bookmarks and listens are stronger signals.

**Implementation:**

```python
class RecommendationConfig:
    engagement_weights: Dict[str, float] = None  # Defaults below
    
# Default weights
DEFAULT_ENGAGEMENT_WEIGHTS = {
    "bookmark": 2.0,  # Bookmarks are 2x stronger
    "listen": 1.5,    # Listens are 1.5x
    "click": 1.0      # Clicks are baseline
}
```

Applied when computing user vector:

```python
for eng in sorted_eng:
    eng_type = eng.get("type", "click")
    weight = config.engagement_weights.get(eng_type, 1.0)
    weights.append(weight)
```

**v1.3 Tuning:** Increased `bookmark` weight to 5.0 for stronger differentiation.

**Status:** ✅ Implemented. Configurable weights per engagement type.

---

## Blended Scoring Formula

The final implementation combines all factors:

```
final_score = (weight_similarity × similarity_score) 
            + (weight_quality × quality_score) 
            + (weight_recency × recency_score)
```

| Version | Similarity | Quality | Recency |
|---------|------------|---------|---------|
| v1.0/v1.2 | 0.55 | 0.30 | 0.15 |
| v1.3 | 0.85 | 0.10 | 0.05 |

---

## Additions Beyond Original Spec

### Quality Gates (Stage A Pre-filtering)

Not in original brief, but added for quality assurance:

```python
# Credibility floor: C >= 2
if credibility < config.credibility_floor:
    continue

# Combined floor: C + I >= 5
if credibility + insight < config.combined_floor:
    continue
```

**Rationale:** Ensures minimum content quality regardless of similarity.

### Exclusion Logic

Implicit in the brief ("what are the top 10") but made explicit:

```python
excluded_ids = set(request.excluded_ids)
# Also exclude engaged episodes from new recommendations
for eng in request.engagements:
    excluded_ids.add(eng.episode_id)
```

### Cold Start Handling

Not in original brief, added for edge case:

```python
cold_start = not engagements
if cold_start:
    # Use quality + recency only (no similarity)
    final_score = (config.cold_start_weight_quality * quality_score +
                   config.cold_start_weight_recency * recency_score)
```

---

## Summary: Spec Compliance

| Original Requirement | Implementation Status |
|---------------------|----------------------|
| Top 10 user activity | ✅ `user_vector_limit: 10` |
| Sum similarity scores | ⚠️ Mean-pooling default; v1.3 adds sum option |
| Semantic matching | ✅ OpenAI embeddings |
| Interaction date focus | ✅ Sorted by timestamp |
| Category overlap (v2) | ⏸️ Deferred |
| Quality score (credibility higher) | ✅ `credibility_multiplier: 1.5` |
| Recency of candidate | ✅ Exponential decay |
| Depth of engagement | ✅ `engagement_weights` |

**Overall:** v1.0 implements the core specification with minor variations (mean-pooling vs sum). v1.3 adds the sum-of-similarities option to more closely match the original "add up scores" language.
