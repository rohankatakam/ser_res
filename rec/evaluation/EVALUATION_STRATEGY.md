# Evaluation Strategy

> Guidelines for choosing evaluation methods for recommendation system tests

**Version:** 1.0  
**Date:** February 6, 2026

---

## Evaluation Method Types

### 1. **Deterministic** (`deterministic`)

Pure programmatic validation with measurable, objective criteria.

| Characteristic | Description |
|---------------|-------------|
| **Speed** | Fast (~50ms) |
| **Cost** | Free |
| **Reproducibility** | 100% deterministic |
| **Best For** | Numeric thresholds, functional correctness, regression testing |

**Use When:**
- Criteria are purely numeric (e.g., "credibility >= 2")
- Checking functional behavior (e.g., "excluded IDs don't appear")
- Need CI/CD gates that run on every commit
- No semantic understanding required

**Examples:**
- Quality gates (C >= 2, C+I >= 5)
- Excluded episode filtering
- Recency score ordering
- API response structure validation

---

### 2. **Deterministic + LLM** (`deterministic_llm`)

Programmatic checks for pass/fail, with LLM providing qualitative assessment.

| Characteristic | Description |
|---------------|-------------|
| **Speed** | Medium (~10s with LLM) |
| **Cost** | LLM API cost |
| **Reproducibility** | Deterministic pass/fail, LLM ~95% consistent |
| **Best For** | Tests where "passing" needs semantic validation |

**Use When:**
- Have measurable criteria AND semantic nuance matters
- Want to catch edge cases where numbers pass but UX fails
- Debugging why something "feels wrong"
- Need both automated gates and qualitative insight

**Examples:**
- Cold start quality (numbers pass, but is it *actually* good content?)
- Category personalization (keyword match vs semantic relevance)
- Personalization difference (different episodes, but *relevantly* different?)

---

### 3. **LLM Only** (`llm_only`)

Pure qualitative evaluation where no objective metric exists.

| Characteristic | Description |
|---------------|-------------|
| **Speed** | Slow (~10s) |
| **Cost** | LLM API cost |
| **Reproducibility** | ~90-95% consistent |
| **Best For** | Subjective quality, user experience, edge case exploration |

**Use When:**
- No objective metric can capture the criteria
- Evaluating overall "feel" or user experience
- Exploratory testing of new features
- Comparing recommendation quality across algorithm versions

**Examples:**
- "Does this feed feel coherent?"
- "Would a VC find these recommendations useful?"
- "Is there too much repetition in themes?"
- A/B comparison: "Which algorithm version feels better?"

---

## Current Test Classification

| Test ID | Name | Method | Rationale |
|---------|------|--------|-----------|
| 01 | Cold Start Quality | `deterministic_llm` | Numbers (avg C ≥ 3) + semantic quality |
| 02 | Personalization Differs | `deterministic_llm` | Count differs + relevance validation |
| 03 | Quality Gates | `deterministic` | Pure numeric thresholds |
| 04 | Excluded Episodes | `deterministic` | Pure functional check |
| 05 | Category Personalization | `deterministic_llm` | Keyword match + semantic relevance |
| 06 | Bookmark Weighting | `deterministic_llm` | Score comparison + behavioral validation |
| 07 | Recency Scoring | `deterministic` | Pure score ordering |

---

## Adding New Tests: Decision Tree

```
                    Can the criteria be measured numerically?
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                   YES                              NO
                    │                               │
                    ▼                               ▼
        Does semantic understanding          ┌─────────────┐
        add value to validation?             │  LLM Only   │
                    │                        └─────────────┘
        ┌───────────┴───────────┐
        │                       │
       YES                      NO
        │                       │
        ▼                       ▼
┌───────────────────┐   ┌───────────────┐
│ Deterministic+LLM │   │ Deterministic │
└───────────────────┘   └───────────────┘
```

---

## Test Case JSON Schema

When creating new tests, include the `evaluation_method` field:

```json
{
  "test_id": "08_new_test",
  "name": "New Test Name",
  "type": "MFT|DIR|INV|EDGE",
  "evaluation_method": "deterministic|deterministic_llm|llm_only",
  "description": "...",
  "profiles": ["..."],
  "pass_criteria": [...],
  "llm_criteria": {
    "enabled": true,
    "focus_areas": ["relevance", "diversity", "quality"],
    "custom_prompt": null
  }
}
```

---

## Running Tests by Method

```bash
# Run all deterministic tests only (fast, for CI/CD)
python runner.py --method deterministic

# Run all tests with LLM evaluation where applicable
python runner.py --with-llm

# Run specific test with LLM
python runner.py --test 05 --with-llm

# Run LLM evaluation standalone
python llm_judge.py --profile 02_vc_partner_ai_tech --test 05_category_personalization
```

---

## Cost Considerations

| Method | Per-Test Cost | 100 Tests/Day | Notes |
|--------|---------------|---------------|-------|
| Deterministic | $0 | $0 | Run freely |
| Deterministic+LLM | ~$0.001 | ~$0.10 | Gemini Flash is cheap |
| LLM Only | ~$0.001 | ~$0.10 | Same as above |

**Recommendation:** Use LLM evaluation liberally during development, but gate CI/CD on deterministic tests only.

---

## Future Considerations

- **A/B Testing Mode**: Compare two algorithm versions with LLM as judge
- **Batch Evaluation**: Run LLM evaluation overnight on larger test suites
- **Human-in-the-Loop**: Flag low-confidence LLM evaluations for human review
- **Prompt Tuning**: Customize LLM prompts per test category
