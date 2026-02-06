# Test 06: Bookmarks Outweigh Clicks

**Type:** DIR (Directional Expectation Test)  
**Profile:** Custom variants

## Description
Bookmarks should have stronger influence than clicks (2x weight).

## Setup
Two scenarios with same 3 AI/tech episodes, different engagement types:

**Scenario A (Bookmarks):**
| Episode | Type |
|---------|------|
| Martin Casado on the Demand Forces Behind AI | bookmark |
| The Hidden Economics Powering AI | bookmark |
| Marc Andreessen's 2026 Outlook | bookmark |

**Scenario B (Clicks):**
| Episode | Type |
|---------|------|
| Martin Casado on the Demand Forces Behind AI | click |
| The Hidden Economics Powering AI | click |
| Marc Andreessen's 2026 Outlook | click |

## Pass Criteria
| Criterion | Check |
|-----------|-------|
| Higher similarity | Scenario A avg similarity_score > Scenario B |
| More AI content | OR Scenario A has ≥ AI episodes in top 5 |

## If Fails, Adjust
- Bookmark weight (currently 2.0x)
- User vector weighted mean computation
