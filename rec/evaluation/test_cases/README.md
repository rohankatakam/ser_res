# Evaluation Test Cases

> Test cases for validating the For You recommendation algorithm

**Created:** February 6, 2026  
**Updated:** February 9, 2026  
**Total Tests:** 7

---

## Test Summary

| # | Test Name | Type | Method | Profiles | Key Validation |
|---|-----------|------|--------|----------|----------------|
| 01 | Cold Start Returns Quality Content | MFT | `deterministic_llm` | 01 | Avg C ≥ 3, cold_start=true |
| 02 | Personalization Differs from Cold Start | MFT | `deterministic_llm` | 01, 02 | ≥5 different episodes |
| 03 | Quality Gates Enforce Credibility Floor | MFT | `deterministic` | All 5 | No C<2 episodes ever |
| 04 | Excluded Episodes Never Reappear | MFT | `deterministic` | 02 (modified) | Exclusions respected |
| 05 | Category Engagement → Category Recs | DIR | `deterministic_llm` | 02, 03 | ≥50% category match |
| 06 | Recency Scoring Works | DIR | `deterministic` | 01 | Both episodes in top 10, recent ranks higher |
| 07 | Bookmarks Outweigh Clicks | DIR | `deterministic_llm` | Custom | Crypto dominance in bookmark-crypto scenario |

---

## Changelog

### 2026-02-09
- **Removed Test 06 (Bookmark Weighting - Mixed Quality)**: This test used low-quality crypto episodes that correctly failed quality gates, conflating two behaviors. The test was incorrectly expecting crypto dominance when quality gates were working as designed.
- **Renumbered Test 07 → 06 (Recency Scoring)**
- **Renumbered Test 08 → 07 (Bookmark Weighting)**: Now uses high-quality episodes that pass quality gates, isolating bookmark weighting behavior.

---

## Evaluation Methods

| Method | Description | Tests | When to Use |
|--------|-------------|-------|-------------|
| `deterministic` | Pure programmatic validation | 03, 04, 06 | Numeric thresholds, functional checks |
| `deterministic_llm` | Programmatic + LLM qualitative assessment | 01, 02, 05, 07 | Semantic understanding adds value |
| `llm_only` | Pure LLM evaluation (none yet) | — | No objective metric exists |

See **EVALUATION_STRATEGY.md** for detailed guidance on choosing evaluation methods.

---

## Test Types

| Type | Description | Count |
|------|-------------|-------|
| **MFT** | Minimum Functionality Test — Basic capabilities that must work | 4 |
| **DIR** | Directional Expectation Test — Changes with expected directional effect | 3 |

---

## Running Tests

```bash
# Run all tests (deterministic checks only)
python runner.py

# Run all tests with LLM evaluation
python runner.py --with-llm

# Run specific test
python runner.py --test 05

# Run specific test with LLM
python runner.py --test 05 --with-llm --verbose

# Run only deterministic tests
python runner.py --method deterministic

# Run only tests that use LLM
python runner.py --method llm --with-llm

# Save report
python runner.py --with-llm --save
```

---

## Test-to-Parameter Mapping

When tests fail, adjust these parameters:

| Test | If Fails, Adjust |
|------|------------------|
| 01, 03 | Quality gates (credibility floor=2, combined floor=5) |
| 01 | Quality weight in cold start (60%) |
| 02, 05, 07 | Similarity weight, user vector computation |
| 04 | Stage A exclusion filter logic |
| 06 | Recency weight (15%/40%), lambda decay (0.03) |
| 07 | Bookmark weight (engagement_weights.bookmark) |

---

## Files

### JSON (Machine-Readable)
- `01_cold_start_quality.json`
- `02_personalization_differs.json`
- `03_quality_gates_credibility.json`
- `04_excluded_episodes.json`
- `05_category_personalization.json`
- `06_recency_scoring.json`
- `07_bookmark_weighting.json`

### Markdown (Human-Readable)
- `01_cold_start_quality.md`
- `02_personalization_differs.md`
- `03_quality_gates_credibility.md`
- `04_excluded_episodes.md`
- `05_category_personalization.md`
- `06_recency_scoring.md`

---

## How Professional Recommendation Engines Handle Bookmarks

The algorithm follows industry best practices for bookmark handling:

| Platform | "Bookmark" Action | Reappears in Feed? | Signal Usage |
|----------|------------------|-------------------|--------------|
| **TikTok** | Favorite/Save | No — saved for later | Heavy signal for SIMILAR content |
| **Netflix** | My List | No — already expressed interest | Boosts similar genres/actors |
| **Spotify** | Like Song | No — goes to Liked Songs | Influences Discover Weekly, Radio |
| **Serafis** | Bookmark | No — excluded from new recs | Strong signal for user vector |

**Key Behavior:**
1. Bookmarked episodes are excluded from future recommendations (already saved)
2. Bookmark signal influences user interest vector (strong interest indicator)
3. NEW recommendations must still pass quality gates
4. Low-quality bookmarked content influences vector, but new recs are quality-filtered
