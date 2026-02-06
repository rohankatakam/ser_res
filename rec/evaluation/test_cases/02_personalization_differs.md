# Test 02: Personalization Differs from Cold Start

**Type:** MFT (Minimum Functionality Test)  
**Profiles:** `01_cold_start`, `02_vc_partner_ai_tech`

## Description
Engaged user's top 10 should be measurably different from cold start top 10.

## Setup
Run two API calls:
1. **Cold Start** — 0 engagements
2. **VC Partner** — 10 AI/tech engagements from profile

## Pass Criteria
| Criterion | Check |
|-----------|-------|
| Episode difference | ≥5 different episodes between cold start and VC |
| Similarity increase | VC has higher avg similarity_score |
| Cold start flag | VC response has `cold_start: false` |

## If Fails, Adjust
- Similarity weight (currently 55%)
- User vector computation (engagement limit)
