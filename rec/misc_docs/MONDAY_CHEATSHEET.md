# Monday Cheat Sheet — Recommendation Engine

## 6-Minute Walkthrough Script

**1. The Problem (30 sec)**
> "Serafis needs two interfaces: History (Jump In) and Recommendations (novel discovery). Without codebase access, I built a mock system to validate an approach."

**2. What I Built (90 sec)**
> "I extracted ~200 episodes from Serafis, built a FastAPI backend, and a React frontend to test algorithms live."

5 recommendation sections:
- 📊 Insights for You → category match + quality
- 💎 Highest Signal → global quality ranking  
- 🔥 Non-Consensus → contrarian + high credibility
- 📡 New from Shows → subscription-based
- 🌟 Trending → popularity + quality

Plus: Jump In history section with timestamps.

**3. Key Decisions (60 sec)**
> "Three design choices that differentiate from Spotify:"

1. **Quality score:** 45% insight, 40% credibility, 15% info (entertainment excluded)
2. **Credibility floor:** Episodes below 2 filtered out entirely
3. **Non-consensus section:** Dedicated space for contrarian ideas

**4. What's Next (60 sec)**
> "Once I have access:"
- Week 1: Wire to real data, instrument events
- Week 2: Improve ranking, cold start, A/B test credibility threshold
- Week 3: Session-based recs, entity tracking

**5. Close (30 sec)**
> "The goal wasn't perfection — it was a shippable baseline with clear next steps. I'm ready to integrate Monday."

---

## Quick Reference

### Quality Formula
```
quality = insight×0.45 + credibility×0.40 + info×0.15
```
Credibility floor: ≥2 required

### Exclusion Logic
- Viewed episodes ❌
- Bookmarked episodes ❌
- Not interested ❌

### Key Questions to Ask
- "Should recs include subscribed series episodes?"
- "Do we have listen duration or just visits?"
- "How should credibility floor be configured for B2B?"
- **Before debating weights, let's lock event semantics + success metrics.**

### Your Narrative
> "Given no codebase access, I created clarity and momentum from ambiguity. The algorithms are production-ready patterns; the integration is the work ahead."

---

## The 3 Monday Blocks

### Block 1: Pair Programming (45 min)
- Clarify inputs/outputs first (2-3 min)
- Start brute-force, then refactor
- Talk in checkpoints: correctness → structure → edge cases → optimize

### Block 2: Project Walkthrough (45 min)
For each project: Problem → Why it mattered → What you built → Hard tradeoff → Result → What you'd do differently

### Block 3: Trial Kickoff (45 min)
Bring:
- 3-week trial plan with milestones
- Questions: What does success look like? What autonomy do I have?
- Don't be thirsty about equity — focus on proving ownership

---

## Assumptions to Confirm (Reference)

| # | Assumption | Need |
|---|------------|------|
| 1 | "Visit" = meaningful intent | Confirm event taxonomy |
| 2 | Scores accessible in mobile backend | Confirm API |
| 3 | Subscriptions queryable | Confirm table |
| 4 | "Not interested" exists or can add | Confirm storage |
| 5 | Credibility floor ≥2 safe | Confirm business rules |
