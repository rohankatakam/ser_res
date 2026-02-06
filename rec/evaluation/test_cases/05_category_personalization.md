# Test 05: Category Engagement → Category Recommendations

**Type:** DIR (Directional Expectation Test)  
**Profiles:** `02_vc_partner_ai_tech`, `03_crypto_web3_investor`

## Description
User with category-specific engagements should see matching category content.

## Setup
Run two scenarios:
1. **AI/Tech Focus** — Profile 02 (10 AI engagements)
2. **Crypto Focus** — Profile 03 (8 crypto engagements)

## Category Detection Keywords

**AI/Tech:**
- Series: a16z, AI, No Priors, Latent Space, Sourcery
- Content: AI, artificial intelligence, machine learning, OpenAI, Anthropic

**Crypto/Web3:**
- Series: Bankless, Unchained, web3, 0xResearch
- Content: crypto, Bitcoin, Ethereum, DeFi, blockchain, stablecoin

## Pass Criteria
| Criterion | Check |
|-----------|-------|
| AI/Tech match | Profile 02: ≥5 of top 10 are AI/Tech |
| Crypto match | Profile 03: ≥5 of top 10 are Crypto |

## If Fails, Adjust
- Similarity weight (currently 55%)
- User vector computation
- Embedding quality
