# Hypothesis Alignment Criterion

## Overview

Evaluates how well recommendations align with the explicit Content Hypothesis for the test scenario. This is a key metric for testing whether the algorithm correctly interprets user signals (clicks, bookmarks, etc.).

## Type

**LLM-based** - Uses multi-LLM judges to evaluate hypothesis alignment.

## Scoring

- **Scale:** 1-10
- **Default Threshold:** 6.0
- **Pass Condition:** score >= threshold

## Evaluation Factors

1. **Content Hypothesis Match** - Do recommendations reflect the stated hypothesis?
2. **Signal Interpretation** - Are engagement signals (bookmarks > clicks) correctly weighted?
3. **Category Dominance** - Does the expected category dominate recommendations?
4. **Preference Boundaries** - Are stated boundaries respected?

## Scoring Guide

| Score | Meaning |
|-------|---------|
| 10 | Recommendations demonstrate clear understanding of user's content preferences |
| 7-9 | Strong alignment with hypothesis, minor deviations |
| 4-6 | Partial alignment with room for improvement |
| 1-3 | Recommendations seem to ignore the Content Hypothesis entirely |

## Used By Tests

- 05_category_personalization
- 07_bookmark_weighting

## Content Hypothesis Components

A Content Hypothesis typically includes:
- **Specialization %:** How focused the user is (e.g., "85% AI/Tech")
- **Exploration %:** How much variety they want (e.g., "15% cross-domain")
- **Curiosity Level:** Low/Moderate/High for cross-disciplinary content
- **Specific Interests:** Named topics, series, or themes

## Example

For Test 07 (Bookmark Weighting):
- **Hypothesis:** "User bookmarks crypto content → crypto should dominate recommendations"
- **Good Alignment:** 7+ crypto episodes in top 10
- **Poor Alignment:** < 5 crypto episodes, AI content dominates despite click-only engagement
