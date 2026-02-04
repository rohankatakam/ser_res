# Deep Dive 05: Base Score Aggregation

> *Combines scoring components into a single normalized score for candidate ranking.*

**Document:** 5 of 8  
**Subsystem:** Base Score Aggregation  
**Pipeline Stage:** Stage 2 (Final Scoring)  
**Status:** Final

---

## 1. Purpose

This subsystem takes the three scoring components (S_sim, S_alpha, S_fresh) and combines them into a single **BaseScore** using a weighted linear combination. The BaseScore determines the initial ranking of episodes before diversity reranking.

---

## 2. Subsystem Context

```
┌─────────────────────────────────────────────────────────────────┐
│              BASE SCORE AGGREGATION                              │
│                   (This Document)                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUTS (from Document 04)                                      │
│  ─────────────────────────                                      │
│  • S_sim ∈ [0, 1]                                               │
│  • S_alpha ∈ [0.25, 1.0]                                        │
│  • S_fresh ∈ [0.10, 1.0]                                        │
│                                                                  │
│                         │                                        │
│                         ▼                                        │
│              ┌─────────────────────┐                            │
│              │  WEIGHTED SUM       │                            │
│              │  BaseScore =        │                            │
│              │  Σ(W_i × S_i)       │                            │
│              └─────────────────────┘                            │
│                         │                                        │
│                         ▼                                        │
│                                                                  │
│  OUTPUT                                                         │
│  ──────                                                         │
│  • BaseScore ∈ [0, 1]                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Top 50 by          │
                    │  BaseScore          │
                    └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Document 07:       │
                    │  Narrative          │
                    │  Reranking          │
                    └─────────────────────┘
```

---

## 3. Input Parameters

| Parameter | Source | Type | Range | Description |
|-----------|--------|------|-------|-------------|
| `S_sim` | Document 04 | Float | [0, 1] | Semantic similarity to user interests |
| `S_alpha` | Document 04 | Float | [0.25, 1.0] | Signal quality (credibility + insight) |
| `S_fresh` | Document 04 | Float | [0.10, 1.0] | Freshness score |

---

## 4. Output Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `BaseScore` | Float | [0, 1] | Combined episode score for ranking |

---

## 5. Formula

### 5.1 Core Equation

```
BaseScore = (S_sim × W_sim) + (S_alpha × W_alpha) + (S_fresh × W_fresh)
```

### 5.2 Weight Configuration

| Weight | Symbol | Default | Tunable? | Range | Rationale |
|--------|--------|---------|----------|-------|-----------|
| Similarity | W_sim | **0.50** | ⚙️ Yes | 0.40–0.60 | Primary personalization signal |
| Signal Quality | W_alpha | **0.35** | ⚙️ Yes | 0.25–0.45 | Serafis differentiation — quality matters |
| Freshness | W_fresh | **0.15** | ⚙️ Yes | 0.10–0.20 | Feed currency |

**Constraint:** W_sim + W_alpha + W_fresh = 1.0

> **Tuning Note:** The 50/35/15 distribution is a starting point based on product priorities. These weights should be tuned during testing based on user feedback and engagement metrics. Adjust toward higher W_sim if feed feels generic, or higher W_alpha if quality feels inconsistent.

### 5.3 Why These Weights?

| Weight | Value | Reasoning |
|--------|-------|-----------|
| W_sim = 50% | Personalization is the primary value of a "For You" feed. Without relevance to user interests, the feed is just a quality-sorted list. |
| W_alpha = 35% | Serafis's core differentiator is surfacing high-quality, credible content — not just popular content. This deserves significant weight. |
| W_fresh = 15% | Freshness matters for a news-adjacent product, but timeless content should still surface. 15% provides currency without burying evergreen content. |

---

## 6. Range Guarantee

**Claim:** BaseScore ∈ [0, 1] for all valid inputs.

**Intuitive Proof:**

1. Each component S_i ∈ [0, 1] (or subrange thereof)
2. Each weight W_i ∈ [0, 1]
3. Weights sum to 1.0
4. Therefore: BaseScore = Σ(W_i × S_i) is a convex combination
5. Convex combinations of values in [0, 1] produce values in [0, 1]

**Practical Range:**

Given component ranges after quality gates:
- S_sim: [0, 1] (full range, 0.5 for cold start)
- S_alpha: [0.25, 1.0] (minimum after gates)
- S_fresh: [0.10, 1.0] (floor enforced)

| Scenario | S_sim | S_alpha | S_fresh | BaseScore |
|----------|-------|---------|---------|-----------|
| Worst case (cold start, gate boundary, old) | 0.5 | 0.625 | 0.10 | **0.484** |
| Best case (perfect match, perfect quality, new) | 1.0 | 1.0 | 1.0 | **1.000** |
| Typical good episode | 0.75 | 0.80 | 0.70 | **0.760** |

---

## 7. Algorithm Implementation

```python
def compute_base_score(
    s_sim: float,
    s_alpha: float,
    s_fresh: float,
    w_sim: float = 0.50,
    w_alpha: float = 0.35,
    w_fresh: float = 0.15
) -> float:
    """
    Compute the base score from component scores.
    
    Args:
        s_sim: Semantic similarity score [0, 1]
        s_alpha: Signal quality score [0.25, 1.0]
        s_fresh: Freshness score [0.10, 1.0]
        w_sim: Weight for similarity (default 0.50)
        w_alpha: Weight for quality (default 0.35)
        w_fresh: Weight for freshness (default 0.15)
    
    Returns:
        BaseScore in [0, 1]
    """
    # Validate weight constraint
    assert abs(w_sim + w_alpha + w_fresh - 1.0) < 0.001, "Weights must sum to 1.0"
    
    base_score = (s_sim * w_sim) + (s_alpha * w_alpha) + (s_fresh * w_fresh)
    
    return base_score
```

---

## 8. Candidate Selection

After computing BaseScore for all episodes that pass quality gates, select the **top 50** for reranking.

```python
def select_candidates(
    episodes: list[Episode],
    user: User,
    n_candidates: int = 50
) -> list[Episode]:
    """
    Select top N candidates by BaseScore for reranking.
    
    Args:
        episodes: All episodes in catalog
        user: Current user
        n_candidates: Number of candidates to select (default 50)
    
    Returns:
        Top N episodes sorted by BaseScore descending
    """
    # Filter by quality gates
    passed_episodes = [
        ep for ep in episodes 
        if evaluate_gates(ep, user).result == GateResult.PASS
    ]
    
    # Compute scores
    scored_episodes = []
    for ep in passed_episodes:
        s_sim = compute_s_sim(user.v_activity, ep.embedding)
        s_alpha = compute_s_alpha(ep.scores)
        s_fresh = compute_s_fresh(ep.days_old)
        base_score = compute_base_score(s_sim, s_alpha, s_fresh)
        
        scored_episodes.append({
            'episode': ep,
            'base_score': base_score,
            'components': {
                's_sim': s_sim,
                's_alpha': s_alpha,
                's_fresh': s_fresh
            }
        })
    
    # Sort and select top N
    scored_episodes.sort(key=lambda x: x['base_score'], reverse=True)
    
    return scored_episodes[:n_candidates]
```

| Parameter | Value | Tunable? | Rationale |
|-----------|-------|----------|-----------|
| n_candidates | 50 | ⚙️ Yes | Provides enough diversity for reranking while limiting computation. *Tune during testing — increase if reranking lacks variety, decrease if performance is a concern.* |

---

## 9. Worked Example

### 9.1 Episode Data

**User:**
- Has viewed 5 AI-focused episodes (V_activity computed)
- Cold start = False

**Episode:**
```json
{
  "id": "B7d9XwUOKOuoH7R8Tnzi",
  "title": "Gokul Rajaram - Lessons from Investing in 700 Companies",
  "scores": {
    "insight": 3,
    "credibility": 4
  },
  "published_at": "2026-01-29T09:00:00+00:00"  // 5 days ago
}
```

### 9.2 Component Calculations

| Component | Calculation | Value |
|-----------|-------------|-------|
| S_sim | CosineSim(V_activity, E.embedding) | 0.82 |
| S_alpha | (0.5 × 3 + 0.5 × 4) / 4.0 = 3.5/4.0 | 0.875 |
| S_fresh | max(0.10, exp(-0.03 × 5)) = exp(-0.15) | 0.86 |

### 9.3 Base Score Calculation

```
BaseScore = (0.82 × 0.50) + (0.875 × 0.35) + (0.86 × 0.15)
          = 0.410 + 0.306 + 0.129
          = 0.845
```

### 9.4 Component Contribution Analysis

| Component | Value | Weight | Contribution | % of Total |
|-----------|-------|--------|--------------|------------|
| S_sim | 0.82 | 0.50 | 0.410 | 48.5% |
| S_alpha | 0.875 | 0.35 | 0.306 | 36.2% |
| S_fresh | 0.86 | 0.15 | 0.129 | 15.3% |
| **Total** | — | 1.00 | **0.845** | 100% |

**Interpretation:** This is a high-quality, relevant, fresh episode. It would likely rank in the top 10 before reranking.

---

## 10. Score Interpretation

| BaseScore Range | Interpretation | Likely Position |
|-----------------|----------------|-----------------|
| 0.85–1.00 | Excellent match | Top 5 |
| 0.70–0.85 | Strong match | Top 20 |
| 0.55–0.70 | Moderate match | Top 50 |
| 0.40–0.55 | Weak match | May not make candidate pool |
| <0.40 | Poor match | Unlikely to be recommended |

---

## 11. Edge Cases

### 11.1 Cold Start User

| Scenario | S_sim | Effect on BaseScore |
|----------|-------|---------------------|
| No activity, no interests | 0.5 | Neutral; quality and freshness dominate |
| Has category interests | Computed | Normal personalization |

**Cold Start BaseScore Range:**
```
Min: (0.5 × 0.50) + (0.625 × 0.35) + (0.10 × 0.15) = 0.484
Max: (0.5 × 0.50) + (1.0 × 0.35) + (1.0 × 0.15)   = 0.750
```

For cold start users, the feed is essentially a quality-weighted, freshness-adjusted list.

### 11.2 Perfect Episode

| Component | Value | Contribution |
|-----------|-------|--------------|
| S_sim | 1.0 | 0.50 |
| S_alpha | 1.0 | 0.35 |
| S_fresh | 1.0 | 0.15 |
| **BaseScore** | — | **1.00** |

### 11.3 Gate Boundary Episode

Minimum quality after passing gates: C=2, I=3 (or C=3, I=2)

| Component | Value | Contribution |
|-----------|-------|--------------|
| S_sim | 0.5 (cold start) | 0.25 |
| S_alpha | 0.625 | 0.219 |
| S_fresh | 0.10 (old) | 0.015 |
| **BaseScore** | — | **0.484** |

---

## 12. Tuning Guidance

### 12.1 When to Adjust Weights

| Symptom | Likely Cause | Adjustment |
|---------|--------------|------------|
| Feed feels generic | W_sim too low | Increase W_sim (e.g., 0.55) |
| Feed is echo chamber | W_sim too high | Decrease W_sim (e.g., 0.45) |
| Low-quality content surfacing | W_alpha too low | Increase W_alpha (e.g., 0.40) |
| Feed feels stale | W_fresh too low | Increase W_fresh (e.g., 0.20) |
| Old quality content buried | W_fresh too high | Decrease W_fresh (e.g., 0.10) |

### 12.2 Tuning Priority

| Parameter | Priority | Impact |
|-----------|----------|--------|
| W_sim | **High** | Personalization strength |
| W_alpha | **High** | Quality vs relevance balance |
| W_fresh | Medium | Currency vs evergreen balance |
| n_candidates | Low | Reranking pool size |

---

## 13. Logging & Debugging

For every episode scored, log:

```json
{
  "episode_id": "B7d9XwUOKOuoH7R8Tnzi",
  "base_score": 0.845,
  "components": {
    "s_sim": 0.82,
    "s_alpha": 0.875,
    "s_fresh": 0.86
  },
  "weights": {
    "w_sim": 0.50,
    "w_alpha": 0.35,
    "w_fresh": 0.15
  },
  "contributions": {
    "sim_contribution": 0.410,
    "alpha_contribution": 0.306,
    "fresh_contribution": 0.129
  },
  "rank_before_reranking": 3,
  "passed_to_reranking": true
}
```

This enables:
- "Why did I see this?" debugging
- Component contribution visualization (radar charts)
- Weight tuning analysis

---

## 14. Traceability

### 14.1 Design Decisions

| Decision | Rationale | Backing |
|----------|-----------|---------|
| Linear weighted sum | Simple, interpretable, tunable | Industry standard |
| 50/35/15 weight split | Balances personalization, quality, freshness | Derived from product priorities |
| Top 50 candidates | Enough for diversity; limits compute | Practical engineering choice |
| Normalize to [0,1] | Consistent range for downstream processing | Mathematical convenience |

### 14.2 Why Linear Combination?

| Alternative | Why Not Used |
|-------------|--------------|
| Multiplicative combination | One zero component kills the score |
| Neural network | Overkill for 3 inputs; not interpretable |
| Max/Min selection | Ignores component contributions |
| Learned weights | Requires training data; deferred to V2 |

---

## 15. Dependencies

### 15.1 Upstream (Required)

| Dependency | Source | Description |
|------------|--------|-------------|
| S_sim | Document 04 | Similarity component |
| S_alpha | Document 04 | Quality component |
| S_fresh | Document 04 | Freshness component |

### 15.2 Downstream (Consumers)

| Consumer | Usage |
|----------|-------|
| Document 07: Reranking | Uses BaseScore as starting point for adjustments |

---

## 16. Document References

| Related Document | Relationship |
|------------------|--------------|
| 03: Quality Gates | Filters episodes before scoring |
| 04: Scoring Components | Provides S_sim, S_alpha, S_fresh |
| 07: Narrative Reranking | Consumes BaseScore, applies adjustments |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Feb 2026 | Initial deep dive document |
