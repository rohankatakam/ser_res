# Serafis — Product Pillars & Value Architecture

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

## The Four Product Pillars

### Pillar 1: Coverage (The Foundation)

> *"If an investor can't find a company, they churn immediately."*

**What it means:**  
Every entity (company, person, theme) mentioned in the corpus should be discoverable—regardless of whether it's Google or a Series A startup like Etched.

**The Current Gap:**  
- Major entities (Nvidia, Microsoft) → Rich structured results  
- Emerging entities (Etched, Omnara, CodeRabbit) → Zero results in Organization workflow, despite presence in transcript data

**The Binary Risk:**  
Either a company is in the graph (great experience) or it isn't (zero experience). There is no graceful fallback.

**Success Metric:**  
- **Org Coverage Rate**: % of entity queries that return relevant results
- **Zero-Result Rate**: Currently ~40% for Series A startups → Goal: <5%

**Strategic Importance:**  
Coverage is the **table stakes**. Without it, nothing else matters. Institutional investors expect completeness.

---

### Pillar 2: Alpha Extraction (The Moat)

> *"Alpha isn't 'Microsoft was mentioned'—it's what was claimed, by whom, with what conviction, and why should I care?"*

**What it means:**  
The output should not be a list of episodes. It should be a ranked list of **claims** with episode citations underneath.

**The Claim-First Model:**

| Component | Description |
|-----------|-------------|
| **Claim** | The specific assertion ("Microsoft committed to shielding residential power rates from data center buildout costs") |
| **Speaker** | Who said it + their role (Satya Nadella, CEO vs. random podcast host) |
| **Stance** | Bull / Bear / Neutral |
| **Evidence** | Timestamp + quote snippet (defensible, auditable) |
| **Novelty** | Is this consensus or non-consensus? Priced-in or early signal? |

**The Current State:**  
Serafis returns "episode-level relevance" (which episodes mention X). Alpha requires "claim-level relevance" (what specific claims matter).

**Success Metric:**  
- **Alpha Density**: Non-consensus claims extracted per query
- **Claim Precision**: % of extracted claims that are actually investable insights

**Strategic Importance:**  
This is what separates Serafis from "a podcast search engine." Incumbents index PDFs. Serafis extracts **narratives that move markets**.

---

### Pillar 3: Credibility Weighting (The Trust Layer)

> *"Institutional investors require auditability. If we surface noise, they churn."*

**What it means:**  
Not all speakers are equal. An operator (CEO, CTO, founder) carries more weight than a pundit. A domain expert's claim about their industry matters more than a generalist's speculation.

**The Credibility Hierarchy:**

```
Operator (CEO, CTO, Founder)
    ↓
Domain Expert (Industry Veteran, Technical Lead)
    ↓
Informed Observer (Investor, Analyst)
    ↓
Generalist / Pundit
```

**The Current State:**  
The People search shows titles (CEO of Nvidia, AI researcher) but relevance scores don't seem to weight speaker authority heavily.

**Success Metric:**  
- **Speaker Authority Score**: Weighting system for ranking claims
- **Source Confidence**: How defensible is this claim based on who said it?

**Strategic Importance:**  
McKinsey and hedge funds need **auditable** intelligence. They can't cite "some guy on a podcast." They need to cite "Satya Nadella, in his Davos interview, stated X."

---

### Pillar 4: Relevance Ranking (The Signal Filter)

> *"The system currently rewards Recall (finding mentions) over Precision (finding insight)."*

**What it means:**  
Broad queries (like "SaaS") should surface deep-dive interviews, not episodes with high keyword repetition or generic news recaps.

**The Ranking Hierarchy:**

| Signal | Priority |
|--------|----------|
| Specific, argumentative claims with evidence | Highest |
| Deep-dive interviews with operators | High |
| Industry analysis with context | Medium |
| News recaps / keyword mentions | Low |
| Keyword stuffing / spam | Filter out |

**The Current State:**  
- Relevance scores (0.6–0.9) exist but optimize for "find mentions"
- Queries for broad themes surface volume over insight
- "SaaS" searches show repetitive keyword matches

**Success Metric:**  
- **Precision@5**: Top 5 results are genuinely high-signal
- **Claim Density**: Specific claims per result, not keyword counts

**Strategic Importance:**  
This is the difference between a "search engine" and an "intelligence platform." Investors don't want 1000 results. They want 5 that matter.

---

## The Pillar Hierarchy (Prioritization)

```
┌─────────────────────────────────────────────────┐
│  COVERAGE                                        │
│  "Can I find Etched?"                            │
│  → Foundation. Without this, nothing else works. │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  ALPHA EXTRACTION                                │
│  "What did they claim about Etched?"             │
│  → Moat. This is the product differentiation.    │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  CREDIBILITY WEIGHTING                           │
│  "Who said it and should I trust them?"          │
│  → Trust. Required for institutional adoption.   │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  RELEVANCE RANKING                               │
│  "Show me the 5 that matter."                    │
│  → Polish. Separates good from great.            │
└─────────────────────────────────────────────────┘
```

---

## Trial Focus: The "Org Discovery Bridge"

Given the pillar hierarchy, the 2-week trial should focus on **Pillar 1 (Coverage)** with a foundation for **Pillar 2 (Alpha Extraction)**.

**Why Coverage First:**
- Highest asymmetric leverage (solves "Zero Result" → immediate value)
- Requires no UI changes (backend-only)
- Measurable (0% → 100% coverage for emerging orgs)
- Proves technical ownership without stepping on existing code

**The Bridge Concept:**
- User searches "Etched" → Graph lookup misses
- **Fallback**: Hit transcript/RAG index for "Etched"
- **Extract**: Canonical name, domain, sentiment
- **Return**: "Virtual" entity result that looks like a first-class org

**Phase 2 Setup (Alpha):**
- Deliver a backend API contract that can serve `{claim, speaker, proof}`
- Jason can render when ready; you build the engine behind the contract

---

## Summary: The Serafis Value Stack

| Layer | Question | Current State | Target State |
|-------|----------|---------------|--------------|
| **Coverage** | "Does it exist?" | Binary (graph hit/miss) | Universal (graph + fallback) |
| **Alpha** | "What's the claim?" | Episode-level | Claim-level |
| **Credibility** | "Who said it?" | Metadata exists | Weighted ranking |
| **Relevance** | "Is it signal?" | Volume-based | Insight-based |

The product vision is **"Institutional Narrative Intelligence."**  
The current product is a **"Podcast Search Engine."**  
The gap is the opportunity.
