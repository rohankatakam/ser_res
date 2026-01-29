# Serafis Recommendation Engine — Technical Specification

> *Design document for the research intelligence recommendation system powering the Serafis mobile app.*

**Date:** January 29, 2026  
**Author:** Rohan Katakam  
**Status:** Draft  
**Stakeholder:** Rohan Sharma (CEO)

---

## 1. Framing

### 1.1 What Serafis Is

**Serafis is a research intelligence tool, not a podcast app.**

- The podcast content is the **data source**, not the product category
- Users have **professional/financial motivations**, not entertainment motivations
- Recommendations should surface **insights relevant to work**, not "podcasts to enjoy"

### 1.2 Who the User Is

| Segment | Examples | True Motivation | Job to Be Done |
|---------|----------|-----------------|----------------|
| **Institutional** | HF/PE/VC analyst, McKinsey consultant | Alpha generation, professional performance | "Find what experts say about [company] for my memo" |
| **Prosumer** | RIA, family office, crypto trader | Make money, be early to trends | "Know what smart people think before it's consensus" |
| **Operator** | Founder, VP Strategy, Corp Dev | Strategic advantage, career growth | "Understand where my market is going" |

### 1.3 Why They Choose Serafis Over Spotify/Apple

| Need | Spotify/Apple | Serafis |
|------|---------------|---------|
| Search by company mentioned | ❌ | ✅ |
| Search by person/speaker | ❌ | ✅ |
| Quality scoring (Insight, Credibility) | ❌ | ✅ |
| Claim/insight extraction | ❌ | ✅ |
| Non-consensus idea detection | ❌ | ✅ |
| Professional research workflow | ❌ | ✅ |

### 1.4 Key Differentiator

> **Spotify/Apple optimize for engagement. Serafis optimizes for decision usefulness.**

---

## 2. Data Schema

### 2.1 User Signals

| Signal | Fields | Use |
|--------|--------|-----|
| **Activity** | `entity_type`, `entity_id`, `timestamp` | Implicit interest signal |
| **Bookmarks** | `entity_type`, `entity_id`, `timestamp` | Explicit save signal |
| **Subscriptions** | `series_id`, `timestamp` | Series affinity |
| **Research Profile** | `role`, `sectors`, `tracked_companies`, `tracked_people` | Core personalization |
| **Not Interested** | `episode_id`, `timestamp` | Negative signal |

### 2.2 Research Profile (New)

Captures user's professional context for research-oriented recommendations:

```python
class ResearchProfile:
    role: str                    # "investor", "analyst", "operator", "prosumer"
    sectors: List[str]           # ["AI", "Crypto", "Fintech", ...]
    tracked_companies: List[str] # ["OpenAI", "Anthropic", "Stripe", ...]
    tracked_people: List[str]    # ["Sam Altman", "Jensen Huang", ...]
```

### 2.3 Content Metadata

| Field | Scope | Description |
|-------|-------|-------------|
| `insight_score` | Episode | Novelty and depth of ideas (1-4) |
| `credibility_score` | Episode | Speaker authority (1-4) |
| `information_score` | Episode | Data density (1-4) |
| `categories` | Episode | Major themes (Technology & AI, Crypto, etc.) |
| `entities` | Episode | Companies mentioned with relevance scores |
| `people` | Episode | People mentioned with titles and relevance |
| `critical_views` | Episode | Non-consensus idea flags |
| `embedding` | Episode | Transcript embedding for similarity |

---

## 3. Onboarding: Build a Research Profile

### 3.1 Flow

Unlike Spotify ("What genres do you like?"), Serafis asks about professional context:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  TELL US ABOUT YOUR RESEARCH FOCUS                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  What best describes your role?                                          │
│  ○ Investor (VC / PE / HF / Public Markets)                              │
│  ○ Analyst / Consultant                                                  │
│  ○ Operator / Founder / Executive                                        │
│  ○ Individual Investor / Prosumer                                        │
│                                                                          │
│  What sectors do you focus on? (select all)                              │
│  ☐ AI & Machine Learning        ☐ Enterprise SaaS                        │
│  ☐ Crypto & Web3                ☐ Consumer & Retail                      │
│  ☐ Fintech & Payments           ☐ Healthcare & Biotech                   │
│  ☐ Public Markets               ☐ Energy & Climate                       │
│                                                                          │
│  What companies are you tracking?                                        │
│  [OpenAI, Anthropic, Stripe...]                      (entity autocomplete)│
│                                                                          │
│  What people do you follow?                                              │
│  [Sam Altman, Jensen Huang...]                       (person autocomplete)│
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Why This Matters

| Spotify Onboarding | Serafis Onboarding |
|-------------------|-------------------|
| Listening preferences | Research profile |
| Optimizes for engagement | Optimizes for relevance to work |
| "What do you enjoy?" | "What do you need to know?" |

---

## 4. Discover Page Architecture

### 4.1 Section Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  DISCOVER                                                     🔍 Search │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  ⏱️ CONTINUE RESEARCH                             [History - N/A] │  │
│  │  Pick up where you left off                                       │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  📊 INSIGHTS FOR YOUR FOCUS                           [PHASE 1]  │  │
│  │  Based on AI & Machine Learning, Enterprise SaaS                  │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                 │  │
│  │  │ Episode │ │ Episode │ │ Episode │ │ Episode │                 │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  🎯 TRACKING: OPENAI                                  [PHASE 1]  │  │
│  │  Latest high-relevance episodes                                   │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                 │  │
│  │  │ Episode │ │ Episode │ │ Episode │ │ Episode │                 │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  👤 TRACKING: SAM ALTMAN                              [PHASE 1]  │  │
│  │  Recent appearances and mentions                                  │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐                             │  │
│  │  │ Episode │ │ Episode │ │ Episode │                             │  │
│  │  └─────────┘ └─────────┘ └─────────┘                             │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  🔥 NON-CONSENSUS IDEAS                               [PHASE 1]  │  │
│  │  Contrarian views from credible speakers                          │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                 │  │
│  │  │ Episode │ │ Episode │ │ Episode │ │ Episode │                 │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  💎 HIGHEST SIGNAL THIS WEEK                          [PHASE 1]  │  │
│  │  Top Insight + Credibility across all topics                      │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                 │  │
│  │  │ Episode │ │ Episode │ │ Episode │ │ Episode │                 │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  📡 NEW FROM YOUR SHOWS                               [PHASE 2]  │  │
│  │  Latest from subscribed series                                    │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                 │  │
│  │  │ Episode │ │ Episode │ │ Episode │ │ Episode │                 │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Section Definitions

| Section | Algorithm | Personalized? | Phase |
|---------|-----------|---------------|-------|
| **Continue Research** | User history | Yes | N/A |
| **Insights for Your Focus** | Sector match + quality | Yes | 1 |
| **Tracking: [Company]** | Entity relevance | Yes | 1 |
| **Tracking: [Person]** | Person relevance | Yes | 1 |
| **Non-Consensus Ideas** | Critical Views + credibility | No (global) | 1 |
| **Highest Signal** | Pure quality scores | No (global) | 1 |
| **New from Your Shows** | Subscription-based | Yes | 2 |

---

## 5. Episode Card Design

### 5.1 Layout

```
┌──────────────────────────────────────────────────────────────┐
│  ┌──────────┐                                                │
│  │          │  Episode Title (max 2 lines)                   │
│  │ [ARTWORK]│  Series Name                                   │
│  │          │  Jan 21 • 32 min                               │
│  └──────────┘  ───────────────────────────────               │
│                💎 High Insight  •  ⭐ High Credibility        │
│                                                              │
│  Key insight preview: "Jensen Huang discusses why           │
│  inference will dominate compute spend by 2027..."           │
│                                                              │
│  🏷️ AI & Machine Learning                                    │
│                                                              │
│  [🔖 Save]                                [⊘ Not Interested] │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Quality Badges

| Badge | Condition | Display |
|-------|-----------|---------|
| 💎 High Insight | `insight_score >= 3` | "💎 High Insight" |
| ⭐ High Credibility | `credibility_score >= 3` | "⭐ High Credibility" |
| 📊 Data-Rich | `information_score >= 3` | "📊 Data-Rich" |
| 🔥 Contrarian | Critical Views flags non-consensus | "🔥 Contrarian" |

Show up to 2 badges. Priority: Insight > Credibility > Information > Contrarian.

### 5.3 Key Difference from Spotify/Apple

| Element | Spotify/Apple | Serafis |
|---------|---------------|---------|
| Quality signal | None / user ratings | AI quality badges |
| Preview text | Description | Key insight extraction |
| Purpose | "Will I enjoy this?" | "Will this help my research?" |

---

## 6. Algorithm Specifications

### 6.1 "Insights for Your Focus"

Surfaces episodes relevant to user's research profile sectors.

```python
def get_insights_for_focus(user_id: str, limit: int = 10) -> List[Episode]:
    """
    Episodes matching user's sector focus, weighted by quality.
    """
    user = get_research_profile(user_id)
    
    # Get episodes matching user's sectors
    candidates = []
    for sector in user.sectors:
        candidates.extend(get_episodes_by_category(sector, limit=50))
    
    # Filter seen
    seen_ids = get_user_seen_ids(user_id)
    candidates = [ep for ep in candidates if ep.id not in seen_ids]
    
    # Score: 60% quality, 40% recency
    scored = []
    for ep in candidates:
        quality = (ep.insight_score * 0.5 + ep.credibility_score * 0.5) / 4.0
        recency = max(0, 1 - (days_since(ep.published_at) / 30))
        score = quality * 0.6 + recency * 0.4
        scored.append((ep, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return diversify([ep for ep, _ in scored], limit)
```

### 6.2 "Tracking: [Company]"

Surfaces episodes where a tracked company is discussed with high relevance.

```python
def get_tracking_company(user_id: str, company_id: str, limit: int = 10) -> List[Episode]:
    """
    Episodes mentioning tracked company with relevance >= 3.
    """
    # Get episodes where company has high relevance
    episodes = get_episodes_by_entity(
        entity_id=company_id,
        entity_type="organization",
        min_relevance=3,
        limit=50
    )
    
    # Filter seen
    seen_ids = get_user_seen_ids(user_id)
    episodes = [ep for ep in episodes if ep.id not in seen_ids]
    
    # Sort by: relevance * quality * recency
    scored = []
    for ep in episodes:
        entity_relevance = get_entity_relevance(ep.id, company_id) / 4.0
        quality = (ep.insight_score + ep.credibility_score) / 8.0
        recency = max(0, 1 - (days_since(ep.published_at) / 60))
        score = entity_relevance * 0.4 + quality * 0.4 + recency * 0.2
        scored.append((ep, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]
```

### 6.3 "Tracking: [Person]"

Surfaces episodes where a tracked person appears or is discussed.

```python
def get_tracking_person(user_id: str, person_id: str, limit: int = 10) -> List[Episode]:
    """
    Episodes featuring or mentioning tracked person.
    Prioritize interviews (relevance 4) over mentions.
    """
    episodes = get_episodes_by_person(
        person_id=person_id,
        min_relevance=2,
        limit=50
    )
    
    seen_ids = get_user_seen_ids(user_id)
    episodes = [ep for ep in episodes if ep.id not in seen_ids]
    
    # Heavily weight person relevance (interview vs mention)
    scored = []
    for ep in episodes:
        person_relevance = get_person_relevance(ep.id, person_id) / 4.0
        quality = (ep.insight_score + ep.credibility_score) / 8.0
        recency = max(0, 1 - (days_since(ep.published_at) / 90))
        score = person_relevance * 0.5 + quality * 0.3 + recency * 0.2
        scored.append((ep, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]
```

### 6.4 "Non-Consensus Ideas"

Surfaces contrarian views from credible speakers (unique Serafis value).

```python
def get_non_consensus_ideas(limit: int = 10, days: int = 14) -> List[Episode]:
    """
    Episodes flagged as non-consensus by Critical Views analysis,
    filtered to high-credibility speakers only.
    """
    recent = get_episodes_published_after(now() - timedelta(days=days))
    
    # Filter to episodes with non-consensus flag AND high credibility
    contrarian = [
        ep for ep in recent
        if ep.has_critical_views and ep.credibility_score >= 3
    ]
    
    # Sort by insight (novel ideas) + credibility (trustworthy source)
    contrarian.sort(
        key=lambda ep: ep.insight_score * 0.6 + ep.credibility_score * 0.4,
        reverse=True
    )
    
    return diversify(contrarian, limit)
```

### 6.5 "Highest Signal This Week"

Global quality ranking (not personalized).

```python
def get_highest_signal(limit: int = 10, days: int = 7) -> List[Episode]:
    """
    Top quality episodes from the past week.
    This is Serafis's unique value vs Spotify/Apple.
    """
    recent = get_episodes_published_after(now() - timedelta(days=days))
    
    # Pure quality score
    scored = []
    for ep in recent:
        quality = (
            ep.insight_score * 0.45 +
            ep.credibility_score * 0.40 +
            ep.information_score * 0.15
        ) / 4.0
        scored.append((ep, quality))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return diversify([ep for ep, _ in scored], limit)
```

### 6.6 Cold Start

For users with no research profile yet:

```python
def get_cold_start_recommendations(limit: int = 10) -> List[Episode]:
    """
    Before research profile is set, show global Highest Signal.
    Prompt user to complete onboarding for personalization.
    """
    return get_highest_signal(limit)
```

### 6.7 Diversification

```python
def diversify(episodes: List[Episode], limit: int, max_per_series: int = 2) -> List[Episode]:
    """
    Ensure variety: max 2 episodes per series.
    """
    result = []
    series_count = {}
    
    for ep in episodes:
        if series_count.get(ep.series_id, 0) >= max_per_series:
            continue
        result.append(ep)
        series_count[ep.series_id] = series_count.get(ep.series_id, 0) + 1
        if len(result) >= limit:
            break
    
    return result
```

---

## 7. "Not Interested" Feedback

### 7.1 Data Model

```python
class NotInterested:
    user_id: str
    episode_id: str
    timestamp: datetime
```

### 7.2 Usage

- Exclude from all recommendation queries
- Future: Propagate penalty to similar content (same series, same primary entity)

---

## 8. API Specification

### 8.1 Endpoints

| Endpoint | Description | Phase |
|----------|-------------|-------|
| `GET /api/recommendations/focus` | Insights for user's sector focus | 1 |
| `GET /api/recommendations/tracking/company/{id}` | Episodes for tracked company | 1 |
| `GET /api/recommendations/tracking/person/{id}` | Episodes for tracked person | 1 |
| `GET /api/recommendations/non-consensus` | Contrarian ideas | 1 |
| `GET /api/recommendations/highest-signal` | Top quality (global) | 1 |
| `GET /api/recommendations/subscriptions` | New from subscribed series | 2 |
| `POST /api/feedback/not-interested` | Mark as not interested | 1 |
| `PUT /api/profile/research` | Update research profile | 1 |

### 8.2 Response Format

```json
{
  "section": "tracking_company",
  "title": "Tracking: OpenAI",
  "subtitle": "Latest high-relevance episodes",
  "episodes": [
    {
      "id": "ep_123",
      "title": "20VC: Sam Altman vs Elon Musk",
      "series": {
        "id": "series_456",
        "name": "The Twenty Minute VC",
        "artwork_url": "https://..."
      },
      "published_at": "2026-01-22T00:00:00Z",
      "duration_seconds": 3720,
      "key_insight": "Discusses the $100B legal battle and OpenAI's path to AGI...",
      "scores": {
        "insight": 4,
        "credibility": 4,
        "information": 3
      },
      "badges": ["high_insight", "high_credibility"],
      "entity_relevance": 0.9,
      "categories": ["Technology & AI"]
    }
  ]
}
```

---

## 9. Implementation Timeline

### Phase 1: MVP (Week 1-2)

| Day | Task |
|-----|------|
| 1 | Research profile data model + onboarding API |
| 2 | `get_insights_for_focus()` implementation |
| 3 | `get_tracking_company()` implementation |
| 4 | `get_tracking_person()` implementation |
| 5 | `get_non_consensus_ideas()` implementation |
| 6 | `get_highest_signal()` implementation |
| 7 | Filtering (seen, not interested) + diversification |
| 8 | API endpoints + integration testing |
| 9-10 | Mobile frontend integration |

### Phase 2: Enhancements (Week 3-4)

- Subscription-based section
- Embedding similarity for "Related Research"
- Not interested penalty propagation
- Multiple tracked companies/people sections

---

## 10. Success Metrics

### 10.1 Research-Oriented Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Profile completion rate** | Users who complete research profile | > 60% |
| **Tracking adoption** | Users who track ≥1 company or person | > 40% |
| **Quality of engaged content** | Avg (insight + credibility) of clicked episodes | > 3.0 |
| **Research session depth** | Episodes viewed per session | > 3 |

### 10.2 Engagement Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Section CTR** | Clicks / impressions per section | > 5% |
| **Not interested rate** | Not interested / impressions | < 5% |
| **Return rate** | Users returning within 7 days | > 30% |

---

## 11. Open Questions for Rohan S.

1. **Entity tracking in mobile:** Is there UI for users to add companies/people to track?
2. **Onboarding flow:** Can we add research profile questions to signup?
3. **Critical Views data:** Is the non-consensus flag reliably populated?
4. **Key insight extraction:** Can we surface a 1-sentence insight preview on cards?
5. **Success metric:** Is the goal listening time or research efficiency?

---

## Appendix A: Serafis Intelligence Scores

| Score | Scale | Description | Weight in Recommendations |
|-------|-------|-------------|--------------------------|
| **Insight** | 1-4 | Novelty and depth of ideas | Primary (45%) |
| **Credibility** | 1-4 | Speaker authority | Primary (40%) |
| **Information** | 1-4 | Data density | Secondary (15%) |
| **Entertainment** | 1-4 | Engagement quality | Not used (entertainment ≠ research value) |

---

## Appendix B: User Segment Behaviors

| Segment | Primary Sections | Key Entities |
|---------|-----------------|--------------|
| **VC Investor** | Focus (AI/Enterprise), Tracking (portfolio cos), Non-Consensus | OpenAI, Anthropic, emerging startups |
| **HF Analyst** | Tracking (public cos), Focus (sector), Highest Signal | Nvidia, Microsoft, macro themes |
| **McKinsey** | Focus (client sectors), Tracking (client cos), Non-Consensus | Varies by engagement |
| **Prosumer** | Highest Signal, Non-Consensus, Tracking (FAANG) | Tesla, Apple, crypto projects |
| **Founder** | Focus (own sector), Tracking (competitors), Non-Consensus | Direct competitors, VCs |

---

## Appendix C: Related Documents

- [Competitor Analysis](./competitor_analysis.md)
- [UI Examination](/Users/rohankatakam/Documents/serafis/ui/ui_examination.md)
- [Investor Memo](/Users/rohankatakam/Documents/serafis/serafis_investor_memo.md)
