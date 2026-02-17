# Quality Criterion

## Overview

Evaluates if high-quality episodes (credibility >= 3) are being surfaced prominently. Quality is a fundamental requirement - users should see credible, insightful content.

## Type

**LLM-based** - Uses multi-LLM judges to evaluate content quality.

## Scoring

- **Scale:** 1-10
- **Default Threshold:** 6.0
- **Pass Condition:** score >= threshold

## Evaluation Factors

1. **Credibility Scores** - Are recommendations from authoritative sources?
2. **Insight Depth** - Do episodes offer substantive analysis?
3. **Quality Score** - The computed quality metric (0-1)
4. **Source Mix** - Balance of established and emerging voices

## Scoring Guide

| Score | Meaning |
|-------|---------|
| 10 | Top recommendations are all high-quality, credible sources |
| 7-9 | Mostly high-quality with 1-2 moderate entries |
| 4-6 | Mix of quality levels, some questionable sources |
| 1-3 | Low-quality content is prominent, credibility issues |

## Used By Tests

- 01_cold_start_quality
- 03_quality_gates_credibility

## Quality Thresholds

The algorithm enforces quality gates:
- **Credibility Floor:** No episode with credibility < 2
- **Combined Floor:** C + I >= 5
- **Target Average:** avg(credibility) >= 3.0 for top 10

## Example

Good quality recommendations:
- ✅ Credibility 4-5, Insight 3-5, known expert hosts
- ✅ Deep analysis, actionable takeaways

Poor quality recommendations:
- ❌ Credibility 1-2, shallow content
- ❌ Unknown sources, clickbait-style titles
