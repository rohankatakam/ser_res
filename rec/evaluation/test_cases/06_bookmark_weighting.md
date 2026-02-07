# Test 06: Bookmarks Outweigh Clicks in Mixed History

**Type:** DIR (Directional Expectation Test)  
**Profile:** Custom variants

## Description
Within a mixed engagement history, bookmarked episodes contribute 2x more to the user vector than clicked episodes. This test validates that the engagement type weights correctly influence which topic dominates recommendations.

## Key Insight
Engagement weights differentiate **within a mixed history** — comparing how different engagement types on different topics compete for influence on the user vector.

## Setup
Both scenarios use the same 3 episodes (1 AI, 2 Crypto) but with different engagement type distributions:

**Scenario A — Bookmark AI + Click Crypto:**
| Episode | Category | Type | Weight |
|---------|----------|------|--------|
| Martin Casado on AI | AI/Tech | bookmark | 2.0 |
| Bits + Bips: Bitcoin Is Deeply Oversold | Crypto | click | 1.0 |
| The Chopping Block: Market Meltdown | Crypto | click | 1.0 |

→ AI influence: 2.0 / 4.0 = **50%**

**Scenario B — Click AI + Bookmark Crypto:**
| Episode | Category | Type | Weight |
|---------|----------|------|--------|
| Martin Casado on AI | AI/Tech | click | 1.0 |
| Bits + Bips: Bitcoin Is Deeply Oversold | Crypto | bookmark | 2.0 |
| The Chopping Block: Market Meltdown | Crypto | bookmark | 2.0 |

→ AI influence: 1.0 / 5.0 = **20%**

## Pass Criteria
| Criterion | Check |
|-----------|-------|
| Different results | At least 2 different episodes in top 10 between scenarios |
| Crypto dominance in B | Scenario B has more crypto episodes in top 10 than Scenario A |

## If Fails, Adjust
- Bookmark weight (currently 2.0x)
- User vector limit (currently 10)
