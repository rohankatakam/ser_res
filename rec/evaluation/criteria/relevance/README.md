# Relevance Criterion

## Overview

Evaluates if recommendations match the user's content hypothesis and engagement patterns. This is a core personalization metric that measures how well the algorithm understands and serves user interests.

## Type

**LLM-based** - Uses multi-LLM judges to evaluate recommendation relevance.

## Scoring

- **Scale:** 1-10
- **Default Threshold:** 6.0
- **Pass Condition:** score >= threshold

## Evaluation Factors

1. **Content Hypothesis Alignment** - Do recommendations match the user's stated content preferences?
2. **Engagement Pattern Match** - Are recommendations similar to content the user has engaged with?
3. **Specialization vs Exploration** - Does the mix match the user's exploration/specialization ratio?
4. **Cross-Disciplinary Curiosity** - For explorers, is there appropriate cross-domain content?

## Scoring Guide

| Score | Meaning |
|-------|---------|
| 10 | Recommendations perfectly match the content hypothesis |
| 7-9 | Strong alignment with minor gaps |
| 4-6 | Partial alignment, some content doesn't fit |
| 1-3 | Recommendations conflict with user preferences |

## Used By Tests

- 01_cold_start_quality
- 02_personalization_differs
- 05_category_personalization

## Example

For a user with AI/Tech focus (85% specialization), relevant recommendations would be:
- ✅ AI research discussions, ML applications, tech industry analysis
- ❌ Unrelated macro economics, random lifestyle content
