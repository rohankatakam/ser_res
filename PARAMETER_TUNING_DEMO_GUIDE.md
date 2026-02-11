# Parameter Tuning Demo Guide
**Live Algorithm Tuning & Test Validation**

## Overview

This guide documents successful parameter tuning demonstrations showing **real-time algorithm behavior changes** measured through automated evaluation tests. All tests run on the **currently tuned configuration**, not defaults, with full observability of parameter diffs and config snapshots in reports.

---

## Demo 1: Personalization Strength (Test 02) ✅ VALIDATED

**Test:** `02_personalization_differs` - "Personalization Differs from Cold Start (Centroid Shift Test)"  
**Algorithm:** v1.5_diversified  
**Parameter:** `stage_b.weight_similarity` (controls personalization strength)  
**Test Type:** MFT (Model Fitness Test) with deterministic + LLM evaluation

### What This Test Measures

**Model Selection Agreement (MSA):** As a user's engagement history grows, recommendations should shift proportionally away from generic "cold start" content toward personalized content matching their interests.

**Pass Criteria:**
- ✅ At least 5 of top 10 episodes are different from cold start
- ✅ Engaged user has **higher** avg similarity_score than cold start
- ✅ Cold start flag is correctly set

### Baseline: Default Configuration

**Parameter:** `weight_similarity = 0.85` (85% weight on user-content similarity)

**Scoring Formula:**
```python
final_score = 0.85 × similarity + 0.10 × quality + 0.05 × recency
```

**Results:**
- **Test Score:** 9.1/10 ✅ PASSED
- **Episode Difference:** 8 out of 10 episodes different from cold start
- **Similarity Delta:** +0.046 (VC Partner: 0.546 vs Cold Start: 0.500)
- **Interpretation:** Strong personalization - user vector dominates scoring

**Key Observations:**
- All 7 criteria passed
- LLM judges rated hypothesis alignment at 7.9/10, relevance at 8.7/10
- Recommendations heavily skewed toward user's AI/Tech infrastructure interests
- High similarity scores indicate algorithm is matching user preferences

---

### Tuning Demo: Weaken Personalization

**Parameter Change:** `weight_similarity = 0.10` (reduce from 0.85 to 0.10)

**New Scoring Formula:**
```python
final_score = 0.10 × similarity + ~0.60 × quality + ~0.30 × recency
# (frontend auto-normalizes to sum to 1.0)
```

**Results:**
- **Test Score:** 6.2/10 ❌ FAILED
- **Episode Difference:** Only 4 out of 10 different (below 5 threshold) ❌
- **Similarity Delta:** -0.045 (VC Partner: 0.455 vs Cold Start: 0.500) ❌
  - **Negative delta!** Personalized recs score LOWER on similarity than generic cold start
- **Interpretation:** Weak personalization - quality & recency dominate, user interests ignored

**What Changed:**
- **Failed Criteria:**
  - `episode_difference`: 4/10 different (needs ≥5)
  - `similarity_increase`: Negative delta (needs positive)
- **Why It Failed:**
  - With only 10% weight on similarity, algorithm ignores user vector
  - Recommendations become generic "high quality + recent" content
  - User's specific AI/Tech interests are overridden by dataset-wide quality scores

**LLM Judge Feedback:**
> "While several recommendations align with the user's single click on AI content, the complete absence of addressing the user's stronger bookmark signals represents a significant miss."

---

### Why This Validates Parameter Tuning

#### ✅ End-to-End Data Flow Confirmed

1. **UI slider change** → Frontend state update in `ParameterSidebar.jsx`
2. **"Apply & Refresh"** → `POST /api/algorithm/config/update` 
3. **Config merged** into `state.current_algorithm.config` (runtime state)
4. **Tests run** with tuned config (not defaults)
5. **`RecommendationConfig.from_dict()`** loads tuned `weight_similarity`
6. **Scoring formula** uses tuned weights: `config.weight_similarity * sim_score`

#### ✅ Algorithm Behavior Is Correct

| Similarity Weight | Behavior | Episode Diff | Similarity Delta | Score |
|-------------------|----------|--------------|------------------|-------|
| **0.85 (High)** | Strong personalization | 8/10 different | +0.046 | 9.1/10 ✅ |
| **0.10 (Low)** | Weak personalization | 4/10 different | -0.045 | 6.2/10 ❌ |

**Interpretation:**
- High similarity weight = User interests dominate = Personalized recommendations
- Low similarity weight = Quality/recency dominate = Generic recommendations

#### ✅ Test Sensitivity Is Working

The test correctly detects when personalization is too weak by measuring:
1. **Episode overlap** - How many recommendations differ from cold start
2. **Similarity score delta** - Whether personalized recs score higher on similarity

#### ✅ Code Validation

**File:** `rec/algorithms/v1_5_diversified/recommendation_engine.py` (lines 555-559)

```python
final = (
    config.weight_similarity * sim_score +
    config.weight_quality * qual_score +
    config.weight_recency * rec_score
)
```

This directly multiplies the tuned `weight_similarity` parameter, so changes have **immediate, proportional impact** on final ranking.

---

### Conclusion: Test 02 Demo

✅ **Parameter tuning is working perfectly.** This demo proves:

1. Parameters in the UI are applied to the backend algorithm
2. Algorithm behavior changes appropriately (more/less personalization)
3. Tests run on the tuned configuration (not defaults)
4. Tuning warning banner shows modified parameters
5. Test reports include config snapshots for reproducibility

**This is a real, working parameter tuning workflow** that allows experimentation with algorithm behavior in real-time and measurement of impact using automated evaluation tests.

---

## Demo 2: Category Specialization (Test 05) ✅ VALIDATED

**Test:** `05_category_personalization` - "Category Personalization & Boundary Cross Test"  
**Algorithm:** v1.5_diversified  
**Parameter:** `stage_b.weight_similarity` (same parameter, different test angle)  
**Test Type:** DIR (Differential Response Test) with deterministic + LLM evaluation

### What This Test Measures

**Category Specialization:** Users with 80%+ category-specific engagements should receive 50%+ matching category content in their top 10 recommendations.

**Boundary Cross Quality:** Any "outside category" recommendations (the remaining 1-2 episodes) should be **contextually linked** to user interests (e.g., AI+defense-tech, crypto+regulatory policy) rather than random unrelated content.

**Pass Criteria:**
- ✅ AI/Tech Profile: At least 5 of top 10 are AI/Tech related
- ✅ Crypto Profile: At least 5 of top 10 are Crypto/Web3 related
- ✅ Outside-category episodes are "bridge content" (contextually linked)
- ✅ No completely random/unrelated content

### Baseline: Default Configuration

**Parameter:** `weight_similarity = 0.85` (85% weight on user-content similarity)

**Results:**
- **Test Score:** 8.7/10 ✅ PASSED
- **AI/Tech Profile (02):** 10/10 episodes are AI/Tech (100% category match!)
- **Crypto Profile (03):** 9/10 episodes are Crypto/Web3 (90% category match!)
- **Boundary Cross:** Both profiles show contextual bridge content
  - AI VC gets: Space-based AI infrastructure, American Dynamism/defense-tech
  - Crypto investor gets: Macro/geopolitical trends linking to crypto

**Interpretation:**
- Strong category specialization with 85% similarity weight
- Algorithm respects user's domain focus (crypto investor gets 90% crypto!)
- Outside-category content is strategically chosen (bridges, not noise)

---

### Validated Tuning Demo: Weaken Category Focus

**Parameter Change:** `weight_similarity = 0.30` (reduce from 0.85 to 0.30)

**Actual Behavior:**
- Similarity weight drops from 85% to 30%
- Quality (~60%) and recency (~10%) become dominant factors
- Recommendations shift toward "best recent content" regardless of category match

**Actual Results:**

| Profile | Category Matches (Default 0.85) | Actual (0.30) | Threshold | Pass? |
|---------|--------------------------------|---------------|-----------|-------|
| **AI/Tech VC** | 10/10 AI episodes | 10/10 AI episodes | ≥5 | ✅ PASS |
| **Crypto Investor** | 9/10 crypto episodes | **2/10 crypto episodes** | ≥5 | ❌ **FAIL** |

**Test Score:** 7.4/10 ❌ FAILED  
**Failed Criterion:** `crypto_category_match` (2/10 crypto, needs ≥5)

**Why This Happens:**
1. With 30% similarity weight, user's crypto interests become a weak signal
2. Quality-dominant formula favors dataset-wide "best" content (often AI/Tech heavy)
3. Crypto investor's specialized interest is overridden by generic quality scores
4. Test criterion `crypto_category_match` fails: "At least 5 of top 10 must be Crypto"

**Key Insight - Dataset Bias Revealed:**
> Notice the **asymmetric impact**: AI/Tech VC still gets 10/10 AI episodes even with weak personalization, but crypto investor drops from 9/10 → 2/10 (78% decrease). This reveals that our dataset is **AI-heavy**. Quality-based scoring naturally favors AI content. Without strong personalization, minority interests (crypto) get buried under majority-popular content (AI). This demonstrates why high similarity weight is critical for serving niche interests.

---

### Tuning Demo Script for Test 05

#### Step 1: Baseline (Default Config)

**Action:** Run Test 05 with `weight_similarity = 0.85`

**Talking Points:**
> "With 85% weight on similarity, our algorithm strongly specializes. The AI-focused VC partner gets 10 out of 10 AI/Tech episodes. The crypto investor gets 9 out of 10 crypto episodes—90% category match. The remaining 1 episode is a contextual bridge, linking to geopolitical trends relevant to crypto. This passes the test with 8.7/10."

**Show in UI:**
- Open Tests page
- Expand Test 05 results
- Point out: `ai_tech_matches=10/10`, `crypto_matches=9/10`
- Show LLM feedback praising category focus

---

#### Step 2: Reduce Personalization

**Action:** 
1. Open Parameter Tuning sidebar
2. Adjust `Similarity Weight` from 0.85 → 0.30
3. Click "Apply & Refresh"
4. Run Test 05 again

**Actual Results:**
- AI/Tech profile: **Stays at 10/10 AI episodes** ✅ (dataset is AI-heavy)
- Crypto profile: **Drops from 9/10 → 2/10 crypto episodes** ❌ (78% decrease!)
- Test score: 7.4/10 ❌ FAILED
- Criterion `crypto_category_match` fails (2/10, needs ≥5)

**Talking Points:**
> "I've reduced similarity weight from 85% to 30%. Watch what happens. The AI VC still gets 10 out of 10 AI episodes—our dataset is AI-heavy, so quality-based scoring naturally favors AI content. 
>
> But look at the crypto investor: they drop from 9 crypto episodes to only 2. That's a 78% decrease! The test criterion requires at least 5 crypto episodes—we're getting only 2. The test fails.
>
> This reveals an important insight: without strong personalization, minority interests get buried under majority-popular content. The crypto investor is now getting generic 'best content'—which happens to be AI-focused—instead of content matching their actual interests. This demonstrates why high similarity weight is essential for niche communities."

**Show in UI:**
- Tuning warning banner: "Testing on Tuned Algorithm (1 parameter modified)"
- Expand parameter diff: `stage_b.weight_similarity: 0.85 → 0.30 (-64.7%)`
- Point out **failed criterion**: `crypto_category_match: 2/10 (needs ≥5)` ❌
- Show red X icon next to failed criterion

---

#### Step 3: Restore Default

**Action:**
1. Click "Reset to Defaults" in sidebar
2. Click "Apply & Refresh"
3. Run Test 05 again

**Actual Results:**
- Back to 10/10 AI, 9/10 crypto
- Test passes with 8.7/10 ✅

**Talking Points:**
> "Restored to 85%. The crypto investor immediately gets 9 crypto episodes back. Category specialization returns. This proves our parameter tuning is working—and it shows the critical importance of the similarity weight for serving diverse user interests in an AI-heavy content landscape."

---

### Why This Demo Is Extremely Effective

#### ✅ Visual & Countable
You can literally count AI vs Crypto episodes in the UI results—audience can verify the claim

#### ✅ Clear Threshold
Binary pass/fail: "At least 5 of 10 must be crypto" is easy to understand

#### ✅ Dramatic Impact
Goes from 9/10 → 2/10 (78% drop, well below threshold)—clear, severe degradation

#### ✅ Reveals Dataset Bias
Asymmetric impact (AI stays 10/10, crypto drops to 2/10) reveals that dataset is AI-heavy and demonstrates why personalization is critical for minority interests

#### ✅ Real-World Relevance
Demonstrates tradeoff between personalization (user wants crypto) vs quality (system says AI is better content), and shows how majority content can drown out niche interests

#### ✅ Complements Test 02
- Test 02 shows: Personalization vs generic (same user, cold start vs engaged)
- Test 05 shows: Category specialization (different users, different interests)
- Together they demonstrate personalization from two angles

---

## Demo Flow: Complete 15-Minute Presentation

### Recommended Order

**1. Test 02: Personalization Strength** (5 minutes)
- Default (0.85) → 9.1/10, strong personalization
- Reduce (0.10) → 6.2/10, FAILS, becomes generic
- **Key Message:** "Similarity weight controls how much we respect user interests"

**2. Test 05: Category Specialization** (5 minutes)
- Default (0.85) → 8.7/10, crypto investor gets 9/10 crypto
- Reduce (0.30) → 7.4/10, FAILS, crypto investor gets 2/10 crypto (78% drop!)
- **Key Message:** "Without strong personalization, minority interests get buried under majority-popular content"

**3. Test 03: Quality Gates** (5 minutes) *(optional third demo)*
- Default (credibility_floor=2) → 10/10, no bad content
- Disable (credibility_floor=0) → FAILS, low-quality episode appears
- **Key Message:** "Quality gates are non-negotiable constraints"

---

## Technical Architecture Notes (For Q&A)

### Parameter Flow
```
ParameterSidebar.jsx → updateAlgorithmConfig()
                     ↓
         POST /api/algorithm/config/update
                     ↓
         Deep merge into state.current_algorithm.config
                     ↓
         Session cleared (old config invalid)
                     ↓
         Tests call /api/evaluation/run with current config
                     ↓
         RecommendationConfig.from_dict(tuned_config)
                     ↓
         Scoring: config.weight_similarity * sim_score
```

### Config Diff Tracking
- `GET /api/algorithm/config/diff` compares current vs defaults
- Tests page shows warning banner with modified parameters
- Test reports include full config snapshot for reproducibility

### Frontend Auto-Normalization
- `sum_to_one` constraint detected from schema
- When one weight changes, others adjust proportionally
- Keeps weights valid (sum=1.0) without backend rejection

### Computed Parameters
- Base parameters (tunable): `weight_similarity`, `weight_quality`, `weight_recency`
- Computed parameters (derived): Normalized weights, quality score range, recency half-life
- UI shows both in real-time

---

## Known Issues & Future Work

### Current Limitations
1. **Bookmark weighting test (07) not working** - Crypto episodes may not pass Stage A quality gates or have weak embeddings
2. **Cold start diversity (01) failing** - Architectural issue (needs MMR reranking), not fixable by parameter tuning
3. **LLM judge variability** - Anthropic consistently rates diversity lower than OpenAI/Gemini

### Suggested Improvements
1. Expand dataset to 10K episodes for better category coverage
2. Add MMR reranking for explicit diversity control
3. Implement human baseline collection (Spotify methodology)
4. Normalize LLM evaluation scores with calibration factors
5. Add CI/CD pipeline to run tests on every config change

---

## Conclusion

These demonstrations prove the parameter tuning infrastructure is **production-ready**:

✅ **Reliable** - Consistent, reproducible results  
✅ **Observable** - Full visibility into config changes and impacts  
✅ **Measurable** - Automated tests quantify algorithm behavior  
✅ **Transparent** - Clear warnings when testing on tuned config  
✅ **Reproducible** - Config snapshots in test reports  

**This enables data-driven algorithm development:** hypothesis → tune parameters → measure impact → iterate.

---

**Document Version:** 1.0  
**Last Updated:** February 11, 2026  
**Algorithm Version:** v1.5_diversified  
**Test Suite:** 7 tests (5 passing baseline, 2 with known issues)
