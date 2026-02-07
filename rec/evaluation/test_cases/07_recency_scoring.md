# Test 07: Recency Scoring Works

**Type:** DIR (Directional Expectation Test)  
**Profile:** `01_cold_start`

## Description
Given two episodes with identical quality scores, the more recent one should rank higher due to recency decay scoring.

## Setup
Cold start formula: `final = 0.6 * quality + 0.4 * recency`

Both test episodes have identical quality (C=3, I=3 → Q=0.90), so recency is the only differentiating factor.

## Test Episode Pair
| Episode | Published | Age | C/I | Quality | Recency | Position |
|---------|-----------|-----|-----|---------|---------|----------|
| **Recent:** 4D Creation Open Beta | Feb 4, 2026 | 1d | 3/3 | 0.90 | ~0.97 | Top 5 |
| **Older:** Palmer Luckey on Hardware | Feb 2, 2026 | 3d | 3/3 | 0.90 | ~0.91 | Top 10 |

Episode IDs:
- Recent: `uJLuvlba870Dje0TDoOo`
- Older: `JEQEzGoCESXzJtBGb4Dl`

## Key Insight
With identical quality scores, the final score difference comes entirely from recency:
- Recent: 0.6 × 0.90 + 0.4 × 0.97 = **0.93**
- Older: 0.6 × 0.90 + 0.4 × 0.91 = **0.90**

## Pass Criteria
| Criterion | Check |
|-----------|-------|
| Both in top 10 | Both episodes found in cold start results |
| Recency score ordering | Recent recency_score > Older recency_score |
| Ranking reflects recency | Recent ranks higher (lower position) than Older |

## If Fails, Adjust
- Recency weight in cold start (currently 40%)
- Lambda decay (currently 0.03)
- Quality score formula

## Notes
Using episodes with identical quality ensures a clean test of recency scoring. Lambda=0.03 means each day reduces recency by ~3%.
