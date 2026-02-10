# Crypto Episode Count Criterion

## Overview

Counts the number of crypto/web3 related episodes in the top N recommendations. Used to verify category personalization for crypto-focused users and to test bookmark weighting effects.

## Type

**Deterministic** - Computed via keyword matching, no LLM needed.

## Scoring

- **Scale:** 0-10 (count of matching episodes)
- **Default Threshold:** 5
- **Pass Condition:** crypto_count >= threshold

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `top_n` | int | 10 | Number of episodes to evaluate |
| `threshold` | int | 5 | Minimum crypto episodes to pass |
| `keywords` | list | (see below) | Keywords to match |

### Default Keywords

```python
["crypto", "bitcoin", "ethereum", "web3", "blockchain", 
 "defi", "btc", "eth", "stablecoin", "nft", "token",
 "bankless", "unchained", "coinbase", "binance"]
```

## Calculation

For each episode in top N:
1. Combine title + key_insight + series_name
2. Check if any keyword appears in combined text
3. Count matching episodes

## Used By Tests

- 05_category_personalization (crypto profile should get 5+ crypto episodes)
- 07_bookmark_weighting (scenario B should have more crypto than scenario A)

## Example

For a crypto-focused user's recommendations:

| # | Title | Match |
|---|-------|-------|
| 1 | Bitcoin ETF Analysis | ✅ "bitcoin" |
| 2 | Ethereum 2.0 Deep Dive | ✅ "ethereum" |
| 3 | AI in Healthcare | ❌ |
| 4 | DeFi Yield Strategies | ✅ "defi" |
| 5 | Startup Fundraising | ❌ |
| 6 | Web3 Gaming Future | ✅ "web3" |
| 7 | Macro Market Outlook | ❌ |
| 8 | Crypto Regulation Update | ✅ "crypto" |
| 9 | VC Portfolio Strategy | ❌ |
| 10 | Stablecoin Mechanics | ✅ "stablecoin" |

- Count: 6/10
- Threshold: 5
- Result: **PASS** (6 >= 5)
