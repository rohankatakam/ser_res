# Parameter Reference

**Document:** 03 of 07 | Algorithm Evolution Documentation  
**Last Updated:** 2026-02-10

---

## Parameter Categories

1. [Scoring Weights](#scoring-weights) — Control the final score composition
2. [Engagement Weights](#engagement-weights) — Weight user actions differently
3. [Quality Gates](#quality-gates) — Filter thresholds for candidate selection
4. [Cold Start Parameters](#cold-start-parameters) — New user handling
5. [Technical Parameters](#technical-parameters) — Algorithm behavior tuning

---

## Scoring Weights

These parameters control how similarity, quality, and recency contribute to the final score.

### weight_similarity

| Property | Value |
|----------|-------|
| Type | `float` (0.0 - 1.0) |
| Default | 0.55 |
| Current (v1.5) | **0.85** |
| Constraint | `weight_similarity + weight_quality + weight_recency = 1.0` |

**Description:** Proportion of final score derived from user-content similarity. Higher values prioritize personalization over content quality.

**Evolution:**
| Version | Value | Rationale |
|---------|-------|-----------|
| v1.0 | 0.55 | Balanced baseline |
| v1.2 | 0.55 | Unchanged |
| v1.3 | **0.85** | Maximize personalization |
| v1.4 | 0.85 | Unchanged |
| v1.5 | 0.85 | Unchanged |

---

### weight_quality

| Property | Value |
|----------|-------|
| Type | `float` (0.0 - 1.0) |
| Default | 0.30 |
| Current (v1.5) | **0.10** |

**Description:** Proportion of final score derived from content quality (credibility × insight). Reduced in v1.3 to let personalization dominate.

**Evolution:**
| Version | Value | Rationale |
|---------|-------|-----------|
| v1.0 | 0.30 | Strong quality emphasis |
| v1.2 | 0.30 | Unchanged |
| v1.3 | **0.10** | Minimal quality influence |
| v1.4 | 0.10 | Unchanged |
| v1.5 | 0.10 | Unchanged |

---

### weight_recency

| Property | Value |
|----------|-------|
| Type | `float` (0.0 - 1.0) |
| Default | 0.15 |
| Current (v1.5) | **0.05** |

**Description:** Proportion of final score derived from publication freshness. Reduced to minimize recency bias.

**Evolution:**
| Version | Value | Rationale |
|---------|-------|-----------|
| v1.0 | 0.15 | Moderate freshness boost |
| v1.2 | 0.15 | Unchanged |
| v1.3 | **0.05** | Minimal recency influence |
| v1.4 | 0.05 | Unchanged |
| v1.5 | 0.05 | Unchanged |

---

## Engagement Weights

These parameters differentiate user actions by signal strength.

### bookmark_weight (engagement_weights.bookmark)

| Property | Value |
|----------|-------|
| Type | `float` |
| Default | 2.0 |
| Current (v1.5) | **10.0** |
| Range | 1.0 - 20.0 (recommended) |

**Description:** Multiplier for bookmarked episodes in user vector calculation. Represents strongest explicit interest signal.

**Evolution:**
| Version | Value | Rationale |
|---------|-------|-----------|
| v1.0 | 2.0 | Baseline (2x clicks) |
| v1.2 | 2.0 | Unchanged |
| v1.3 | **5.0** | Strong bookmark signal |
| v1.4 | **7.0** | Improved hypothesis alignment |
| v1.5 | **10.0** | Maximum bookmark influence |

**Impact Analysis:**
- v1.3 (5.0): Test 07 diversity improved but hypothesis alignment still weak
- v1.4 (7.0): Approaching pass threshold on Test 07
- v1.5 (10.0): Best overall score; strong crypto dominance for bookmark users

---

### listen_weight (engagement_weights.listen)

| Property | Value |
|----------|-------|
| Type | `float` |
| Default | 1.5 |
| Current (v1.5) | **1.5** |

**Description:** Multiplier for listened episodes. Unchanged across all versions.

---

### click_weight (engagement_weights.click)

| Property | Value |
|----------|-------|
| Type | `float` |
| Default | 1.0 |
| Current (v1.5) | **1.0** |

**Description:** Baseline multiplier for clicked episodes. All other weights are relative to clicks.

---

## Quality Gates

These parameters filter candidates in Stage A.

### credibility_floor

| Property | Value |
|----------|-------|
| Type | `int` (1-4) |
| Default | 2 |
| Current (v1.5) | **2** |

**Description:** Minimum credibility score required for inclusion. Episodes with credibility < 2 are excluded.

**Scale:**
- 1 = Low credibility
- 2 = Acceptable
- 3 = Good
- 4 = Excellent

---

### combined_floor

| Property | Value |
|----------|-------|
| Type | `int` (2-9) |
| Default | 5 |
| Current (v1.5) | **5** |

**Description:** Minimum sum of (Credibility + Insight) required. Ensures substantive content from reliable sources.

**Formula:** `credibility + insight >= combined_floor`

---

### freshness_window_days

| Property | Value |
|----------|-------|
| Type | `int` |
| Default | 90 |
| Current (v1.5) | **90** |

**Description:** Maximum age (in days) for episodes to be considered. Episodes older than this are excluded from candidate pool.

---

### candidate_pool_size

| Property | Value |
|----------|-------|
| Type | `int` |
| Default | 150 |
| Current (v1.5) | **150** |

**Description:** Maximum number of candidates to pass to Stage B for ranking.

---

## Cold Start Parameters

### cold_start.weight_quality

| Property | Value |
|----------|-------|
| Type | `float` (0.0 - 1.0) |
| Default | 0.60 |
| Current (v1.5) | **0.60** |

**Description:** Quality weight used when no user vector exists. Higher than normal `weight_quality` to ensure new users see best content.

---

### cold_start.weight_recency

| Property | Value |
|----------|-------|
| Type | `float` (0.0 - 1.0) |
| Default | 0.40 |
| Current (v1.5) | **0.40** |

**Description:** Recency weight for cold start scoring.

---

### cold_start.category_diversity.enabled

| Property | Value |
|----------|-------|
| Type | `boolean` |
| Default | false |
| Current (v1.5) | **true** |
| Introduced | v1.5 |

**Description:** Enables round-robin category selection for cold start recommendations.

---

### cold_start.category_diversity.min_per_category

| Property | Value |
|----------|-------|
| Type | `int` |
| Default | 1 |
| Current (v1.5) | **1** |
| Introduced | v1.5 |

**Description:** Minimum episodes from each category to include in cold start results.

---

### cold_start.category_diversity.categories

| Property | Value |
|----------|-------|
| Type | `array[string]` |
| Introduced | v1.5 |

**Description:** Target categories for diversity enforcement.

**Current Value:**
```json
[
  "Technology & AI",
  "Startups, Growth and Founder Journeys",
  "Macro, Investing & Market Trends",
  "Crypto & Web3",
  "Regulation & Policy",
  "Venture & Private Markets",
  "Culture, Society & Wellbeing"
]
```

---

## Technical Parameters

### use_sum_similarities

| Property | Value |
|----------|-------|
| Type | `boolean` |
| Default | false |
| Current (v1.5) | **true** |
| Introduced | v1.3 |

**Description:** When `true`, calculates similarity as weighted sum of individual episode similarities rather than similarity to mean-pooled user vector.

**Trade-offs:**
| Mode | Pros | Cons |
|------|------|------|
| Mean-pooling (`false`) | Faster, simpler | Blurs distinct interests |
| Sum-of-similarities (`true`) | Preserves interest clusters | More computation |

---

### user_vector_limit

| Property | Value |
|----------|-------|
| Type | `int` |
| Default | 10 |
| Current (v1.5) | **10** |

**Description:** Maximum number of recent engagements to consider when building user vector. Prevents over-weighting of long engagement history.

---

### credibility_multiplier

| Property | Value |
|----------|-------|
| Type | `float` |
| Default | 1.5 |
| Current (v1.5) | **1.5** |

**Description:** Boost factor for credibility in quality score calculation.

**Formula:**
```python
quality_score = (credibility / 4.0) * credibility_multiplier * (insight / 5.0)
```

---

### recency_lambda

| Property | Value |
|----------|-------|
| Type | `float` |
| Default | 0.03 |
| Current (v1.5) | **0.03** |

**Description:** Decay rate for exponential recency scoring.

**Formula:**
```python
recency_score = exp(-recency_lambda * days_old)
```

**Interpretation:**
- `lambda = 0.03` → Half-life ≈ 23 days
- 30-day-old content scores ~0.41
- 60-day-old content scores ~0.17
- 90-day-old content scores ~0.07

---

## Parameter Evolution Table

| Parameter | v1.0 | v1.2 | v1.3 | v1.4 | v1.5 |
|-----------|------|------|------|------|------|
| **Scoring Weights** |
| weight_similarity | 0.55 | 0.55 | **0.85** | 0.85 | 0.85 |
| weight_quality | 0.30 | 0.30 | **0.10** | 0.10 | 0.10 |
| weight_recency | 0.15 | 0.15 | **0.05** | 0.05 | 0.05 |
| **Engagement Weights** |
| bookmark_weight | 2.0 | 2.0 | **5.0** | **7.0** | **10.0** |
| listen_weight | 1.5 | 1.5 | 1.5 | 1.5 | 1.5 |
| click_weight | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| **Algorithm Modes** |
| use_sum_similarities | false | false | **true** | true | true |
| cold_start_diversity | — | — | — | — | **enabled** |
| **Quality Gates** |
| credibility_floor | 2 | 2 | 2 | 2 | 2 |
| combined_floor | 5 | 5 | 5 | 5 | 5 |

---

## Configuration File Locations

| Version | Config Path |
|---------|-------------|
| v1.0 | `algorithms/v1_0_default/config.json` |
| v1.2 | `algorithms/v1_2_blended/config.json` |
| v1.3 | `algorithms/v1_3_tuned/config.json` |
| v1.4 | `algorithms/v1_4_optimized/config.json` |
| v1.5 | `algorithms/v1_5_diversified/config.json` |

---

## Related Documents

- [02_VERSION_CHANGELOG.md](./02_VERSION_CHANGELOG.md) - When parameters changed
- [06_TUNING_DECISIONS.md](./06_TUNING_DECISIONS.md) - Why parameters changed
