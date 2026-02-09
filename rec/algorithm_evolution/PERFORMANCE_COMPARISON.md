# Performance Comparison Across Algorithm Versions

**Last Updated:** 2026-02-08  
**Test Suite:** 8 tests (4 deterministic-only, 4 with LLM-as-Judge)  
**Dataset:** eval_909_feb2026 (909 episodes)

---

## Executive Summary

| Version | Overall Score | Tests Passed | Pass Rate |
|---------|--------------|--------------|-----------|
| v1.0 Default | 7.65 | 4/8 | 50.0% |
| v1.2 Blended | 8.29 | 6/8 | 75.0% |
| v1.3 Tuned | **8.80** | **6/8** | **75.0%** |

**Key Improvements:**
- v1.0 → v1.2: +8.4% score (bug fixes unlocked 2 tests)
- v1.2 → v1.3: +6.2% score (tuning improved personalization)
- v1.0 → v1.3: +15.0% overall improvement

---

## Test-by-Test Comparison

### Test 01: Cold Start Quality ✅✅✅

*Tests quality of recommendations for new users with no engagement history.*

| Criterion | v1.0 | v1.2 | v1.3 |
|-----------|------|------|------|
| cold_start_flag | ✓ 10.00 | ✓ 10.00 | ✓ 10.00 |
| avg_credibility | ✓ 10.00 | ✓ 10.00 | ✓ 10.00 |
| min_credibility | ✓ 10.00 | ✓ 10.00 | ✓ 10.00 |
| top_quality_score | ✓ 9.67 | ✓ 9.67 | ✓ 9.67 |
| llm_relevance | ✓ 8.00 | ✓ 9.00 | ✓ 9.00 |
| llm_diversity | ✓ 7.00 | ✓ 8.00 | ✓ 8.00 |
| llm_quality | ✓ 10.00 | ✓ 10.00 | ✓ 10.00 |
| llm_hypothesis_alignment | ✓ 8.00 | ✓ 9.00 | ✓ 9.00 |
| **AGGREGATE** | **✅ 9.17** | **✅ 9.50** | **✅ 9.50** |

**Analysis:** Cold start behavior is stable across all versions. Quality gates ensure high-quality content for new users.

---

### Test 02: Personalization Differs ❌✅✅

*Tests that personalized recommendations differ from cold start.*

| Criterion | v1.0 | v1.2 | v1.3 |
|-----------|------|------|------|
| episode_difference | ✗ 1.00 | ✓ 6.40 | ✓ 7.30 |
| similarity_increase | ✗ 3.00 | ✓ 10.00 | ✓ 5.96 |
| cold_start_flag_off | ✓ 10.00 | ✓ 10.00 | ✓ 10.00 |
| llm_relevance | ✓ 7.00 | ✓ 10.00 | ✓ 10.00 |
| llm_diversity | ✓ 6.00 | ✓ 7.00 | ✓ 8.00 |
| llm_quality | ✓ 9.00 | ✓ 10.00 | ✓ 10.00 |
| llm_hypothesis_alignment | ✗ 5.00 | ✓ 8.00 | ✓ 10.00 |
| **AGGREGATE** | **❌ 5.53** | **✅ 8.61** | **✅ 8.65** |

**Analysis:** v1.0 failed because engaged episodes were appearing in recommendations (no auto-exclusion). Fixed in v1.2.

---

### Test 03: Quality Gates ✅✅✅

*Tests that quality gates (credibility ≥2, C+I ≥5) are enforced.*

| Criterion | v1.0 | v1.2 | v1.3 |
|-----------|------|------|------|
| credibility_floor | ✓ 10.00 | ✓ 10.00 | ✓ 10.00 |
| combined_floor | ✓ 10.00 | ✓ 10.00 | ✓ 10.00 |
| **AGGREGATE** | **✅ 10.00** | **✅ 10.00** | **✅ 10.00** |

**Analysis:** Perfect scores across all versions. Quality gates are correctly implemented.

---

### Test 04: Excluded Episodes ✅✅✅

*Tests that excluded episodes never appear in recommendations.*

| Criterion | v1.0 | v1.2 | v1.3 |
|-----------|------|------|------|
| exclusions_respected | ✓ 10.00 | ✓ 10.00 | ✓ 10.00 |
| still_returns_results | ✓ 10.00 | ✓ 10.00 | ✓ 10.00 |
| **AGGREGATE** | **✅ 10.00** | **✅ 10.00** | **✅ 10.00** |

**Analysis:** Perfect scores. Exclusion logic works correctly.

---

### Test 05: Category Personalization ❌✅✅

*Tests that AI-focused and Crypto-focused users see appropriate content.*

| Criterion | v1.0 | v1.2 | v1.3 |
|-----------|------|------|------|
| ai_tech_category_match | ✓ 9.10 | ✓ 10.00 | ✓ 10.00 |
| crypto_category_match | ✗ 1.90 | ✓ 5.50 | ✓ 8.20 |
| llm_relevance | ✓ 8.00 | ✓ 10.00 | ✓ 9.00 |
| llm_diversity | ✓ 7.00 | ✓ 9.00 | ✓ 8.00 |
| llm_quality | ✓ 9.00 | ✓ 10.00 | ✓ 10.00 |
| llm_hypothesis_alignment | ✓ 6.00 | ✓ 9.00 | ✓ 9.00 |
| **AGGREGATE** | **❌ 6.64** | **✅ 8.75** | **✅ 9.04** |

**Analysis:** v1.0's crypto detection was poor (1.90). Improved through config loading (v1.2) and stronger personalization (v1.3).

---

### Test 06: Bookmark Weighting ❌❌❌

*Tests that bookmarked content is weighted more heavily than clicked content.*

| Criterion | v1.0 | v1.2 | v1.3 |
|-----------|------|------|------|
| different_results | ✗ 1.00 | ✓ 4.60 | ✓ 8.20 |
| crypto_dominance_in_b | ✓ 5.50 | ✓ 5.95 | ✓ 6.40 |
| llm_relevance | ✗ 3.00 | ✗ 2.00 | ✗ 3.00 |
| llm_diversity | ✗ 4.00 | ✗ 3.00 | ✗ 4.00 |
| llm_quality | ✓ 9.00 | ✓ 9.00 | ✓ 9.00 |
| llm_hypothesis_alignment | ✗ 1.00 | ✗ 1.00 | ✗ 1.00 |
| **AGGREGATE** | **❌ 4.04** | **❌ 4.39** | **❌ 5.35** |

**Analysis:** This test uses low-quality crypto episodes (one fails quality gates). The algorithm correctly filters low-quality content, but this conflicts with the test's expectation of crypto dominance.

---

### Test 07: Recency Scoring ✅✅✅

*Tests that recent content is ranked higher than older content of similar quality.*

| Criterion | v1.0 | v1.2 | v1.3 |
|-----------|------|------|------|
| both_in_top_10 | ✓ 10.00 | ✓ 10.00 | ✓ 10.00 |
| recency_score_ordering | ✓ 5.73 | ✓ 5.74 | ✓ 5.74 |
| ranking_reflects_recency | ✓ 7.75 | ✓ 7.75 | ✓ 7.75 |
| **AGGREGATE** | **✅ 7.55** | **✅ 7.56** | **✅ 7.56** |

**Analysis:** Stable recency behavior. The exponential decay formula works as expected.

---

### Test 08: Bookmark Weighting (High Quality) ❌❌❌

*Same as Test 06 but with high-quality crypto episodes that pass quality gates.*

| Criterion | v1.0 | v1.2 | v1.3 |
|-----------|------|------|------|
| different_results | ✗ 1.00 | ✓ 4.60 | ✓ 13.60 |
| crypto_dominance_in_b | ✓ 5.50 | ✓ 5.95 | ✓ 7.75 |
| llm_relevance | ✗ 1.00 | ✗ 1.00 | ✓ 6.00 |
| llm_diversity | ✗ 3.00 | ✗ 2.00 | ✓ 7.00 |
| llm_quality | ✓ 9.00 | ✓ 9.00 | ✓ 9.00 |
| llm_hypothesis_alignment | ✗ 1.00 | ✗ 1.00 | ✗ 4.00 |
| **AGGREGATE** | **❌ 3.58** | **❌ 4.08** | **❌ 7.88** |

**Analysis:** Dramatic improvement in v1.3 (+93%). With high-quality episodes, the algorithm now:
- Produces 14 different episodes between scenarios (vs 0 in v1.0)
- Shows 6 crypto episodes in bookmark scenario (vs 1)
- Passes llm_relevance and llm_diversity

**Remaining blocker:** `llm_hypothesis_alignment` at 4.00 (threshold 6.0). The LLM judge wants even stronger bookmark dominance.

---

## Failure Analysis

### Tests 06 & 08: Why `llm_hypothesis_alignment` Fails

The LLM judge evaluates whether the hypothesis "bookmarks should dominate" is reflected in recommendations. Current findings:

1. **Test 06 Issue:** One bookmarked crypto episode (`nbpPmxK8`) has C:2, I:2 → fails `combined_floor` quality gate. The algorithm correctly excludes it.

2. **Test 08 Status:** Uses high-quality episodes. v1.3 shows 6/10 crypto in the bookmark scenario, but the LLM still scores hypothesis alignment at 4/10.

3. **LLM Expectation:** The judge may expect 7-8+ crypto episodes for "dominance". Current 6/10 is majority but not overwhelming.

### Potential v1.4 Fixes

1. Reduce `llm_hypothesis_alignment` threshold to 5.0 (accept current behavior)
2. Add explicit category boost for bookmarked topics
3. Increase `bookmark_weight` beyond 5.0 (diminishing returns likely)
4. Try different `user_vector_limit` (currently 10)

---

## Appendix: Test Evaluation Reports

- v1.0: `/tmp/v1_0_results.json` (saved 2026-02-08)
- v1.2: `reports/20260208_152616_v1_2_blended__eval_909_feb2026.json`
- v1.3: `reports/20260208_152806_v1_3_tuned__eval_909_feb2026.json`
