# Deep Dive 04: Scoring Components Subsystem

> *Four independent scoring signals that measure relevance, quality, alignment, and freshness.*

**Document:** 4 of 8  
**Subsystem:** Scoring Components (S_sim, S_alpha, S_entity, S_fresh)  
**Pipeline Stage:** Stage 2 (Scoring)  
**Status:** Final

---

## 1. Purpose

This subsystem computes **four independent scoring components** for each episode that passes the quality gates. These components are combined in Document 05 to produce the final BaseScore.

Each component captures a distinct dimension of episode value:

| Component | Symbol | Measures |
|-----------|--------|----------|
| Semantic Similarity | S_sim | How well the episode matches user interests |
| Signal Quality | S_alpha | Intrinsic quality (credibility + insight) |
| Freshness | S_fresh | Recency of publication |

> **Note:** Entity Alignment (S_entity) is documented in Document 08 as a future enhancement. It requires an explicit "Follow Company/Person" feature that does not currently exist in the product.

---

## 2. Subsystem Context

```
┌─────────────────────────────────────────────────────────────────┐
│              SCORING COMPONENTS SUBSYSTEM                        │
│                    (This Document)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUTS                                                         │
│  ──────                                                         │
│  • V_activity (from Document 02)                                │
│  • E.embedding (from Document 01)                               │
│  • E.scores.insight, E.scores.credibility (from Document 01)    │
│  • E.published_at (from Document 01)                            │
│                                                                  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                          │
│  │  S_sim  │  │ S_alpha │  │ S_fresh │                          │
│  │ (50%)   │  │  (35%)  │  │  (15%)  │                          │
│  └────┬────┘  └────┬────┘  └────┬────┘                          │
│       │            │            │                               │
│       └────────────┴────────────┘                               │
│                         │                                        │
│                         ▼                                        │
│                                                                  │
│  OUTPUTS                                                        │
│  ───────                                                        │
│  • S_sim ∈ [0, 1]                                               │
│  • S_alpha ∈ [0.25, 1.0]                                        │
│  • S_fresh ∈ [0.10, 1.0]                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Document 05:       │
                    │  Base Score         │
                    │  Aggregation        │
                    └─────────────────────┘
```

---

## 3. Component 1: Semantic Similarity (S_sim)

### 3.1 Purpose

S_sim measures how well an episode's content aligns with the user's demonstrated research interests. This is the **primary personalization signal**.

### 3.2 Formula

```
IF V_activity is not null:
    S_sim = CosineSim(V_activity, E.embedding)
ELSE:
    S_sim = 0.5  // Neutral default for cold start
```

### 3.3 Input Parameters

| Parameter | Source | Type | Description |
|-----------|--------|------|-------------|
| `V_activity` | Document 02 | Vector[1536] \| null | User's research interest embedding |
| `E.embedding` | Document 01 | Vector[1536] | Episode's content embedding |

### 3.4 Output

| Property | Value |
|----------|-------|
| Range | [0, 1] (cosine similarity normalized) |
| Cold start default | 0.5 |
| Tunable? | 🔒 Fixed (weight W_sim is tunable) |

### 3.5 Cosine Similarity Explanation

```python
import numpy as np

def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.
    
    Returns:
        Float in range [-1, 1], but embedding spaces typically
        produce values in [0, 1] for similar content.
    """
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    
    return dot_product / (norm_v1 * norm_v2)
```

### 3.6 Interpretation

| S_sim Value | Interpretation |
|-------------|----------------|
| 0.90–1.00 | Highly aligned — very similar to user's interests |
| 0.75–0.90 | Strong match — clearly relevant |
| 0.60–0.75 | Moderate match — somewhat related |
| 0.40–0.60 | Weak match — tangentially related |
| 0.00–0.40 | Poor match — likely not relevant |

### 3.7 Cold Start Behavior

When `V_activity` is null (pure cold start with no interests):
- S_sim = 0.5 for all episodes
- All episodes are treated equally on this dimension
- Ranking relies on S_alpha (quality) as the differentiator

---

## 4. Component 2: Signal Quality (S_alpha)

### 4.1 Purpose

S_alpha measures the **intrinsic quality** of the episode — how credible the speaker is and how insightful the content is. This is Serafis's key differentiator: surfacing "alpha" (valuable signal) rather than just popular content.

### 4.2 Formula

```
S_alpha = (W_insight × E.scores.insight + W_cred × E.scores.credibility) / 4.0
```

### 4.3 Input Parameters

| Parameter | Source | Type | Range | Description |
|-----------|--------|------|-------|-------------|
| `E.scores.insight` | Document 01 | Integer | 1–4 | Novelty and depth of ideas |
| `E.scores.credibility` | Document 01 | Integer | 1–4 | Speaker authority and track record |

### 4.4 Weighting Parameters

| Parameter | Symbol | Default | Tunable? | Range | Rationale |
|-----------|--------|---------|----------|-------|-----------|
| Insight weight | W_insight | 0.5 | ⚙️ Yes | 0.4–0.6 | Balanced V1; may favor insight later |
| Credibility weight | W_cred | 0.5 | ⚙️ Yes | 0.4–0.6 | Balanced V1; may favor credibility later |
| Normalizer | — | 4.0 | 🔒 Fixed | — | Max possible score |

**Constraint:** W_insight + W_cred = 1.0

### 4.5 Output

| Property | Value |
|----------|-------|
| Range | [0.25, 1.0] |
| Minimum (after gates) | 0.3125 (C=2, I=3 at gate boundary) |
| Tunable? | Via W_insight, W_cred |

**Why [0.25, 1.0]?**

After passing quality gates (C ≥ 2, C + I ≥ 5), the minimum possible scores are:
- Worst case passing: C=2, I=3 → (0.5×3 + 0.5×2)/4 = 0.625
- Theoretical minimum: C=1, I=1 → (0.5×1 + 0.5×1)/4 = 0.25 (but rejected by gates)

### 4.6 Score Interpretation

| S_alpha Value | Interpretation | Typical Episode |
|---------------|----------------|-----------------|
| 0.875–1.000 | Exceptional | C=4, I=4 — Top-tier expert, groundbreaking insight |
| 0.750–0.875 | Strong | C=4, I=3 or C=3, I=4 — Great episode |
| 0.625–0.750 | Good | C=3, I=3 — Solid content |
| 0.500–0.625 | Adequate | C=2, I=3 — Meets quality bar |
| <0.500 | Weak | Would likely fail Gate 2 |

### 4.7 Worked Example

**Episode Scores:** insight=4, credibility=3

```
S_alpha = (0.5 × 4 + 0.5 × 3) / 4.0
        = (2.0 + 1.5) / 4.0
        = 3.5 / 4.0
        = 0.875
```

---

## 5. Component 3: Freshness (S_fresh)

### 6.1 Purpose

S_fresh measures how recently an episode was published. This ensures the feed stays **current** while still allowing discovery of timeless content.

### 6.2 Formula

```
S_fresh = max(FLOOR, exp(-λ_fresh × E.DaysOld))
```

### 6.3 Input Parameters

| Parameter | Source | Type | Description |
|-----------|--------|------|-------------|
| `E.DaysOld` | Derived (Doc 01) | Integer | Days since publication |

### 6.4 Tunable Parameters

| Parameter | Symbol | Default | Tunable? | Range | Rationale |
|-----------|--------|---------|----------|-------|-----------|
| Decay rate | λ_fresh | 0.03 | ⚙️ Yes | 0.02–0.05 | Controls freshness half-life |
| Floor value | FLOOR | 0.10 | ⚙️ Yes | 0.05–0.20 | Minimum score for old content |

### 6.5 Output

| Property | Value |
|----------|-------|
| Range | [FLOOR, 1.0] = [0.10, 1.0] |
| At publication (Day 0) | 1.0 |
| At half-life (~23 days) | 0.5 |
| Evergreen content | 0.10 (floor) |

### 6.6 Decay Curve

With λ_fresh = 0.03:

| Days Old | S_fresh | Interpretation |
|----------|---------|----------------|
| 0 | 1.00 | Just published |
| 7 | 0.81 | One week old |
| 14 | 0.66 | Two weeks old |
| 23 | 0.50 | Half-life point |
| 30 | 0.41 | One month old |
| 60 | 0.17 | Two months old |
| 90+ | 0.10 | Floor (evergreen) |

### 6.7 Why Exponential Decay with Floor?

**Exponential Decay:**
- Smooth degradation (no cliff effects)
- Recent content strongly favored
- Mathematically elegant

**Floor Value:**
- Prevents excellent old content from being permanently buried
- A classic interview from 6 months ago still contributes 10%
- Enables "timeless" content discovery

### 6.8 Implementation

```python
import math

def compute_s_fresh(days_old: int, 
                    lambda_fresh: float = 0.03, 
                    floor: float = 0.10) -> float:
    """
    Compute freshness score with exponential decay and floor.
    
    Args:
        days_old: Days since episode publication
        lambda_fresh: Decay rate (higher = faster decay)
        floor: Minimum score for old content
    
    Returns:
        Float in [floor, 1.0]
    """
    raw_score = math.exp(-lambda_fresh * days_old)
    return max(floor, raw_score)
```

### 6.9 Decay Rate Comparison

| λ_fresh | Half-Life | Use Case |
|---------|-----------|----------|
| 0.02 | ~35 days | Slower decay; more evergreen focus |
| 0.03 | ~23 days | Balanced (default) |
| 0.05 | ~14 days | Faster decay; more news focus |
| 0.10 | ~7 days | Very aggressive; breaking news only |

---

## 6. Component Summary

| Component | Symbol | Formula | Range | Weight (Default) |
|-----------|--------|---------|-------|------------------|
| Semantic Similarity | S_sim | CosineSim(V_activity, E.embedding) | [0, 1] | 50% |
| Signal Quality | S_alpha | (W_i × I + W_c × C) / 4.0 | [0.25, 1.0] | 35% |
| Freshness | S_fresh | max(FLOOR, exp(-λ × days)) | [0.10, 1.0] | 15% |

---

## 7. All Parameters

### 7.1 Fixed Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| View weight (in V_activity) | 1.0 | Baseline reference |
| S_alpha normalizer | 4.0 | Max possible score |

### 7.2 Tunable Parameters

| Parameter | Symbol | Default | Range | Priority |
|-----------|--------|---------|-------|----------|
| W_insight | — | 0.5 | 0.4–0.6 | Medium |
| W_cred | — | 0.5 | 0.4–0.6 | Medium |
| λ_fresh | — | 0.03 | 0.02–0.05 | Medium |
| FLOOR | — | 0.10 | 0.05–0.20 | Low |

---

## 8. Edge Cases

### 8.1 S_sim Edge Cases

| Scenario | Behavior |
|----------|----------|
| V_activity = null | S_sim = 0.5 (neutral) |
| E.embedding = zero vector | S_sim = 0 (data quality issue) |
| Identical vectors | S_sim = 1.0 |

### 8.2 S_alpha Edge Cases

| Scenario | Behavior |
|----------|----------|
| C=4, I=4 | S_alpha = 1.0 (maximum) |
| C=2, I=3 (gate boundary) | S_alpha = 0.625 |
| C=1, I=1 | Would be rejected by gates |

### 8.3 S_fresh Edge Cases

| Scenario | Behavior |
|----------|----------|
| Published today | S_fresh = 1.0 |
| Published 1 year ago | S_fresh = 0.10 (floor) |
| Future publish date | S_fresh > 1.0 (clamp to 1.0 if needed) |

---

## 9. Traceability

### 9.1 Design Decisions

| Component | Decision | Rationale | Backing |
|-----------|----------|-----------|---------|
| S_sim | Cosine similarity | Industry standard for embedding comparison | Spotify Semantic IDs paper |
| S_alpha | Weighted credibility + insight | Serafis differentiator; quality over popularity | Artifact app, LinkedIn Author Authority |
| S_fresh | Exponential decay with floor | Smooth, tunable, preserves evergreen | Common recommender pattern |

### 9.2 Why These Three Components?

| User Need | Component | How It Addresses |
|-----------|-----------|------------------|
| "Show me relevant content" | S_sim | Matches to user interests |
| "Show me quality content" | S_alpha | Filters for credibility + insight |
| "Show me fresh content" | S_fresh | Prioritizes recent publications |

### 9.3 What's Not Included (V2 Considerations)

| Potential Component | Why Deferred |
|--------------------|--------------|
| S_entity | Requires explicit entity tracking feature (see Document 08) |
| S_popularity | Serafis differentiates on quality, not popularity |
| S_series | Could boost preferred series; adds complexity |
| S_duration | Episode length preference; requires more user data |
| S_information | Already have insight + credibility; may add at 10-15% |

---

## 10. Dependencies

### 10.1 Upstream (Required)

| Dependency | Source | Used By |
|------------|--------|---------|
| V_activity | Document 02 | S_sim |
| E.embedding | Document 01 | S_sim |
| E.scores.* | Document 01 | S_alpha |
| E.published_at | Document 01 | S_fresh |

### 10.2 Downstream (Consumers)

| Consumer | Usage |
|----------|-------|
| Document 05: Base Score | Combines all three components |

---

## 11. Document References

| Related Document | Relationship |
|------------------|--------------|
| 01: Data Model | Provides all episode and user data |
| 02: User Embedding | Provides V_activity |
| 05: Base Score Aggregation | Combines S_* into BaseScore |
| 08: Future Enhancements | S_entity specification (requires entity tracking feature) |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Feb 2026 | Initial deep dive document |
