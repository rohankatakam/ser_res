# Serafis — Product Quality Framework

> *"Serafis is the intelligence layer for alternative content."*  
> — Investor Memo, Section 3

---

## The Core Thesis

Serafis exists because **alternative content** (podcasts, interviews, panels) contains the highest-signal, earliest narratives about markets—but this content is:

- Unstructured
- Unindexed by institutional tools
- 99% noise, 1% alpha

The product must solve **one meta-problem**: Transform infinite unstructured audio into **structured, defensible, institutional-grade intelligence**.

---

## What "Institutional-Grade" Means

Institutional investors (the target customer) have specific requirements that distinguish "podcast search" from "narrative intelligence":

| Requirement | Definition |
|-------------|------------|
| **Defensible** | Every insight must be auditable back to a source (speaker, timestamp, quote) |
| **Complete** | If an entity exists in the corpus, it must be discoverable (no "Walled Garden") |
| **Precise** | Top results must be high-signal, not high-frequency (no spam) |
| **Credible** | Speaker authority must weight ranking (CEO > pundit) |
| **Early** | Non-consensus ideas must be surfaced before they're priced in |

The gap between "podcast search" and "narrative intelligence" is **defined by these five requirements**.

---

## The Five Quality Dimensions

Rather than a hierarchy, Serafis quality is measured across **five interdependent dimensions**. Each dimension has a clear definition, observable current state, and measurable success criteria.

```
                    ┌─────────────────┐
                    │   DEFENSIBILITY │
                    │  (Auditability) │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────▼─────────┐    │    ┌─────────▼─────────┐
    │     COVERAGE      │    │    │    CREDIBILITY    │
    │   (Completeness)  │    │    │    (Authority)    │
    └─────────┬─────────┘    │    └─────────┬─────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────▼─────────┐    │    ┌─────────▼─────────┐
    │    RELEVANCE      │◄───┴───►│     NOVELTY       │
    │   (Precision)     │         │  (Non-Consensus)  │
    └───────────────────┘         └───────────────────┘
```

**Interdependence:**
- **Defensibility** is the foundation — without auditability, nothing else matters for institutional users
- **Coverage** and **Credibility** feed into ranking — you can't rank what you can't find, and ranking without authority is noise
- **Relevance** and **Novelty** are the output dimensions — precision (signal vs. noise) and early-signal detection (priced-in vs. alpha)

---

## Dimension 1: Defensibility (Auditability)

> *"Institutional investors require auditability. If we surface noise, they churn."*

### Definition
Every insight surfaced by Serafis must be traceable to a specific source: **who said it**, **when**, **in what context**, with a **direct quote**.

### Current State (What Exists)
| Component | Status |
|-----------|--------|
| Timestamped transcripts | ✅ Built (Transcript tab) |
| Inline citations in Ask AI | ✅ Built (citation format with timestamps) |
| Top Quotes extraction | ✅ Built (Episode Analysis) |
| Speaker attribution in quotes | ⚠️ Partial (in episode, not in search results) |

### Current Gaps
- **Search results lack defensibility** — Context snippets are paraphrased, not direct quotes
- **Ask AI answers lack speaker attribution** — "OpenAI is discussed..." but not "Sam Altman stated..."

### Success Metrics
| Metric | Description |
|--------|-------------|
| **Citation Accuracy** | % of citations that correctly match the source content |
| **Quote Fidelity** | % of Key Insights backed by direct transcript quotes |
| **Attribution Coverage** | % of claims with explicit speaker identification |

---

## Dimension 2: Coverage (Completeness)

> *"If an investor can't find a company, they churn immediately."*

### Definition
Every entity (company, person, theme) mentioned in the corpus should be discoverable—regardless of whether it's Google or a Series A startup like Etched.

### Current State (What Exists)
| Component | Status |
|-----------|--------|
| Major entity graph (Org/Person/Theme) | ✅ Built (dropdown search with n/score) |
| Per-episode entity extraction | ✅ Built (Entities tab shows all mentioned orgs) |
| RAG-based discovery (Ask AI) | ✅ Built (can find entities not in graph) |

### Current Gaps (The "Walled Garden" Problem)
- **Graph ≠ Corpus** — Etched is extracted in episode Entities (relevance=1) but doesn't appear in org dropdown
- **No fallback** — Structured search fails silently for entities below threshold
- **Threshold opacity** — Unclear what `n=X / score=Y` threshold determines dropdown inclusion

### The Surfacing Problem (Confirmed)
```
┌─────────────────────────────────────────────────────────────────┐
│  ENTITY: "Etched"                                                │
├─────────────────────────────────────────────────────────────────┤
│  Episode Entities Tab  →  ✅ Extracted (relevance=1)            │
│  Ask AI (RAG)          →  ✅ Found in transcripts               │
│  Org Search Dropdown   →  ❌ Not listed                         │
│  Org Search Results    →  ❌ Zero results                       │
└─────────────────────────────────────────────────────────────────┘

The data exists. The extraction exists. The surfacing fails.
```

### Success Metrics
| Metric | Description |
|--------|-------------|
| **Org Coverage Rate** | % of entities in episode Entities tabs that appear in org dropdown |
| **Zero-Result Rate** | % of entity queries that return zero structured results |
| **Fallback Parity** | % of Ask AI-discoverable entities also discoverable in Structured Search |

---

## Dimension 3: Credibility (Speaker Authority)

> *"Not all speakers are equal. An operator carries more weight than a pundit."*

### Definition
Speaker authority must be computed and weighted in ranking. A claim from the CEO of the company being discussed carries more weight than commentary from a generalist podcast host.

### Current State (What Exists)
| Component | Status |
|-----------|--------|
| Credibility score per episode | ✅ Built (★★★★ scale with rationale) |
| Title/role metadata for people | ✅ Built (People tab shows "CTO at Block") |
| Speaker distinction (guest vs. mentioned) | ✅ Partial (relevance score distinguishes) |

### Current Gaps
- **Credibility doesn't influence search ranking** — A ★★★★ episode ranks the same as ★★☆☆
- **No cross-episode speaker profiles** — "Sam Altman" is scattered, not unified
- **Title authority not weighted** — "CEO of OpenAI" should outrank "tech podcaster"

### The Credibility Hierarchy (To Be Defined)
```
Tier 1: Operator (CEO, CTO, Founder of the entity being discussed)
    ↓
Tier 2: Domain Expert (Industry veteran with direct experience)
    ↓
Tier 3: Informed Observer (Investor, analyst with track record)
    ↓
Tier 4: Generalist / Pundit (Commentary without domain expertise)
```

*Note: This hierarchy is a starting hypothesis. The actual weighting must be co-defined with Rohan Sharma based on what institutional users value.*

### Success Metrics
| Metric | Description |
|--------|-------------|
| **Authority Rank Correlation** | Correlation between speaker tier and result ranking |
| **Credibility Score Validity** | Expert agreement with ★★★★ ratings |
| **Operator Surfacing Rate** | % of top-5 results that feature operators (not just mention them) |

---

## Dimension 4: Relevance (Precision)

> *"The system currently rewards Recall (finding mentions) over Precision (finding insight)."*

### Definition
Top results should be high-signal, not high-frequency. A podcast that says "SaaS" 100 times in a chant is spam. A podcast that discusses SaaS unit economics in depth is signal.

### Current State (What Exists)
| Component | Status |
|-----------|--------|
| Relevance scores (0.0–1.0) | ✅ Built (search results) |
| Entity relevance (0–4) | ✅ Built (episode Entities/People tabs) |
| Key Insights extraction | ✅ Built (Episode Analysis) |
| Data Points extraction | ✅ Built (Episode Analysis) |

### Current Gaps (The "Frequency Trap")
- **Ranking is frequency-weighted** — "SaaS" search surfaces keyword spam
- **Recency bias** — Recent news outranks timeless, high-signal interviews
- **Insight extraction siloed** — Key Insights / Data Points exist per-episode but aren't searchable

### The Ranking Problem (Confirmed)
```
Query: "SaaS"
Expected: Deep-dive interview on SaaS metrics, churn, ARR
Actual: Episode with "Saas" repeated in religious chant (high n, low signal)

Query: "Apple"
Expected: Timeless interview with Steve Jobs, Palmer Luckey on hardware
Actual: Recent generic news commentary (recency bias)
```

### Success Metrics
| Metric | Description |
|--------|-------------|
| **Precision@5** | % of top 5 results judged as "high-signal" by evaluator |
| **Claim Density** | Specific claims extracted per episode (vs. keyword mentions) |
| **NDCG (Normalized DCG)** | Standard IR metric for ranking quality |

---

## Dimension 5: Novelty (Non-Consensus Detection)

> *"Evaluate to what extent a claim is non-consensus or priced-in."*  
> — Investor Memo, Sections 2, 5, 9

### Definition
The highest-value insights are **non-consensus** — ideas that haven't yet been priced into markets. Serafis should surface early signals before they become consensus.

### Current State (What Exists)
| Component | Status |
|-----------|--------|
| Critical Views extraction | ✅ Built (Episode Analysis, identifies contrarian ideas) |
| Novelty assessment | ✅ Partial (Critical Views includes "somewhat contrarian" ratings) |

### Current Gaps
- **Novelty isn't searchable** — Can't query "show me non-consensus AI takes"
- **Novelty isn't weighted in ranking** — Consensus commentary ranks equally with early signals
- **No temporal tracking** — Can't see "this idea first appeared in Jan 2024, now it's consensus"

### The Non-Consensus Opportunity
```
Investor Question: "What are the non-consensus bear cases on OpenAI?"

Ideal Output:
1. [Non-Consensus] "OpenAI will miss 2026 revenue by 40%" — Harry Stebbings, 20VC
2. [Non-Consensus] "Sam Altman will not be CEO by end of 2026" — Rob, Unsupervised Learning
3. [Consensus] "OpenAI faces compute cost challenges" — (multiple sources)

Current Output:
- Episode-level results without consensus/non-consensus tagging
```

### Success Metrics
| Metric | Description |
|--------|-------------|
| **Contrarian Precision** | % of "Critical Views" correctly identified as non-consensus |
| **Early Signal Lead Time** | Avg. time between first podcast mention and mainstream coverage |
| **Novelty Rank Boost** | Impact of novelty weighting on ranking quality |

---

## The Unified Quality Framework

These five dimensions form a **Unified Quality Framework** for evaluating Serafis performance:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SERAFIS QUALITY FRAMEWORK                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  │ DEFENSIVE-  │  │  COVERAGE   │  │ CREDIBILITY │  │  RELEVANCE  │  │   NOVELTY   │
│  │    IBILITY  │  │             │  │             │  │             │  │             │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤
│  │ Citation    │  │ Org Coverage│  │ Authority   │  │ Precision@5 │  │ Contrarian  │
│  │ Accuracy    │  │ Rate        │  │ Rank Corr.  │  │             │  │ Precision   │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤
│  │ Quote       │  │ Zero-Result │  │ Credibility │  │ Claim       │  │ Early Signal│
│  │ Fidelity    │  │ Rate        │  │ Score Valid │  │ Density     │  │ Lead Time   │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤
│  │ Attribution │  │ Fallback    │  │ Operator    │  │ NDCG        │  │ Novelty     │
│  │ Coverage    │  │ Parity      │  │ Surfacing   │  │             │  │ Rank Boost  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Trial Focus: Co-Defining Quality

The **highest-leverage trial contribution** is not fixing individual bugs — it's **co-authoring the Quality Framework** with Rohan Sharma.

### Why This Proves Cofounder/CTO Impact

| Founding Engineer | Cofounder/CTO |
|-------------------|---------------|
| "I built the Org Discovery Bridge" | "I created the framework we use to decide what to build" |
| Execution ownership | Strategic ownership |
| Fixes symptoms | Defines what "healthy" looks like |
| Ships features | Ships direction |

### The Trial Deliverable

1. **Quality Definition Workshop** — Work with Rohan to align on what each dimension means for Serafis specifically
2. **Evaluation Dataset** — Curate 50-100 test queries with expected outputs across all 5 dimensions
3. **Baseline Measurement** — Score current product against the framework
4. **Gap Prioritization** — Data-driven roadmap showing which dimension has highest ROI to fix first

### Why This Matters for the Business

- **McKinsey and hedge funds** need to trust the output → Defensibility + Credibility
- **Emerging company investors** need to find early signals → Coverage + Novelty
- **All users** need signal over noise → Relevance

The Quality Framework becomes **the language for product decisions** going forward.

---

## Summary: From Podcast Search to Narrative Intelligence

| Dimension | Question | Current State | Target State |
|-----------|----------|---------------|--------------|
| **Defensibility** | "Can I cite this?" | Citations exist, speaker attribution partial | Every insight has speaker + timestamp + quote |
| **Coverage** | "Can I find it?" | Walled Garden (graph ≠ corpus) | Universal (graph + fallback parity) |
| **Credibility** | "Who said it?" | Metadata exists, not weighted | Authority-weighted ranking |
| **Relevance** | "Is it signal?" | Frequency-biased | Insight-density ranked |
| **Novelty** | "Is it alpha?" | Extracted per-episode | Searchable + ranking boost |

The product vision is **"Institutional Narrative Intelligence."**  
The current product is a **"Podcast Search Engine."**  
The Quality Framework defines the gap — and the path to close it.
