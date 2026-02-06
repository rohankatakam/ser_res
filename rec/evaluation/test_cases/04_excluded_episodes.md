# Test 04: Excluded Episodes Never Reappear

**Type:** MFT (Minimum Functionality Test)  
**Profile:** `02_vc_partner_ai_tech` (modified)

## Description
Episodes in `excluded_ids` must not appear in recommendations.

## Setup
Use Profile 02 with added exclusions:
- `ddzQwPxlELoIPRUgzaOd` — Martin Casado on the Demand Forces Behind AI
- `m5lvLRONK5dP5Nxng6c8` — Marc Andreessen's 2026 Outlook
- `n9VyjM1Fld6PyZlnrty0` — The Hidden Economics Powering AI

## Pass Criteria
| Criterion | Check |
|-----------|-------|
| Exclusions respected | None of 3 excluded IDs appear |
| Still returns results | Response has 10 valid episodes |

## If Fails, Adjust
- Stage A exclusion filter logic
