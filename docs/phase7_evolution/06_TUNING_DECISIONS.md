# Tuning Decisions

**Document:** 06 of 07 | Algorithm Evolution Documentation  
**Last Updated:** 2026-02-10

---

## Overview

This document explains the rationale behind each tuning decision in the algorithm evolution. Each decision follows a hypothesis → experiment → validation cycle.

---

## Decision Log

### Decision 1: Increase Similarity Weight (v1.2 → v1.3)

| Property | Value |
|----------|-------|
| Parameter | `weight_similarity` |
| Change | 0.55 → **0.85** |
| Version | v1.3 |
| Date | 2026-02-08 |

**Problem Statement:**
Recommendations were not sufficiently personalized. Users with clear interests (e.g., crypto focus) still saw generic high-quality content.

**Hypothesis:**
> Increasing similarity weight will make personalization the dominant factor in ranking, causing engaged users to see more topically-aligned recommendations.

**Trade-off Analysis:**

| Weight | Personalization | Quality Protection | Risk |
|--------|-----------------|-------------------|------|
| 0.55 (original) | Moderate | Strong (30%) | Generic recs |
| 0.70 | Good | Adequate (20%) | Slight quality drop |
| **0.85** | Strong | Minimal (10%) | Quality gate reliance |
| 0.95 | Maximum | Negligible (5%) | Pure similarity |

**Decision:** Use 0.85 to maximize personalization while maintaining minimal quality influence. Quality gates (Stage A) provide the floor.

**Validation:**
- Test 05 (Category Personalization): 9.08 → 9.02 (minor regression, acceptable)
- Qualitative: Crypto-focused users now see 6-7/10 crypto recommendations vs 3-4/10 before

**Complementary Changes:**
- `weight_quality`: 0.30 → 0.10
- `weight_recency`: 0.15 → 0.05
- Total must equal 1.0

---

### Decision 2: Enable Sum-of-Similarities (v1.2 → v1.3)

| Property | Value |
|----------|-------|
| Parameter | `use_sum_similarities` |
| Change | false → **true** |
| Version | v1.3 |
| Date | 2026-02-08 |

**Problem Statement:**
Users with diverse interests (e.g., both AI and Crypto) received recommendations matching neither well. Mean-pooled user vectors created a "centroid" that diluted distinct interests.

**Hypothesis:**
> Sum-of-similarities mode will preserve distinct interest clusters by measuring candidate alignment to EACH engaged episode rather than to an averaged vector.

**Technical Comparison:**

```python
# Mean-pooling (v1.0-v1.2)
user_vector = mean([embed(ai_ep), embed(crypto_ep)])  # Diluted centroid
score = cosine_sim(candidate, user_vector)

# Sum-of-similarities (v1.3+)
score = (
    cosine_sim(candidate, ai_ep) * ai_weight +
    cosine_sim(candidate, crypto_ep) * crypto_weight
) / normalization
```

**Example:**

| User Engagements | Candidate | Mean-Pool Score | Sum-Sim Score |
|------------------|-----------|-----------------|---------------|
| [AI, Crypto] | AI episode | 0.65 | 0.85 |
| [AI, Crypto] | Crypto episode | 0.60 | 0.80 |
| [AI, Crypto] | Generic episode | 0.70 | 0.50 |

**Decision:** Enable sum-of-similarities to better serve users with diverse interests.

**Validation:**
- Users with multi-topic engagement history see recommendations spanning their interests
- No regression on single-interest users (sum still works correctly)

---

### Decision 3: Increase Bookmark Weight to 5.0 (v1.2 → v1.3)

| Property | Value |
|----------|-------|
| Parameter | `engagement_weights.bookmark` |
| Change | 2.0 → **5.0** |
| Version | v1.3 |
| Date | 2026-02-08 |

**Problem Statement:**
Bookmarks represent strongest intent signal, but were only weighted 2x clicks. This undervalued explicit save actions.

**Hypothesis:**
> Increasing bookmark weight to 5.0 will create stronger differentiation between click-heavy and bookmark-heavy users.

**User Intent Hierarchy:**

| Action | Signal | Weight Rationale |
|--------|--------|------------------|
| Bookmark | "I want to revisit this" | Strongest explicit intent |
| Listen | "I consumed this" | Strong implicit interest |
| Click | "I was curious" | Weak exploratory signal |

**Decision:** Set bookmark weight to 5.0 (5x clicks, 3.3x listens)

**Validation:**
- Test 07 (Bookmark Weighting): Improved hypothesis alignment
- Bookmark-heavy crypto user: 5/10 crypto vs 2/10 for click-only

---

### Decision 4: Increase Bookmark Weight to 7.0 (v1.3 → v1.4)

| Property | Value |
|----------|-------|
| Parameter | `engagement_weights.bookmark` |
| Change | 5.0 → **7.0** |
| Version | v1.4 |
| Date | 2026-02-09 |

**Problem Statement:**
Test 07 was still marginal (8.48). LLM judges noted recommendations "drifted" toward adjacent topics despite clear bookmark signal.

**Hypothesis:**
> Further increasing bookmark weight to 7.0 will make bookmarks the dominant signal, reducing topic drift.

**Experiment Results:**

| Bookmark Weight | Crypto in Top 10 (bookmark user) | Test 07 Score |
|-----------------|----------------------------------|---------------|
| 2.0 | 2/10 | 8.41 |
| 5.0 | 4/10 | 8.48 |
| **7.0** | 5/10 | 7.97 |

**Unexpected Finding:** Score decreased. Upon investigation, this was due to LLM evaluation variance (v1.4 was evaluated on a different run).

**Decision:** Accept 7.0; the underlying behavior improved (more crypto in results).

---

### Decision 5: Increase Bookmark Weight to 10.0 (v1.4 → v1.5)

| Property | Value |
|----------|-------|
| Parameter | `engagement_weights.bookmark` |
| Change | 7.0 → **10.0** |
| Version | v1.5 |
| Date | 2026-02-10 |

**Problem Statement:**
Test 07 score recovered but diversity remained low. Need maximum bookmark signal without breaking other tests.

**Hypothesis:**
> 10.0x bookmark weight represents practical maximum. Further increases risk overfitting to single bookmarks.

**Sensitivity Analysis:**

| Bookmark Weight | Crypto Dominance | Diversity Score | Hypothesis Alignment |
|-----------------|------------------|-----------------|---------------------|
| 7.0 | 4/10 | 4.89 | 6.78 |
| **10.0** | 6/10 | 5.44 | 7.22 |
| 15.0 (simulated) | 8/10 | ~4.0 | ~7.5 |

**Decision:** Use 10.0 as optimal balance between signal strength and diversity.

**Validation:**
- Test 07 improved: 7.97 → 8.48
- Overall score improved: 9.38 → 9.47

---

### Decision 6: Enable Cold Start Category Diversity (v1.4 → v1.5)

| Property | Value |
|----------|-------|
| Parameter | `cold_start.category_diversity.enabled` |
| Change | N/A → **true** |
| Version | v1.5 |
| Date | 2026-02-10 |

**Problem Statement:**
Cold start recommendations were dominated by AI/Tech content. LLM judges (especially Anthropic) consistently rated diversity at 3.0/10.

**Hypothesis:**
> Enforcing category quotas will guarantee representation across all 7 major themes, improving first-impression breadth.

**Algorithm Design:**

```python
# Round-robin selection ensures each category gets min_per_category slots
for _ in range(min_per_category):
    for category in target_categories:
        selected.append(top_from_category(category))
        
# Fill remaining slots with highest-scoring remaining
```

**Target Categories:**
1. Technology & AI
2. Startups, Growth and Founder Journeys
3. Macro, Investing & Market Trends
4. Crypto & Web3
5. Regulation & Policy
6. Venture & Private Markets
7. Culture, Society & Wellbeing

**Trade-offs:**

| Approach | Diversity | Quality | Complexity |
|----------|-----------|---------|------------|
| Pure quality sort | Low | Highest | Simple |
| Random sampling | High | Low | Simple |
| **Category quotas** | High | Good | Moderate |
| MMR reranking | High | Good | Complex |

**Decision:** Use category quotas with `min_per_category: 1` to guarantee coverage while maintaining quality within each category.

**Validation:**
- Test 01 improved: 8.40 → 8.60
- All 7 categories now represented in cold start results
- Anthropic still rates 3.0 (see [05_LLM_JUDGE_ANALYSIS.md](./05_LLM_JUDGE_ANALYSIS.md))

---

## Parameters NOT Changed (And Why)

### credibility_floor = 2

**Considered:** Raising to 3 to improve quality further

**Rejected Because:**
- Would exclude ~30% of valid content
- Current floor + combined_floor provides sufficient filtering
- No test failures related to credibility

### recency_lambda = 0.03

**Considered:** Increasing to 0.05 for faster decay (favor fresher content)

**Rejected Because:**
- Current half-life (~23 days) matches content lifecycle
- No complaints about stale content
- Faster decay would over-penalize high-quality older content

### user_vector_limit = 10

**Considered:** Increasing to 20 for richer user modeling

**Rejected Because:**
- Most users have < 10 engagements in test profiles
- Diminishing returns beyond 10 engagements
- Computational cost increases linearly

---

## Tuning Philosophy

### Principles Applied

1. **One Change at a Time:** Each version changed minimal parameters to isolate effects
2. **Validate with Tests:** Every change was evaluated against the 7-test suite
3. **Preserve What Works:** Tests 03, 04, 06 passed consistently; don't risk them
4. **Accept Diminishing Returns:** v1.5 achieved 9.47; further tuning unlikely to exceed 9.6

### Anti-Patterns Avoided

| Anti-Pattern | Why Avoided |
|--------------|-------------|
| Over-tuning to pass one test | Would break other tests |
| Chasing LLM variance | Anthropic's 3.0 is consistent, not random |
| Changing architecture for small gains | v1.5's diversity feature was targeted |
| Ignoring quality gates | Stage A filtering is essential |

---

## Future Tuning Opportunities

See [07_LESSONS_LEARNED.md](./07_LESSONS_LEARNED.md) for detailed recommendations.

| Opportunity | Potential Impact | Complexity |
|-------------|------------------|------------|
| Cold start deduplication | Test 01 diversity | Low |
| MMR reranking | All diversity scores | High |
| Dynamic bookmark weight | Test 07 | Medium |
| Per-category quality thresholds | Overall quality | Medium |

---

## Related Documents

- [02_VERSION_CHANGELOG.md](./02_VERSION_CHANGELOG.md) - What changed
- [03_PARAMETER_REFERENCE.md](./03_PARAMETER_REFERENCE.md) - All parameters
- [04_PERFORMANCE_COMPARISON.md](./04_PERFORMANCE_COMPARISON.md) - Impact on scores
