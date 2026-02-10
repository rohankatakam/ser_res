# Diversity Criterion

## Overview

Evaluates if recommendation diversity matches what the user's Content Hypothesis prescribes. Diversity is context-dependent: specialists want depth within their domain, while explorers want breadth across domains.

## Type

**LLM-based** - Uses multi-LLM judges to evaluate diversity appropriateness.

## Scoring

- **Scale:** 1-10
- **Default Threshold:** 6.0
- **Pass Condition:** score >= threshold

## Evaluation Factors

1. **Specialization Ratio** - High specialization users should see depth within domain
2. **Exploration Ratio** - High exploration users should see cross-domain variety
3. **Cold Start** - New users should see maximum diversity to discover interests
4. **Series Variety** - Avoid single-source dominance in recommendations

## Scoring Guide

| Score | Meaning |
|-------|---------|
| 10 | Diversity level perfectly matches user's exploration/specialization ratio |
| 7-9 | Good diversity match with minor issues |
| 4-6 | Some mismatch in diversity expectations |
| 1-3 | Major mismatch (scattered for specialist, narrow for explorer) |

## Used By Tests

- 01_cold_start_quality (expects high diversity for cold start)
- 02_personalization_differs (expects domain-focused diversity)

## Example

| User Type | Good Diversity | Bad Diversity |
|-----------|---------------|---------------|
| AI Specialist (85%) | Multiple AI subtopics, few cross-domain | Random mix of unrelated topics |
| Explorer (70%) | AI, Crypto, Macro, Startups mix | All from one narrow topic |
| Cold Start | Broad sampling across all themes | Clustered in one area |
