# Average Credibility Criterion

## Overview

Computes the average credibility score of the top N recommended episodes. This is a core quality metric that ensures recommendations meet a minimum credibility standard.

## Type

**Deterministic** - Computed directly from episode data, no LLM needed.

## Scoring

- **Scale:** 0-5 (matches credibility score range)
- **Default Threshold:** 3.0
- **Pass Condition:** avg(credibility) >= threshold

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `top_n` | int | 10 | Number of episodes to evaluate |
| `threshold` | float | 3.0 | Minimum average credibility to pass |

## Calculation

```
avg_credibility = sum(episode.scores.credibility for ep in top_n) / n
passed = avg_credibility >= threshold
```

## Used By Tests

- 01_cold_start_quality
- 03_quality_gates_credibility

## Example

For top 10 episodes with credibility scores [4, 4, 3, 4, 3, 5, 4, 3, 4, 4]:
- Average: 3.8
- Threshold: 3.0
- Result: **PASS** (3.8 >= 3.0)

For top 10 episodes with credibility scores [2, 3, 2, 3, 2, 2, 3, 2, 3, 2]:
- Average: 2.4
- Threshold: 3.0
- Result: **FAIL** (2.4 < 3.0)
