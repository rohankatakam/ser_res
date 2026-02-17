# v1.0 Default Baseline

**Created:** 2026-02-08  
**Folder:** `algorithms/v1_0_default/`  
**Status:** Reference baseline (not for production)

---

## Purpose

v1.0 was created to preserve the algorithm behavior before the config loading bug was fixed. It represents:

1. The actual behavior during early Phase 4 testing (when we thought we were testing v1.2)
2. A baseline for measuring improvement from infrastructure fixes
3. Historical reference for traceability

---

## Configuration

Uses hardcoded `DEFAULT_CONFIG` values (no config.json override):

```json
{
  "stage_b": {
    "user_vector_limit": 10,
    "weight_similarity": 0.55,
    "weight_quality": 0.30,
    "weight_recency": 0.15,
    "credibility_multiplier": 1.5,
    "recency_lambda": 0.03,
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

## Key Characteristics

1. **No auto-exclusion:** Engaged episodes could appear in new recommendations
2. **Mean-pooling only:** No sum-of-similarities option
3. **Identical parameters to v1.2:** The difference is in how they're loaded

---

## Test Performance

| Test | Status | Score |
|------|--------|-------|
| 01 Cold Start | ✅ | 9.17 |
| 02 Personalization | ❌ | 5.53 |
| 03 Quality Gates | ✅ | 10.00 |
| 04 Exclusions | ✅ | 10.00 |
| 05 Category | ❌ | 6.64 |
| 06 Bookmark | ❌ | 4.04 |
| 07 Recency | ✅ | 7.55 |
| 08 Bookmark HQ | ❌ | 3.58 |
| **Overall** | **4/8** | **7.65** |

---

## Why Tests Failed

- **Test 02:** Engaged episodes appearing in recommendations (no auto-exclusion)
- **Test 05:** Crypto profile not showing enough crypto content
- **Tests 06/08:** Minimal difference between bookmark/click scenarios

---

## Files

- `manifest.json` - Version metadata
- `config.json` - Empty (uses defaults)
- `recommendation_engine.py` - Identical to v1.2
- `embedding_strategy.py` - Identical to v1.2
