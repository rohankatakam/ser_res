# Test 01: Cold Start Returns Quality Content

**Type:** MFT (Minimum Functionality Test)  
**Profile:** `01_cold_start`

## Description
With 0 engagements, top 10 should be dominated by high-quality episodes. API returns `cold_start: true`.

## Setup
- Empty engagements array
- Empty excluded_ids array

## Pass Criteria
| Criterion | Check |
|-----------|-------|
| Cold start flag | `response.cold_start === true` |
| Average credibility | Avg of top 10 ≥ 3.0 |
| Minimum credibility | All top 10 have C ≥ 2 |
| Top quality scores | Top 3 have quality_score ≥ 0.7 |

## If Fails, Adjust
- Quality weight in cold start (currently 60%)
- Credibility floor (currently 2)
