# v1.3 Tuned Personalization

**Created:** 2026-02-08  
**Folder:** `algorithms/v1_3_tuned/`  
**Status:** Experimental tuning (Phase 4)

---

## Purpose

v1.3 explores maximum personalization to improve bookmark weighting tests. It:
- Dramatically increases similarity weight (55% → 85%)
- Increases bookmark engagement weight (2x → 5x)
- Enables sum-of-similarities for interest diversity

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
    "weight_similarity": 0.85,
    "weight_quality": 0.10,
    "weight_recency": 0.05,
    "credibility_multiplier": 1.5,
    "recency_lambda": 0.03,
    "use_weighted_engagements": true,
    "use_sum_similarities": true
  },
  "engagement_weights": {
    "bookmark": 5.0,
    "listen": 1.5,
    "click": 1.0
  }
}
```

---

## Parameter Changes from v1.2

| Parameter | v1.2 | v1.3 | Rationale |
|-----------|------|------|-----------|
| `weight_similarity` | 0.55 | **0.85** | Maximum personalization |
| `weight_quality` | 0.30 | **0.10** | Quality gates still apply |
| `weight_recency` | 0.15 | **0.05** | Minimize recency influence |
| `bookmark` weight | 2.0 | **5.0** | Strong bookmark signal |
| `use_sum_similarities` | false | **true** | Preserve interest diversity |

---

## Sum-of-Similarities Mode

Instead of averaging user embeddings (mean-pooling), v1.3 can compare each candidate to each engagement individually:

**Mean-pooling (v1.2 default):**
```
user_vector = mean(embedding[eng1], embedding[eng2], ...)
similarity = cosine(candidate, user_vector)
```

**Sum-of-similarities (v1.3):**
```
similarity = Σ (weight[eng_i] × cosine(candidate, embedding[eng_i])) / Σ weights
```

**Advantage:** Candidates that match ANY user interest get credit, rather than needing to match the "average" interest.

---

## Code (No Changes)

v1.3 uses identical `recommendation_engine.py` as v1.2. All behavior changes are configuration-driven.

The sum-of-similarities logic was already implemented:

```python
def compute_similarity_sum(candidate, engagements, embeddings, episode_by_content_id, config):
    """Compute similarity using sum-of-similarities approach."""
    # ... compares candidate to each engagement
```

```python
def rank_candidates(...):
    if config.use_sum_similarities:
        similarity = compute_similarity_sum(...)
    else:
        similarity = cosine_similarity(user_vector, candidate_embedding)
```

---

## Test Performance

| Test | Status | Score | Change from v1.2 |
|------|--------|-------|------------------|
| 01 Cold Start | ✅ | 9.50 | — |
| 02 Personalization | ✅ | 8.65 | +0.04 |
| 03 Quality Gates | ✅ | 10.00 | — |
| 04 Exclusions | ✅ | 10.00 | — |
| 05 Category | ✅ | 9.04 | +0.29 |
| 06 Bookmark | ❌ | 5.35 | +0.96 |
| 07 Recency | ✅ | 7.56 | — |
| 08 Bookmark HQ | ❌ | 7.88 | **+3.80** |
| **Overall** | **6/8** | **8.80** | **+0.51** |

---

## Key Improvements

### Test 08 (Bookmark Weighting, High Quality)

| Criterion | v1.2 | v1.3 |
|-----------|------|------|
| different_results | 4.60 | **13.60** |
| crypto_dominance_in_b | 5.95 | **7.75** |
| llm_relevance | 1.00 | **6.00** ✅ |
| llm_diversity | 2.00 | **7.00** ✅ |
| llm_hypothesis_alignment | 1.00 | 4.00 (still fails) |

**What improved:**
- 14 different episodes between scenarios (vs 4)
- 6/10 crypto episodes in bookmark scenario (vs 2)
- LLM now rates relevance and diversity as passing

**What still fails:**
- `llm_hypothesis_alignment` at 4.0 (threshold 6.0)
- LLM wants even stronger bookmark dominance

---

## Trade-offs

### Pros
- Significantly improved personalization test scores
- Better interest diversity with sum-of-similarities
- Stronger response to user engagement signals

### Cons
- Quality influence reduced (10% vs 30%)
- May over-personalize for users with narrow interests
- Recency almost negligible (5%)

### Mitigations
- Quality gates still enforce minimum standards (C≥2, C+I≥5)
- Could tune back toward balance in v1.4 if needed

---

## Next Steps (v1.4)

Potential approaches to achieve 7/8 or 8/8 pass rate:

1. **Lower LLM threshold:** Reduce `llm_hypothesis_alignment` from 6.0 to 5.0
2. **Category boost:** Add explicit category matching for bookmarked topics
3. **Engagement recency:** Weight recent engagements higher in user vector
4. **Rebalance:** Find middle ground between v1.2 and v1.3 weights

---

## Files

- `manifest.json` - Algorithm metadata with tuning rationale
- `config.json` - Aggressive personalization parameters
- `recommendation_engine.py` - Identical to v1.2
- `embedding_strategy.py` - Identical to v1.2
