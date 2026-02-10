# Version Changelog

**Document:** 02 of 07 | Algorithm Evolution Documentation  
**Last Updated:** 2026-02-10

---

## Version History

| Version | Release Date | Name | Status |
|---------|--------------|------|--------|
| v1.0 | 2026-02-08 | Default Baseline | Archived |
| v1.1 | — | *Skipped* | — |
| v1.2 | 2026-02-05 | Blended Scoring | Archived |
| v1.3 | 2026-02-08 | Tuned Personalization | Archived |
| v1.4 | 2026-02-09 | Optimized Bookmark Weighting | Archived |
| **v1.5** | **2026-02-10** | **Diversified Cold Start** | **Production** |

> **Note:** Version 1.1 was skipped. Development jumped from v1.0 (baseline reference) directly to v1.2 (blended scoring architecture).

---

## v1.5 — Diversified Cold Start + Enhanced Bookmarks

**Release:** 2026-02-10  
**Based On:** v1.4  
**Overall Score:** 9.47 (highest)

### Summary

Introduced cold start category diversity to ensure balanced topic representation for new users, plus increased bookmark weight to 10.0x for stronger personalization signal.

### Changes from v1.4

| Change | Before | After | Rationale |
|--------|--------|-------|-----------|
| `bookmark_weight` | 7.0 | **10.0** | Stronger bookmark signal for hypothesis alignment |
| `cold_start_category_diversity` | N/A | **Enabled** | Ensure all 7 categories represented in first impression |
| `categories` field | Optional | **Required** | Needed for diversity algorithm |

### New Feature: Cold Start Category Diversity

```python
def apply_cold_start_category_diversity(scored, config, top_n=10):
    """
    Ensures at least 1 episode from each of 7 major categories
    in cold start recommendations via round-robin selection.
    """
```

**Target Categories:**
1. Technology & AI
2. Startups, Growth and Founder Journeys
3. Macro, Investing & Market Trends
4. Crypto & Web3
5. Regulation & Policy
6. Venture & Private Markets
7. Culture, Society & Wellbeing

### Test Results Impact

| Test | v1.4 | v1.5 | Change |
|------|------|------|--------|
| 01_cold_start_quality | 8.40 | 8.60 | +0.20 |
| 07_bookmark_weighting | 7.97 | 8.48 | +0.51 |

### Files Modified

- `recommendation_engine.py` — Added `apply_cold_start_category_diversity()` function
- `config.json` — Added `cold_start.category_diversity` section
- `manifest.json` — Updated version metadata, moved `categories` to required fields

---

## v1.4 — Optimized Bookmark Weighting

**Release:** 2026-02-09  
**Based On:** v1.3  
**Overall Score:** 9.38

### Summary

Increased bookmark weight from 5.0 to 7.0 to improve hypothesis alignment on Test 07 (Bookmark Weighting).

### Changes from v1.3

| Parameter | v1.3 | v1.4 | Rationale |
|-----------|------|------|-----------|
| `bookmark_weight` | 5.0 | **7.0** | Stronger bookmark signal for hypothesis alignment |

### Hypothesis

> "Bookmarks represent strongest user intent. Increasing weight will make bookmark-heavy users see more topically-aligned recommendations."

### Validation

- Test 07 improved from 7.88 → 7.97 (approaching pass threshold)
- Crypto-focused bookmark user saw 4/10 crypto recommendations vs 1/10 for click-only

### Files Modified

- `config.json` — Updated `engagement_weights.bookmark`
- `manifest.json` — Updated version and tuning_rationale

---

## v1.3 — Tuned Personalization

**Release:** 2026-02-08  
**Based On:** v1.2  
**Overall Score:** 9.30

### Summary

Major personalization tuning: increased similarity weight to 85%, introduced sum-of-similarities mode, and boosted bookmark weight to 5.0x.

### Changes from v1.2

| Parameter | v1.2 | v1.3 | Rationale |
|-----------|------|------|-----------|
| `weight_similarity` | 0.55 | **0.85** | Near-maximum personalization |
| `weight_quality` | 0.30 | **0.10** | Minimal quality influence |
| `weight_recency` | 0.15 | **0.05** | Minimal recency influence |
| `bookmark_weight` | 2.0 | **5.0** | Strong bookmark signal |
| `use_sum_similarities` | false | **true** | Preserve interest diversity |

### Key Innovation: Sum-of-Similarities

**Before (Mean-Pooling):**
```python
user_vector = mean([embed(ep) for ep in engaged_episodes])
similarity = cosine_sim(user_vector, candidate)
```

**Problem:** Mean-pooling blurs distinct interests (e.g., user interested in both AI and Crypto gets a "centroid" that matches neither well).

**After (Sum-of-Similarities):**
```python
similarities = [
    cosine_sim(candidate, engaged_ep) * weight 
    for engaged_ep in engaged_episodes
]
similarity_score = sum(similarities) / normalization
```

**Benefit:** Preserves distinct interest clusters; candidate matching ANY engaged topic scores well.

### Test Results Impact

| Test | v1.2 | v1.3 | Change |
|------|------|------|--------|
| 07_bookmark_weighting | 8.41 | 8.48 | +0.07 |
| 02_personalization_differs | 9.17 | 9.08 | -0.09 |

### Files Modified

- `recommendation_engine.py` — Added sum-of-similarities logic
- `config.json` — Updated all weight parameters
- `manifest.json` — Added comprehensive tuning_rationale

---

## v1.2 — Blended Scoring

**Release:** 2026-02-05  
**Based On:** N/A (new architecture)  
**Overall Score:** 9.30

### Summary

Introduced the 2-stage pipeline architecture with config-driven parameters, replacing hardcoded defaults.

### Architecture Introduced

1. **Stage A:** Candidate pool pre-selection with quality gates
2. **Stage B:** Personalized ranking with blended scoring formula
3. **Config Loading:** Runtime-configurable parameters via `config.json`

### Key Features

| Feature | Description |
|---------|-------------|
| Quality Gates | Credibility ≥ 2, Combined ≥ 5 |
| Engagement Weights | Configurable bookmark/listen/click weights |
| Cold Start Mode | Fallback to quality + recency when no user vector |
| Candidate Pool | Configurable pool size (default: 150) |

### Default Parameters

```json
{
  "weight_similarity": 0.55,
  "weight_quality": 0.30,
  "weight_recency": 0.15,
  "engagement_weights": {
    "bookmark": 2.0,
    "listen": 1.5,
    "click": 1.0
  }
}
```

### Files Created

- `recommendation_engine.py` — Full implementation
- `config.json` — Runtime configuration
- `manifest.json` — Version metadata
- `embedding_strategy.py` — Embedding generation logic

---

## v1.0 — Default Baseline

**Release:** 2026-02-08  
**Overall Score:** 9.32

### Summary

Reference baseline using hardcoded default parameters. Created to establish performance benchmarks before tuning.

### Purpose

- Establish baseline metrics for comparison
- Validate test suite against known behavior
- Document "out-of-the-box" algorithm performance

### Configuration

```json
{
  "_comment": "Empty config to use hardcoded defaults",
  "_note": "All parameters use DEFAULT_CONFIG values from recommendation_engine.py"
}
```

### Hardcoded Defaults

| Parameter | Value |
|-----------|-------|
| `weight_similarity` | 0.55 |
| `weight_quality` | 0.30 |
| `weight_recency` | 0.15 |
| `bookmark_weight` | 2.0 |
| `listen_weight` | 1.5 |
| `click_weight` | 1.0 |
| `use_sum_similarities` | false |

### Files

- `recommendation_engine.py` — Identical to v1.2 (same codebase)
- `config.json` — Empty (uses defaults)
- `manifest.json` — Baseline metadata

---

## Version Comparison Matrix

| Feature | v1.0 | v1.2 | v1.3 | v1.4 | v1.5 |
|---------|------|------|------|------|------|
| Config Loading | ❌ | ✅ | ✅ | ✅ | ✅ |
| Sum-of-Similarities | ❌ | ❌ | ✅ | ✅ | ✅ |
| Cold Start Diversity | ❌ | ❌ | ❌ | ❌ | ✅ |
| `bookmark_weight` | 2.0 | 2.0 | 5.0 | 7.0 | 10.0 |
| `weight_similarity` | 0.55 | 0.55 | 0.85 | 0.85 | 0.85 |
| Overall Score | 9.32 | 9.30 | 9.30 | 9.38 | 9.47 |

---

## Related Documents

- [03_PARAMETER_REFERENCE.md](./03_PARAMETER_REFERENCE.md) - Complete parameter documentation
- [04_PERFORMANCE_COMPARISON.md](./04_PERFORMANCE_COMPARISON.md) - Detailed test scores
- [06_TUNING_DECISIONS.md](./06_TUNING_DECISIONS.md) - Rationale for each change
