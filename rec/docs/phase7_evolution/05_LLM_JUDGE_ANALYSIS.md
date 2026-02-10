# LLM Judge Analysis

**Document:** 05 of 07 | Algorithm Evolution Documentation  
**Last Updated:** 2026-02-10

---

## Multi-LLM Evaluation Framework

### Overview

The Serafis evaluation framework uses three LLM providers to achieve consensus-based scoring, reducing the impact of individual model biases.

| Provider | Model | Role |
|----------|-------|------|
| OpenAI | GPT-4 | Primary judge |
| Google | Gemini | Secondary judge |
| Anthropic | Claude | Tertiary judge |

### Consensus Method

```
For each criterion:
  1. Each LLM provides 3 samples (temperature > 0)
  2. Per-model mean = average of 3 samples
  3. Consensus score = average of 3 per-model means
  4. Confidence = 1 - normalized_standard_deviation
```

---

## Individual LLM Score Patterns

### Test 01: Cold Start Quality — Diversity Criterion

| LLM | v1.0 | v1.2 | v1.3 | v1.4 | v1.5 | Pattern |
|-----|------|------|------|------|------|---------|
| OpenAI | 6.33 | 6.33 | 6.33 | 6.67 | **6.67** | Moderate, stable |
| Gemini | 7.67 | 7.67 | 7.67 | 7.67 | **7.67** | Generous, stable |
| **Anthropic** | **3.0** | **3.0** | **3.0** | **3.0** | **3.0** | **Low, invariant** |
| **Consensus** | 5.67 | 5.67 | 5.67 | 5.78 | **5.78** | Below threshold |

**Key Finding:** Anthropic consistently scores diversity at 3.0/10 regardless of version, pulling the consensus below the 7.0 pass threshold.

---

### Test 01: Cold Start Quality — Hypothesis Alignment

| LLM | v1.0 | v1.2 | v1.3 | v1.4 | v1.5 | Pattern |
|-----|------|------|------|------|------|---------|
| OpenAI | 5.67 | 5.67 | 5.67 | 5.33 | **5.33** | Critical |
| Gemini | 6.67 | 6.67 | 6.67 | 7.67 | **7.67** | Improving |
| **Anthropic** | **3.0** | **3.0** | **3.0** | **3.0** | **3.0** | **Low, invariant** |
| **Consensus** | 5.11 | 5.11 | 5.11 | 5.33 | **5.33** | Below threshold |

---

### Test 02: Personalization Differs — Diversity Criterion

| LLM | v1.0 | v1.2 | v1.3 | v1.4 | v1.5 | Pattern |
|-----|------|------|------|------|------|---------|
| OpenAI | 8.33 | 8.33 | 8.33 | 9.0 | **9.0** | High, improving |
| Gemini | 7.67 | 7.67 | 7.67 | 7.67 | **7.67** | Stable |
| Anthropic | 9.0 | 9.0 | 9.0 | 8.67 | **8.67** | High |
| **Consensus** | 8.33 | 8.33 | 8.33 | 8.45 | **8.45** | **Above threshold** |

**Key Finding:** Anthropic rates personalized diversity MUCH higher (8.67) than cold start diversity (3.0). This suggests the low cold start scores are due to specific evaluation criteria, not a general negative bias.

---

### Test 07: Bookmark Weighting — Diversity Criterion

| LLM | v1.0 | v1.2 | v1.3 | v1.4 | v1.5 | Pattern |
|-----|------|------|------|------|------|---------|
| OpenAI | 6.33 | 5.67 | 6.0 | 8.33 | **8.33** | Improving |
| Gemini | 7.67 | 7.33 | 7.67 | 4.67 | **5.33** | Volatile |
| **Anthropic** | **3.0** | **3.0** | **3.0** | **3.0** | **3.0** | **Low, invariant** |
| **Consensus** | 5.67 | 5.33 | 5.56 | 5.33 | **5.56** | Below threshold |

---

### Test 07: Bookmark Weighting — Hypothesis Alignment

| LLM | v1.0 | v1.2 | v1.3 | v1.4 | v1.5 | Pattern |
|-----|------|------|------|------|------|---------|
| OpenAI | 8.0 | 7.33 | 7.67 | 6.33 | **7.33** | Variable |
| Gemini | 9.67 | 9.33 | 9.33 | 9.0 | **9.33** | High, stable |
| Anthropic | 6.0 | 6.0 | 6.0 | 5.0 | **5.0** | Lower |
| **Consensus** | 7.89 | 7.56 | 7.67 | 6.78 | **7.22** | Marginal pass |

---

## Provider Analysis

### OpenAI GPT-4

| Characteristic | Observation |
|----------------|-------------|
| Scoring Range | 5.0 - 9.0 (broad) |
| Consistency | Moderate (σ ≈ 0.5-1.0) |
| Bias | Slightly critical on cold start |
| Strengths | Detailed reasoning, nuanced feedback |

**Sample Reasoning (Test 01 Diversity, v1.5):**
> "The slate covers multiple major themes (AI/space, startups/gaming, crypto, finance, bio) so there is cross-sector representation, but it is overweighted toward AI/Elon (multiple near-duplicate Musk items and repeated Palmer Luckey pieces), which reduces effective breadth for a true cold start probe."

---

### Google Gemini

| Characteristic | Observation |
|----------------|-------------|
| Scoring Range | 5.0 - 10.0 (generous) |
| Consistency | High (σ ≈ 0.5-1.5) |
| Bias | Generally positive |
| Strengths | Recognizes improvement attempts |

**Sample Reasoning (Test 01 Hypothesis Alignment, v1.5):**
> "The recommendations largely align with the hypothesis: they are high-quality, avoid low credibility, and feature content from AI, Crypto, and Startups. However, there's a strong emphasis on AI (6-7 out of 10 recommendations), which slightly deviates from the explicit goal to 'maximize initial diversity across major themes.'"

---

### Anthropic Claude

| Characteristic | Observation |
|----------------|-------------|
| Scoring Range | 3.0 - 9.0 (polarized) |
| Consistency | **Very high** (σ = 0.0 on many criteria) |
| Bias | **Strict on cold start diversity** |
| Strengths | Consistent standards |

**Sample Reasoning (Test 01 Diversity, v1.5):**
> "The recommendations are heavily skewed toward AI/Tech and Startups, with Crypto, Macro, and other themes underrepresented. The first two items are near-duplicates (Elon Musk/AI). This does not maximize initial diversity as specified in the hypothesis."

**Notable Pattern:** Anthropic gives exactly 3.0 on cold start diversity across ALL versions with zero variance. This suggests either:
1. The cold start output genuinely fails Anthropic's diversity standards
2. Anthropic's evaluation is more literal/strict about the "maximize diversity" requirement
3. There may be a systematic issue with how the prompt is interpreted

---

## Disagreement Analysis

### Highest Disagreement (std > 2.0)

| Test | Criterion | OpenAI | Gemini | Anthropic | Spread |
|------|-----------|--------|--------|-----------|--------|
| 01 | diversity | 6.67 | 7.67 | 3.0 | **4.67** |
| 01 | hypothesis_alignment | 5.33 | 7.67 | 3.0 | **4.67** |
| 07 | diversity | 8.33 | 5.33 | 3.0 | **5.33** |

### Lowest Disagreement (std < 0.5)

| Test | Criterion | OpenAI | Gemini | Anthropic | Spread |
|------|-----------|--------|--------|-----------|--------|
| 02 | quality | 8.89 | 8.89 | 8.89 | **0.0** |
| 05 | quality | 9.0 | 9.0 | 9.0 | **0.0** |
| 03 | all criteria | 10.0 | 10.0 | 10.0 | **0.0** |

**Insight:** LLMs agree on quality and deterministic-adjacent criteria but disagree significantly on diversity assessments.

---

## Confidence Scores

| Test | v1.0 | v1.2 | v1.3 | v1.4 | v1.5 |
|------|------|------|------|------|------|
| 01_cold_start | 0.86 | 0.86 | 0.87 | 0.87 | 0.86 |
| 02_personalization | 0.89 | 0.88 | 0.88 | 0.88 | 0.88 |
| 03_quality_gates | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| 04_excluded | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| 05_category | 0.89 | 0.86 | 0.89 | 0.89 | 0.89 |
| 06_recency | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| 07_bookmark | 0.88 | 0.88 | 0.88 | 0.83 | 0.88 |
| **Overall** | 0.93 | 0.93 | 0.93 | 0.94 | **0.95** |

**Interpretation:**
- 1.0 = Perfect agreement (deterministic tests)
- 0.95+ = Very high confidence
- 0.85-0.95 = Good confidence
- < 0.85 = Notable disagreement

---

## Recommendations for Evaluation Infrastructure

### Short-Term (v1.6)

1. **Investigate Anthropic's Cold Start Scores**
   - Run isolated tests with Anthropic only
   - Compare prompt interpretation vs other models
   - Consider prompt refinement for diversity criteria

2. **Add Score Normalization**
   - Calibrate each model's typical range
   - Apply z-score normalization before consensus
   - Reduces impact of systematically low/high models

### Medium-Term

3. **Weighted Consensus**
   - Weight models by historical accuracy (if ground truth available)
   - Or weight by inter-model agreement

4. **Prompt Engineering**
   - Make "diversity" criteria more explicit
   - Provide rubric with example scores
   - Reduce interpretation variance

### Long-Term

5. **Human Baseline**
   - Collect human ratings for calibration
   - Identify which LLM best matches human judgment
   - Use as primary judge

---

## Raw Data Reference

### Evaluation Reports

| Version | Report Path |
|---------|-------------|
| v1.0 | `reports/20260210_v1_0_default__eval_909_feb2026.json` |
| v1.2 | `reports/20260210_v1_2_blended__eval_909_feb2026.json` |
| v1.3 | `reports/20260210_v1_3_tuned__eval_909_feb2026.json` |
| v1.4 | `reports/20260210_v1_4_optimized__eval_909_feb2026.json` |
| v1.5 | `reports/20260210_v1_5_diversified__eval_909_feb2026.json` |

### Extracting Individual Model Scores

```python
import json

with open("reports/20260210_v1_5_diversified__eval_909_feb2026.json") as f:
    report = json.load(f)

for result in report["results"]:
    for llm_result in result.get("llm_results", []):
        print(f"{result['test_id']} / {llm_result['criterion_id']}")
        for model, data in llm_result["model_results"].items():
            print(f"  {model}: {data['mean_score']} (std={data['std']})")
```

---

## Related Documents

- [04_PERFORMANCE_COMPARISON.md](./04_PERFORMANCE_COMPARISON.md) - Aggregate scores
- [07_LESSONS_LEARNED.md](./07_LESSONS_LEARNED.md) - Recommendations for improvement
