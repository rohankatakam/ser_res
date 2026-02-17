# Serafis Evaluation Framework

> Systematic testing and evaluation for the "For You" recommendation algorithm

**Version:** 1.0  
**Date:** February 6, 2026

---

## Overview

This framework provides:
1. **User Profiles** — Synthetic users with defined engagement histories
2. **Test Cases** — Behavioral tests validating algorithm behavior
3. **Test Runner** — Automated execution against the API
4. **Metrics** — Quantitative measurement (Precision, Diversity, Coverage)
5. **LLM Judge** — Qualitative evaluation using Claude

---

## Quick Start

### 1. Start the API Server

From the project root:

```bash
python -m uvicorn server.server:app --reload --port 8000
# Or: docker-compose up -d backend
```

### 2. Run All Tests

```bash
cd evaluation
python runner.py
```

### 3. Run with Verbose Output

```bash
python runner.py --verbose
```

### 4. Run Specific Test

```bash
python runner.py --test 01
python runner.py --test 05_category_personalization
```

### 5. Save Report

```bash
python runner.py --save
```

---

## Directory Structure

```
evaluation/
├── README.md                    # This file
├── DATASET_SPEC.md              # Dataset specification
├── runner.py                    # Main test runner
├── metrics.py                   # Quantitative metrics
├── llm_judge.py                 # LLM-based evaluation
├── profiles/                    # User engagement profiles
│   ├── 01_cold_start.json/md
│   ├── 02_vc_partner_ai_tech.json/md
│   ├── 03_crypto_web3_investor.json/md
│   ├── 04_generalist_multi_theme.json/md
│   └── 05_startup_founder_operator.json/md
├── test_cases/                  # Test case definitions
│   ├── README.md
│   ├── 01_cold_start_quality.json/md
│   ├── 02_personalization_differs.json/md
│   ├── 03_quality_gates_credibility.json/md
│   ├── 04_excluded_episodes.json/md
│   ├── 05_category_personalization.json/md
│   ├── 06_recency_scoring.json/md
│   └── 07_bookmark_weighting.json
├── reports/                     # Test reports (generated)
└── data/raw/                    # Raw dataset files
```

---

## User Profiles

| ID | Name | Duration | Engagements | Purpose |
|----|------|----------|-------------|---------|
| 01 | Cold Start | 0 days | 0 | Test quality-only ranking |
| 02 | VC Partner — AI/Tech | 1 week | 10 | Test AI personalization |
| 03 | Crypto/Web3 Investor | 1 week | 8 | Test single-category focus |
| 04 | Generalist Multi-Theme | 2 weeks | 14 | Test diversity handling |
| 05 | Startup Founder | 1 day | 4 | Test warm start behavior |

---

## Test Cases

| ID | Name | Type | Key Validation |
|----|------|------|----------------|
| 01 | Cold Start Returns Quality | MFT | Avg C ≥ 3, cold_start=true |
| 02 | Personalization Differs | MFT | ≥5 different episodes |
| 03 | Quality Gates Credibility | MFT | No C<2 episodes ever |
| 04 | Excluded Episodes | MFT | Exclusions respected |
| 05 | Category Personalization | DIR | ≥50% category match |
| 06 | Recency Scoring | DIR | Recent > older |
| 07 | Bookmark Weighting | DIR | Bookmarks > clicks |

**Test Types:**
- **MFT** = Minimum Functionality Test (must pass)
- **DIR** = Directional Expectation Test (expected behavior)

---

## Metrics

The `metrics.py` module computes:

| Metric | Description |
|--------|-------------|
| `avg_similarity` | Average similarity score of top 10 |
| `avg_quality` | Average quality score of top 10 |
| `avg_recency` | Average recency score of top 10 |
| `series_diversity` | Entropy-based diversity within list |
| `unique_series` | Number of unique series in top 10 |
| `avg_age_days` | Average age of recommended episodes |

### Usage

```python
from metrics import compute_all_metrics, format_metrics_report

response = api.call(...)
metrics = compute_all_metrics(response)
print(format_metrics_report(metrics))
```

---

## LLM Judge

The `llm_judge.py` module uses Gemini to evaluate recommendations qualitatively.

### Requirements

```bash
pip install google-generativeai
export GEMINI_API_KEY=your_key_here  # Optional, uses default if not set
```

### Usage

```python
from llm_judge import evaluate_recommendations

result = evaluate_recommendations(profile, response, test_case, use_llm=True)
print(result["llm_evaluation"])
```

### Evaluation Criteria

| Criterion | Scale | Description |
|-----------|-------|-------------|
| Relevance | 1-5 | How relevant to user interests |
| Diversity | 1-5 | Appropriate variety |
| Quality | 1-5 | High-quality content surfaced |
| Test Pass | bool | Specific test case passed |

---

## Test-to-Parameter Mapping

When tests fail, use this guide to adjust parameters:

| Test | If Fails, Adjust |
|------|------------------|
| 01, 03 | Quality gates (credibility_floor, combined_floor) |
| 01 | Cold start quality weight (60%) |
| 02, 05, 07 | Similarity weight, user vector computation |
| 04 | Exclusion filter logic |
| 06 | Recency weight (15%/40%), lambda (0.03) |
| 07 | Bookmark weight (engagement_weights.bookmark) |

---

## Adding New Tests

### 1. Create Test Case JSON

```json
{
  "test_id": "08_new_test",
  "name": "New Test Name",
  "type": "MFT",
  "description": "What this test validates",
  "profiles": ["profile_ids"],
  "pass_criteria": [
    {"id": "criterion_1", "description": "...", "check": "..."}
  ],
  "if_fails_adjust": ["parameter1", "parameter2"]
}
```

### 2. Add Validator Function

In `runner.py`, add:

```python
def validate_new_test(response: Dict, test_case: Dict) -> TestResult:
    result = TestResult("08_new_test", test_case["name"])
    # Add validation logic
    return result
```

### 3. Register in `run_test()`

```python
elif test_id == "08_new_test":
    # Call validator
```

---

## Iteration Workflow

1. **Run tests** → `python runner.py --verbose`
2. **Identify failures** → Check which criteria failed
3. **Consult mapping** → See test-to-parameter mapping
4. **Adjust parameters** → In `recommendation_engine.py`
5. **Re-run tests** → Verify fix
6. **Track metrics** → Save reports with `--save`

---

## Future Improvements

- [ ] Add more edge case tests (heavy exclusions, extreme profiles)
- [ ] Add A/B test simulation
- [ ] Add regression test suite
- [ ] Integrate with CI/CD
- [ ] Add visual report generation
