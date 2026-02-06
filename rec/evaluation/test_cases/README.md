# Evaluation Test Cases

> Test cases for validating the For You recommendation algorithm (V1.2)

**Created:** February 6, 2026  
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
| 06 | Bookmarks Outweigh Clicks | DIR | `deterministic_llm` | Custom | Bookmarks = stronger signal |
| 07 | Recency Scoring Works | DIR | `deterministic` | 01 | Recent > older when quality similar |

---

## Evaluation Methods

| Method | Description | Tests | When to Use |
|--------|-------------|-------|-------------|
| `deterministic` | Pure programmatic validation | 03, 04, 07 | Numeric thresholds, functional checks |
| `deterministic_llm` | Programmatic + LLM qualitative assessment | 01, 02, 05, 06 | Semantic understanding adds value |
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
| 02, 05, 06 | Similarity weight (55%), user vector computation |
| 04 | Stage A exclusion filter logic |
| 06 | Bookmark weight (2.0x) |
| 07 | Recency weight (15%/40%), lambda decay (0.03) |

---

## Files

### JSON (Machine-Readable)
- `01_cold_start_quality.json`
- `02_personalization_differs.json`
- `03_quality_gates_credibility.json`
- `04_excluded_episodes.json`
- `05_category_personalization.json`
- `06_bookmark_weighting.json`
- `07_recency_scoring.json`

### Markdown (Human-Readable)
- `01_cold_start_quality.md`
- `02_personalization_differs.md`
- `03_quality_gates_credibility.md`
- `04_excluded_episodes.md`
- `05_category_personalization.md`
- `06_bookmark_weighting.md`
- `07_recency_scoring.md`

---

## Current Status (Baseline)

| Test | Deterministic | LLM | Status |
|------|--------------|-----|--------|
| 01 | ✓ Pass | ✓ Pass (5/5/5) | **PASS** |
| 02 | ✓ Pass | ✓ Pass (5/5/5) | **PASS** |
| 03 | ✓ Pass | N/A | **PASS** |
| 04 | ✓ Pass | N/A | **PASS** |
| 05 | ✓ Pass | ✓ Pass (5/4/5) | **PASS** |
| 06 | ✗ Fail | ✗ Fail | **FAIL** — Investigate bookmark weighting |
| 07 | ✗ Fail | N/A | **FAIL** — Older episode not in top 10 |

**Baseline:** 5/7 tests pass (71%)
