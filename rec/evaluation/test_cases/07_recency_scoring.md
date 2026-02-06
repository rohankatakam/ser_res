# Test 07: Recency Scoring Works

**Type:** DIR (Directional Expectation Test)  
**Profile:** `01_cold_start`

## Description
Given two similar-quality episodes, the more recent one should rank higher.

## Setup
Cold start (quality 60% + recency 40%, no similarity).

## Test Episode Pair
| Episode | Published | C/I | Quality | Expected Recency |
|---------|-----------|-----|---------|------------------|
| **Recent:** Elon Musk on Space GPUs | Feb 5, 2026 | 4/4 | 1.0 | ~0.97 (1 day) |
| **Older:** How Marc Andreessen Uses AI | Nov 25, 2025 | 4/3 | 0.9 | ~0.11 (72 days) |

Episode IDs:
- Recent: `10FJ6iMqTrV0LJul40zA`
- Older: `azcjy2HqnbPneTMU5Ylp`

## Pass Criteria
| Criterion | Check |
|-----------|-------|
| Recency score ordering | Recent recency_score > Older recency_score |
| Ranking reflects recency | Recent ranks higher than Older |
| Final score difference | Recent final_score > Older final_score |

## If Fails, Adjust
- Recency weight (currently 15% warm, 40% cold)
- Lambda decay (currently 0.03)
- Freshness window (currently 90 days)

## Notes
Lambda=0.03 gives ~23 day half-life. At 72 days (~3 half-lives), recency_score ≈ 0.11.
