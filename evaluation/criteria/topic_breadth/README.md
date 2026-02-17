# Topic Breadth Criterion

## Overview

Evaluates if recommendations span multiple major themes to probe user interests. This is especially important for cold start users where the algorithm should maximize diversity to discover preferences.

## Type

**LLM-based** - Uses multi-LLM judges to evaluate topic coverage.

## Scoring

- **Scale:** 1-10
- **Default Threshold:** 6.0
- **Pass Condition:** score >= threshold

## Major Themes

The content universe includes these major themes:

| Theme | Keywords |
|-------|----------|
| AI/Tech | AI, machine learning, OpenAI, Anthropic, GPT, LLM, No Priors, Latent Space |
| Crypto/Web3 | Bitcoin, Ethereum, DeFi, blockchain, stablecoin, Bankless, Unchained |
| Macro/Markets | Fed, economy, credit, rates, Goldman, Bloomberg, macro |
| Startups/Founders | Founder, startup, growth, product, Series A, Lenny's, In Depth |
| Venture/PE | VC, venture, fund, portfolio, 20VC, Capital Allocators |

## Scoring Guide

| Score | Themes Represented |
|-------|-------------------|
| 10 | All 5 major themes with good balance |
| 8-9 | 4 themes represented well |
| 6-7 | 3 themes represented |
| 4-5 | Only 2 themes |
| 1-3 | Dominated by single theme |

## Used By Tests

- 01_cold_start_quality

## Example

For a cold start user (no engagements):

**Good Topic Breadth (Score 9):**
1. AI research episode (AI/Tech)
2. Bitcoin analysis (Crypto)
3. Fed policy discussion (Macro)
4. Founder interview (Startups)
5. VC strategy (Venture)
6. ML applications (AI/Tech)
7. DeFi deep dive (Crypto)
8. Market outlook (Macro)
9. Growth tactics (Startups)
10. Fund management (Venture)

**Poor Topic Breadth (Score 3):**
1-8: All AI/Tech episodes
9-10: Two random crypto episodes
