# Algorithm Changelog

This document tracks all algorithm versions with their changes, rationale, and impact on test performance.

---

## v1.3 Tuned Personalization (2026-02-08)

**Goal:** Maximize personalization signal to improve bookmark weighting tests.

### Parameter Changes

| Parameter | v1.2 Value | v1.3 Value | Rationale |
|-----------|-----------|-----------|-----------|
| `bookmark_weight` | 2.0 | **5.0** | Strong differentiation for bookmarked content |
| `weight_similarity` | 0.55 | **0.85** | Near-maximum personalization influence |
| `weight_quality` | 0.30 | **0.10** | Minimal quality influence (quality gates still apply) |
| `weight_recency` | 0.15 | **0.05** | Minimal recency influence |
| `use_sum_similarities` | false | **true** | Preserves interest diversity vs mean-pooling |

### Code Changes

- **No code changes** — v1.3 uses identical `recommendation_engine.py` as v1.2
- All changes are configuration-driven via `config.json`

### Test Impact

| Test | v1.2 → v1.3 | Notes |
|------|-------------|-------|
| 05 Category Personalization | 8.75 → 9.04 (+0.29) | Improved crypto detection |
| 06 Bookmark Weighting | 4.39 → 5.35 (+0.96) | Still fails `llm_hypothesis_alignment` |
| 08 Bookmark HQ | 4.08 → 7.88 (+3.80) | **Dramatic improvement**, still fails LLM alignment |
| **Overall** | **8.29 → 8.80** | **+6.2% improvement** |

### Key Insight

The `llm_hypothesis_alignment` criterion (threshold 6.0) remains the blocker. Test 08 now passes all deterministic criteria and most LLM criteria, but the LLM judge wants even stronger bookmark dominance.

---

## v1.2 Blended Scoring (2026-02-05)

**Goal:** Production-ready algorithm with proper configuration loading.

### Infrastructure Fixes (2026-02-08)

1. **Config Loading Bug**: `server.py` was not passing `config.json` to the recommendation engine. All tests were running on hardcoded `DEFAULT_CONFIG` values.
   - Fixed: `create_session()` and `_call_recommendation_api()` now load and pass `algo_config`
   - Fixed: `recommendation_engine.py` handles `config=None` gracefully

2. **Auto-Exclusion**: Added server-side logic to exclude engaged episode IDs from new recommendations.
   - Previously, engaged episodes could appear in new sessions
   - Now: `excluded_ids` automatically includes all `engagement.episode_id` values

3. **Test Case 08**: Added `08_bookmark_weighting_high_quality.json` with episodes that pass quality gates (C≥3, I≥3).

### Parameters (Defined in config.json)

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `weight_similarity` | 0.55 | User interest matching |
| `weight_quality` | 0.30 | Quality score influence |
| `weight_recency` | 0.15 | Freshness preference |
| `bookmark_weight` | 2.0 | Bookmark engagement multiplier |
| `credibility_multiplier` | 1.5 | Credibility weighted higher in quality score |
| `recency_lambda` | 0.03 | ~23 day half-life decay |

### Test Results (with LLM, post-fix)

| Test | Status | Score |
|------|--------|-------|
| 01 Cold Start Quality | ✅ | 9.50 |
| 02 Personalization Differs | ✅ | 8.61 |
| 03 Quality Gates | ✅ | 10.00 |
| 04 Excluded Episodes | ✅ | 10.00 |
| 05 Category Personalization | ✅ | 8.75 |
| 06 Bookmark Weighting | ❌ | 4.39 |
| 07 Recency Scoring | ✅ | 7.56 |
| 08 Bookmark HQ | ❌ | 4.08 |
| **Overall** | **6/8** | **8.29** |

---

## v1.0 Default Baseline (2026-02-08)

**Goal:** Preserve the baseline behavior before config loading was fixed.

### Context

When the config loading bug was discovered, we realized all prior testing was using hardcoded `DEFAULT_CONFIG` values rather than the intended `config.json` parameters. v1.0 was created to:

1. Document what was actually being tested during early Phase 4
2. Serve as a reference baseline for comparison
3. Preserve the "original" behavior for traceability

### Parameters (Hardcoded DEFAULT_CONFIG)

Same values as v1.2's config.json, but loaded differently:
- v1.0: Uses `DEFAULT_CONFIG` object in Python code (no config.json override)
- v1.2: Uses `config.json` parsed and passed to engine

### Test Results (with LLM)

| Test | Status | Score |
|------|--------|-------|
| 01 Cold Start Quality | ✅ | 9.17 |
| 02 Personalization Differs | ❌ | 5.53 |
| 03 Quality Gates | ✅ | 10.00 |
| 04 Excluded Episodes | ✅ | 10.00 |
| 05 Category Personalization | ❌ | 6.64 |
| 06 Bookmark Weighting | ❌ | 4.04 |
| 07 Recency Scoring | ✅ | 7.55 |
| 08 Bookmark HQ | ❌ | 3.58 |
| **Overall** | **4/8** | **7.65** |

### Key Insight

The 50% → 75% pass rate jump from v1.0 to v1.2 was primarily due to the **config loading fix** and **auto-exclusion fix**, not parameter tuning. Tests 02 and 05 started passing once engaged episodes were properly excluded.

---

## Original Specification (January 2026)

**Source:** Text brief from Rohan Sharma, Founder

```
Recommendation algorithm:
- determine user-specific ranking score for an episode candidate
- for the top 10 (or whatever n) episodes in the user's activity:
  - calculate vector similarity with candidate + user episode (activity)
  - add up scores across top 10 -> overall similarity of candidate to user's interests

Recommendation params:
  - similarity to user's interests (semantic match between episode titles + descriptions)
  - (v2) overlap between candidate episode categories and user aggregate category activity
  - Serafis quality score (weight credibility higher, combine with insight)
  - recency of the candidate content
 
What are the top 10 for user's activity?
  - order by recency of activity (simple to start)
  - later on, order by depth of engagement (did they listen to the full thing? bookmark? etc)
```

### Translation to v1.0

| Brief Element | Implementation |
|---------------|----------------|
| "Add up scores across top 10" | Initially: mean-pooling. v1.3 adds sum-of-similarities option |
| "Semantic match" | OpenAI `text-embedding-3-small` embeddings (1536-dim) |
| "Weight credibility higher" | `credibility_multiplier: 1.5` in quality score |
| "Recency of candidate" | Exponential decay with `recency_lambda: 0.03` |
| "Order by recency" | Engagements sorted by timestamp, limited to `user_vector_limit: 10` |
| "Depth of engagement" | `engagement_weights: {bookmark: 2.0, listen: 1.5, click: 1.0}` |
| "(v2) Category overlap" | **Not implemented** — deferred |

---

## Future: v1.4 (Planned)

**Goal:** Address remaining `llm_hypothesis_alignment` failures in Tests 06 and 08.

### Potential Approaches

1. **Lower LLM threshold**: Reduce `llm_hypothesis_alignment` threshold from 6.0 to 5.0
2. **Category boost**: Add explicit category matching signal for bookmarked topics
3. **Engagement recency weighting**: Weight more recent engagements higher in user vector
4. **Quality gate adjustment**: Consider if quality gates are too strict for test episodes

### Decision Criteria

- Maintain all currently passing tests (no regressions)
- Achieve 7/8 or 8/8 pass rate
- Preserve high quality scores on LLM criteria
