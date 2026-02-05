# Serafis "For You" Feed — Testing Strategy

> *Comprehensive testing framework for the V1.1 recommendation pipeline*

**Version:** 1.0  
**Date:** February 4, 2026  
**Related:** FOR_YOU_V1_1_SPEC.md, FOR_YOU_TESTING_GUIDE.md

---

## Overview

This document defines the testing strategy for validating the V1.1 recommendation algorithm. It covers:

1. **Unit Tests** — Individual component validation
2. **Integration Tests** — End-to-end pipeline testing
3. **Manual Testing** — Frontend-based exploration
4. **Evaluation Metrics** — Quantitative success criteria

---

## 1. Unit Tests

### 1.1 Candidate Pool Pre-Selection (Stage A)

| Test ID | Test Name | Setup | Expected Result | Pass Criteria |
|---------|-----------|-------|-----------------|---------------|
| A.1 | Credibility floor | Episode with C=1 | Filtered out | Not in candidate pool |
| A.2 | Credibility pass | Episode with C=2 | Included | In candidate pool |
| A.3 | Combined floor fail | Episode with C=2, I=2 (sum=4) | Filtered out | Not in candidate pool |
| A.4 | Combined floor pass | Episode with C=2, I=3 (sum=5) | Included | In candidate pool |
| A.5 | Freshness filter | Episode 45 days old | Filtered out | Not in candidate pool |
| A.6 | Freshness pass | Episode 10 days old | Included | In candidate pool |
| A.7 | Exclusion filter | Episode in user's seen list | Filtered out | Not in candidate pool |
| A.8 | Pool size limit | 100 episodes pass filters | Only 50 returned | len(pool) == 50 |
| A.9 | Quality sorting | Mixed quality episodes | Sorted by C+I desc | pool[0] has highest C+I |

**Test Code:**
```python
def test_credibility_floor():
    """Episode with credibility < 2 should be filtered out."""
    episode = {"id": "test1", "scores": {"credibility": 1, "insight": 4}}
    candidates = get_candidate_pool([episode], excluded_ids=set())
    assert len(candidates) == 0

def test_combined_floor():
    """Episode with C+I < 5 should be filtered out."""
    episode = {"id": "test2", "scores": {"credibility": 2, "insight": 2}}
    candidates = get_candidate_pool([episode], excluded_ids=set())
    assert len(candidates) == 0

def test_freshness_filter():
    """Episode older than 30 days should be filtered out."""
    old_date = (datetime.now() - timedelta(days=45)).isoformat()
    episode = {"id": "test3", "scores": {"credibility": 3, "insight": 3}, "published_at": old_date}
    candidates = get_candidate_pool([episode], excluded_ids=set())
    assert len(candidates) == 0
```

### 1.2 Embedding Generation

| Test ID | Test Name | Setup | Expected Result | Pass Criteria |
|---------|-----------|-------|-----------------|---------------|
| B.1 | Embed text format | Episode with title + key_insights | Correct concatenation | Text = "Title. Key insights..." |
| B.2 | Fallback to key_insight | Episode without critical_views | Uses key_insight | Text contains key_insight |
| B.3 | Truncation | key_insights > 500 chars | Truncated | len(text) < 600 |
| B.4 | Empty handling | Episode with no insights | Uses title only | Text = title |
| B.5 | Vector dimensions | Any episode | 1536-dim vector | len(vector) == 1536 |

### 1.3 User Activity Vector

| Test ID | Test Name | Setup | Expected Result | Pass Criteria |
|---------|-----------|-------|-----------------|---------------|
| C.1 | Cold start | 0 engagements | None returned | user_vector is None |
| C.2 | Single engagement | 1 click | That episode's vector | vector == episode_vector |
| C.3 | Multiple engagements | 5 clicks | Mean of 5 vectors | vector = mean(vectors) |
| C.4 | Recency limit | 10 clicks, limit=5 | Only 5 most recent | len(used_engagements) == 5 |
| C.5 | Weighted (Option B) | 1 bookmark, 1 click | Bookmark weighted 2x | vector closer to bookmark |

### 1.4 Cosine Similarity

| Test ID | Test Name | Setup | Expected Result | Pass Criteria |
|---------|-----------|-------|-----------------|---------------|
| D.1 | Identical vectors | v1 == v2 | sim = 1.0 | sim == 1.0 |
| D.2 | Orthogonal vectors | dot(v1, v2) = 0 | sim = 0.0 | sim == 0.0 |
| D.3 | Opposite vectors | v1 == -v2 | sim = -1.0 | sim == -1.0 |
| D.4 | Normal range | Random vectors | -1 ≤ sim ≤ 1 | Valid range |

---

## 2. Integration Tests

### 2.1 End-to-End Pipeline

| Test ID | Test Name | Setup | Expected Result | Pass Criteria |
|---------|-----------|-------|-----------------|---------------|
| E2E.1 | Cold start flow | New user, 0 engagements | Top 10 by quality | All have C+I ≥ 5 |
| E2E.2 | Personalized flow | User with 5 AI clicks | AI episodes ranked higher | ≥7 of top 10 are AI-related |
| E2E.3 | Exclusion works | User clicks episode A | A not in recommendations | A not in results |
| E2E.4 | Quality maintained | Any user | All recs pass gates | All have C≥2, C+I≥5 |
| E2E.5 | Freshness maintained | Any user | All recs are recent | All ≤30 days old |

### 2.2 Personalization Tests

| Test ID | Scenario | User Setup | Expected Outcome |
|---------|----------|------------|------------------|
| P.1 | AI interest | 5 clicks on AI episodes | AI episodes dominate top 5 |
| P.2 | Crypto interest | 5 clicks on Crypto episodes | Crypto episodes dominate top 5 |
| P.3 | Mixed interests | 3 AI + 2 Crypto clicks | Mix of AI and Crypto in top 10 |
| P.4 | Interest shift | 5 old AI clicks + 2 recent Crypto | Crypto weighted higher (recency) |
| P.5 | Strong signal | 1 bookmark vs 3 clicks | Bookmark topic represented |

### 2.3 Edge Case Tests

| Test ID | Scenario | Setup | Expected Behavior |
|---------|----------|-------|-------------------|
| EC.1 | User seen everything | All episodes in excluded_ids | Empty results, graceful message |
| EC.2 | No recent content | All episodes > 30 days old | Expand to 60 days |
| EC.3 | Low quality catalog | Most episodes C < 2 | Return fewer results, not low quality |
| EC.4 | Single category | All viewed same category | Still show variety from that category |
| EC.5 | Very new user | Only 1 engagement | Personalization visible but subtle |

---

## 3. Manual Testing

### 3.1 Testing Frontend

The testing frontend (`/rec/prototype/`) provides interactive testing capabilities:

**Features:**
- Browse all episodes in a grid
- Click episodes to simulate engagement
- View episode details (scores, insights, entities)
- Track engagement history
- View "For You" recommendations in real-time
- Reset to cold start

**Manual Test Workflow:**

1. **Cold Start Test**
   - Open app fresh (or click Reset)
   - Observe: Should see "Highest Signal" section
   - Verify: All shown episodes have C≥2, C+I≥5
   - Verify: Episodes are sorted by quality

2. **First Engagement Test**
   - Click on one AI-related episode
   - Observe: Recommendations should update
   - Verify: Still quality-filtered
   - Note: May not be dramatically different with 1 click

3. **Personalization Build-Up**
   - Click 3-5 AI episodes
   - Observe: AI content should rise in rankings
   - Verify: "For You" section appears
   - Compare: Different from cold start

4. **Category Exploration**
   - Click on a Crypto episode
   - Observe: Mix of AI and Crypto in recommendations
   - Verify: Both interests represented

5. **Bookmark Signal Test**
   - Bookmark an episode (strong signal)
   - Observe: That topic should be emphasized
   - Compare: Bookmark vs click weighting (Option B)

6. **Exclusion Test**
   - Note an episode in recommendations
   - Click it (mark as seen)
   - Observe: Should disappear from recommendations
   - Verify: Never reappears

### 3.2 Episode Detail Page Testing

The episode detail page should display:

| Field | Display Location | Notes |
|-------|------------------|-------|
| Title | Header | Full title |
| Series Name | Subheader | With series avatar |
| Published Date | Metadata | Formatted nicely |
| Credibility Score | Score card | 1-4 scale with label |
| Insight Score | Score card | 1-4 scale with label |
| Information Score | Score card | 1-4 scale with label |
| Entertainment Score | Score card | 1-4 scale with label |
| Key Insights | Main content | Full text from critical_views |
| Categories | Tags | All major categories |
| Entities | Entity cards | Name + relevance + context |
| POV Status | Badge | Contrarian/Consensus |

**Manual Tests:**
- Click through 5+ episodes to verify all data displays
- Check that critical_views.key_insights shows when available
- Verify entities display with context
- Test episodes with null critical_views (should show fallback)

---

## 4. Evaluation Metrics

### 4.1 Embedding Quality Metrics

| Metric | Calculation | Target | Alert Threshold |
|--------|-------------|--------|-----------------|
| Intra-category similarity | Mean sim between episodes in same category | > 0.6 | < 0.4 |
| Inter-category similarity | Mean sim between episodes in different categories | < 0.5 | > 0.7 |
| Similarity distribution | Histogram of all pairwise sims | Normal, centered ~0.4 | Bimodal or extreme |

**Validation Test:**
```python
def test_embedding_clustering():
    """Episodes in same category should be more similar than different categories."""
    ai_episodes = [ep for ep in episodes if "Technology & AI" in ep.categories.major]
    crypto_episodes = [ep for ep in episodes if "Crypto & Web3" in ep.categories.major]
    
    # Intra-category similarity
    ai_sims = pairwise_similarity(ai_episodes)
    crypto_sims = pairwise_similarity(crypto_episodes)
    
    # Inter-category similarity
    cross_sims = cross_similarity(ai_episodes, crypto_episodes)
    
    assert mean(ai_sims) > mean(cross_sims)
    assert mean(crypto_sims) > mean(cross_sims)
```

### 4.2 Recommendation Quality Metrics

| Metric | Calculation | Target | Alert Threshold |
|--------|-------------|--------|-----------------|
| Avg Quality Score | Mean C+I of recommended | ≥ 6.0 | < 5.5 |
| Personalization Delta | Diff between user A and user B top 10 | ≥ 50% different | < 30% |
| Cold Start Quality | Mean C+I for cold start user | ≥ 6.5 | < 6.0 |
| Coverage | % of candidate pool appearing in any user's top 10 | ≥ 30% | < 20% |
| Freshness | Mean days old of recommended | ≤ 14 | > 21 |

### 4.3 A/B Comparison Metrics

When comparing Option A vs Option B:

| Metric | Description | How to Measure |
|--------|-------------|----------------|
| Similarity Spread | Range of similarity scores | max - min of top 10 |
| Interest Alignment | Match with stated preferences | % matching category interests |
| Recency Sensitivity | How much recent clicks affect results | Change in results after new click |
| Bookmark Impact | Difference from bookmark signal | Change in results after bookmark |

---

## 5. Test Data Requirements

### 5.1 Episode Distribution for Testing

Ensure test data includes:

| Category | Minimum Episodes | Purpose |
|----------|------------------|---------|
| Technology & AI | 50+ | Primary test category |
| Crypto & Web3 | 30+ | Secondary test category |
| Mixed categories | 20+ | Cross-category testing |
| Contrarian (has critical_views) | 20+ | POV testing |
| Low quality (C<2 or C+I<5) | 20+ | Gate testing |
| Old content (>30 days) | 50+ | Freshness testing |
| Recent content (<7 days) | 30+ | Recency testing |

### 5.2 User Personas for Testing

| Persona | Engagement History | Expected Behavior |
|---------|-------------------|-------------------|
| Cold Start | 0 engagements | Pure quality ranking |
| AI Enthusiast | 5+ AI episode clicks | AI-heavy recommendations |
| Crypto Fan | 5+ Crypto episode clicks | Crypto-heavy recommendations |
| Generalist | Mixed category clicks | Diverse recommendations |
| Power User | 20+ clicks | Stable personalization |
| Bookmark Heavy | Many bookmarks, few clicks | Bookmark topics emphasized |

---

## 6. Automated Test Suite

### 6.1 Running Tests

```bash
# Run all unit tests
pytest tests/test_recommendation.py -v

# Run integration tests
pytest tests/test_e2e.py -v

# Run embedding quality tests
python tests/validate_embeddings.py

# Run full evaluation
python tests/run_evaluation.py --report
```

### 6.2 Test File Structure

```
rec/
├── tests/
│   ├── __init__.py
│   ├── test_candidate_pool.py      # Stage A unit tests
│   ├── test_embeddings.py          # Embedding quality tests
│   ├── test_user_vector.py         # User activity vector tests
│   ├── test_similarity.py          # Cosine similarity tests
│   ├── test_e2e.py                 # End-to-end tests
│   ├── test_personalization.py     # Personalization tests
│   ├── validate_embeddings.py      # Embedding distribution check
│   └── run_evaluation.py           # Full evaluation metrics
├── mock_api/
│   ├── server.py                   # API with test endpoints
│   └── data/
│       └── test_fixtures.json      # Test data fixtures
└── prototype/
    └── src/
        └── __tests__/              # Frontend tests (optional)
```

---

## 7. Continuous Validation

### 7.1 Pre-Deployment Checklist

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Embedding quality metrics within thresholds
- [ ] Cold start test shows quality content
- [ ] Personalization test shows measurable difference
- [ ] No low-quality episodes in recommendations
- [ ] All recommended episodes are recent (≤30 days)
- [ ] Excluded episodes never appear

### 7.2 Post-Deployment Monitoring

| Check | Frequency | Action if Failed |
|-------|-----------|------------------|
| API response time | Continuous | Alert if >500ms |
| Empty results rate | Hourly | Investigate if >5% |
| Quality score mean | Daily | Alert if drops |
| Diversity check | Daily | Alert if coverage <20% |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Feb 4, 2026 | Initial testing strategy document |
