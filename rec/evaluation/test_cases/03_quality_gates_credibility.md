# Test 03: Quality Gates Enforce Credibility Floor

**Type:** MFT (Minimum Functionality Test)  
**Profiles:** All 5 profiles

## Description
No episode with credibility < 2 should ever appear in recommendations.

## Setup
Run API calls with each of the 5 profiles.

## Known Low-Credibility Episodes (Should NEVER appear)
| ID | Title | C/I |
|----|-------|-----|
| `LexVsfaBFuk0MWokZOhY` | #411 Tortured Into Greatness: Andre Agassi | 1/2 |

## Pass Criteria
| Criterion | Check |
|-----------|-------|
| Credibility floor | No episode with C < 2 in any response |
| Combined floor | All episodes have C + I ≥ 5 |
| Known bad excluded | `LexVsfaBFuk0MWokZOhY` never appears |

## If Fails, Adjust
- Stage A credibility floor (currently 2)
- Stage A combined floor (currently 5)
