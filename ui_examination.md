# Serafis — UI Feature Examination

> *Documentation of all user-facing features, their inputs, outputs, and observations from testing.*

---

## Navigation Structure

The Serafis web application (`app.serafis.ai`) has the following primary navigation:

```
┌────────────────────────────────────────┐
│  SERAFIS                               │
├────────────────────────────────────────┤
│  ◎ Discover                            │
│  ⊕ AI Search                           │
│  □ Bookmarks                           │
│  ○ AI Queries                          │
├────────────────────────────────────────┤
│  Settings                              │
│  ⚙ Account                             │
│  ≡ Preferences                         │
└────────────────────────────────────────┘
```

---

## Feature 1: Discover Tab

**URL:** `app.serafis.ai/#/discover`

### 1.1 Search All Podcasts and Episodes

**Purpose:** Free-text search across all episodes and series in the corpus.

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| Search query | String | Free-text search term |

**Output:**
- List of matching episodes with metadata
- List of matching series

**Observations:**
- Standard keyword-based search
- Returns episode titles, series names, publish dates
- No structured entity resolution in this view

---

### 1.2 Top Episodes Leaderboard

**Purpose:** Surface trending/high-engagement episodes.

**Output:**
| Field | Description |
|-------|-------------|
| Episode Title | Name of the podcast episode |
| Series | Parent podcast series |
| Publish Date | When the episode was released |

**Observations:**
- Appears to rank by recency and/or engagement
- Good for discovery of new content
- No relevance scoring visible

---

### 1.3 Curated Series

**Purpose:** Highlight editorially selected podcast series.

**Output:**
- List of curated podcast series with metadata

**Observations:**
- Manual curation layer
- Signals which sources Serafis considers high-quality
- Useful for understanding corpus composition

---

## Feature 2: AI Search Tab

**URL:** `app.serafis.ai/#/ai_search`

This is the core product surface, containing two primary search modes:

1. **Search by Tag** (Structured entity search)
2. **Ask a Question** (RAG-based Q&A)

---

### 2.1 Search by Tag

Three structured search modalities that query the entity graph.

**Common Output Table Structure (All Tag Searches):**

| Column | Icon/Format | Description |
|--------|-------------|-------------|
| Relevance | Incline graph icon (↗) | Relevance indicator for the entity in this episode |
| Score | Gem icon (💎) | Quality/importance score |
| Mentions (n) | Integer (1-5) | Number of mentions in episode |
| Relevance Score | Decimal (0.0–1.0) | Displayed as percentage in some views |
| Published | ISO timestamp | When the episode was released |
| Episode Title | String | Linked title to episode detail |
| Series | String | Parent podcast series |
| Context | String | Summary of why entity is relevant in this episode |

---

#### 2.1.1 Search by Organization

**Purpose:** Find episodes mentioning a specific company/organization.

**Input Parameters:**

| Parameter | Type | Options/Format | Required |
|-----------|------|----------------|----------|
| Organizations | Dropdown (autocomplete) | Entity list with `(n=X / score=Y)` | Yes |
| Relevance | Dropdown | Moderate Relevance (2), etc. | Yes (default: 2) |
| Search entire index | String | Additional keyword filter | No |
| Published within | Dropdown | Preset date ranges | No |
| Published after | Date picker | YYYY-MM-DD | No |
| Published before | Date picker | YYYY-MM-DD | No |

**Dropdown Autocomplete Format:**
```
Google (n=982 / score=1172)
Dragonfly (n=38 / score=36)
Duolingo (n=28 / score=34)
```
- `n` = mention count across corpus
- `score` = aggregate relevance score

**Example Output (OpenAI search):**
```
Top 50 matches for "OpenAI" (organizations)

↗ 💎 3  0.8   2026-01-26  "The Hidden Economics Powering AI"              a16z Podcast       "OpenAI is extensively discussed as a major AI company..."
↗ 💎 2  0.65  2026-01-26  "20VC: From Only OpenAI to Die-Hard Anthropic"  The Twenty Minute VC  "OpenAI is discussed as Legora's former primary model provider..."
↗ 💎 2  0.7   2026-01-25  "The Future of Everything: What CEOs..."        All-In             "OpenAI was mentioned as a major customer of Crusoe Cloud..."
↗ 💎 4  0.9   2026-01-22  "20VC: Sam Altman vs Elon Musk..."              The Twenty Minute VC  "OpenAI was the primary focus of extensive discussion..."
```

**Observations:**
- ✅ Strong for major entities (Google, Microsoft, OpenAI)
- ❌ **Critical Gap:** Emerging companies (Etched, Omnara, CodeRabbit) return zero results if not in entity graph
- ❌ Relevance score seems volume-weighted, not insight-weighted
- ❌ Context snippets are episode-level, not claim-level
- ⚠️ No fallback to transcript search if org not in dropdown

---

#### 2.1.2 Search by Person

**Purpose:** Find episodes mentioning or featuring a specific person.

**Input Parameters:**

| Parameter | Type | Options/Format | Required |
|-----------|------|----------------|----------|
| Person | Dropdown (autocomplete) | Entity list with `(n=X / score=Y)` | Yes |
| Person Relevance | Dropdown | Moderate Relevance (2), etc. | Yes (default: 2) |
| Search entire index | String | Additional keyword filter | No |
| Published within | Dropdown | Preset date ranges | No |
| Published after | Date picker | YYYY-MM-DD | No |
| Published before | Date picker | YYYY-MM-DD | No |

**Dropdown Autocomplete Format:**
```
Donald Trump (n=464 / score=657)
Elon Musk (n=593 / score=498)
Andrew Huberman (n=126 / score=422)
Sam Altman (n=376 / score=365)
```

**Example Output (Sam Altman search):**
```
Top 50 matches for "Sam Altman" (people)

↗ 💎 3  0.8   2026-01-22  "20VC: Sam Altman vs Elon Musk: The $100BN Battle..."  The Twenty Minute VC  "Sam Altman is extensively discussed in relation to the legal battle..."
↗ 💎 2  0.7   2026-01-21  "Uncapped #40 | Vinod Khosla and Keith Rabois..."      Uncapped with Jack Altman  "Sam is referenced in the context of OpenAI investment decisions..."
↗ 💎 4  0.9   2025-11-05  "Sam Altman on Trust, Persuasion, and the Future..."   Conversations with Tyler  "Sam Altman is the main guest being interviewed..."
↗ 💎 4  0.9   2025-10-08  "Sam Altman on Sora, Energy, and Building an AI Empire" a16z Podcast  "Sam Altman was the primary guest and main speaker throughout..."
```

**Observations:**
- ✅ Strong entity resolution for operators (CEOs, founders)
- ✅ Shows title/role in episode detail view ("CEO of Nvidia", "AI researcher")
- ✅ Relevance scores working well for prominent figures
- ⚠️ Title metadata exists but not used for ranking weight
- ⚠️ Doesn't distinguish "interviewed" vs "mentioned"

---

#### 2.1.3 Search by Theme

**Purpose:** Find episodes covering a specific topic/category.

**Input Parameters:**

| Parameter | Type | Options/Format | Required |
|-----------|------|----------------|----------|
| Theme Options | Dropdown | Category list | Yes |
| Theme scope | Toggle | Major Categories / Subcategories | Yes |
| Category Relevance | Dropdown | Moderate Relevance (2), etc. | Yes (default: 2) |
| Published within | Dropdown | Preset date ranges | No |
| Published after | Date picker | YYYY-MM-DD | No |
| Published before | Date picker | YYYY-MM-DD | No |

**Example Output (AI Infrastructure subcategory):**
```
4 matches for "AI Infrastructure" (subcategories)

↗ 💎 4  0.75  2025-07-24  "From Electrons to Intelligence: How Crusoe Powers AI..."  The Pexapark Podcast  "The entire conversation revolves around the specialized infrastructure required for AI computing..."
↗ 💎 3  0.75  2025-04-09  "Ep 61: Redpoint's AI Investors Break Down..."            Unsupervised Learning  "The speakers extensively discuss the AI infrastructure layer..."
↗ 💎 3  0.7   2025-03-25  "Ep 59: OpenAI Product & Eng Leads..."                     Unsupervised Learning  "The speakers extensively discuss the infrastructure needs for AI development..."
↗ 💎 3  0.7   2025-02-07  "DeepSeek, Deep Research, and 2025 Predictions..."         No Priors             "The conversation extensively covers AI infrastructure..."
```

**Observations:**
- Hierarchical category/subcategory structure
- Two scope options: "Major Categories" and "Subcategories"
- Enables topical exploration (AI, Crypto, Energy, etc.)
- Lower match counts compared to org/person search

---

### 2.2 Ask a Question (RAG Q&A)

**Purpose:** Natural language question answering with citation.

**Input:**

| Parameter | Type | Description |
|-----------|------|-------------|
| Query | String (textarea) | "Ask anything" free-form question |

**Output Structure:**

| Component | Description |
|-----------|-------------|
| Answer | Paragraph response synthesized from sources (markdown formatted) |
| Inline Citations | Bracketed references (e.g., [1], [3], [5]) |
| Citation List | Expandable reference info for each cited podcast episode |

**Citation Format:**
```
* [Citation #]. [Date] | [Series] | [Episode Title]
    * [Timestamp] [Relevant quote from transcript]
```

**Example (Bearish consensus on OpenAI query):**
```
Input: "What is the bearish consensus on OpenAI into 2026"

Output:
The bearish consensus on OpenAI into 2026 centers on several key challenges and risks. 
Foremost, expectations for the company are exceedingly high, leading to a concern that 
anything less than exceptional performance could be perceived as a failure, potentially 
causing OpenAI to miss its financial targets by a significant margin, such as 40% [11]. 
This situation is exacerbated by the substantial capital commitments required, including 
an estimated $10 billion spent by OpenAI and Microsoft in 2023-early 2024 on computing 
clusters, and a hypothesized $100 billion data center (Stargate) for 2028 delivery, 
raising questions about whether future revenues can justify these massive investments [3, 5]...

Citations:
* 11. Jun 05, '25 | The Twenty Minute VC (20VC):... | 20VC: Is Chamath Right...
    * 44:55 Now, maybe it will, because I think it is a more impressive piece of 
      technology when you use it, but maybe it won't...

* 3. Oct 02, '24 | Dwarkesh Podcast | Dylan Patel & Jon (Asianometry) – How the 
     Semiconductor Industry Actually Works
    * 01:43:16 So this is like, you don't necessarily need the revenue in 2025 to 
      support this...

* 5. Dec 06, '24 | Invest Like the Best | Chetan Puttagunta and Modest Proposal...
    * 14:16 Let's apply that to all the various slabs...
```

**Observations:**
- ✅ **Can find entities not in the org graph** (e.g., Omnara, emerging startups)
- ✅ Synthesizes across multiple sources
- ✅ Provides timestamped citations for defensibility
- ✅ Includes relevant quote snippets from transcripts
- ❌ No relevance score on citations
- ❌ No speaker attribution in the answer body
- ⚠️ **Discovery Gap**: Ask AI can reference an org, but Org Search cannot surface it

---

## Feature 3: Episode Detail View

**URL:** `app.serafis.ai/#/episode/{id}`

When clicking into a specific episode, users see a tabbed interface with metadata header:

**Header:**
- Episode Title
- Series (linked)
- Publish Date
- Episode Duration
- Bookmark button
- Share button
- URL link

### 3.1 Tab Structure

| Tab | Purpose |
|-----|---------|
| Analysis | AI-generated summary, key insights, scores |
| Transcript | Full transcript with timestamps |
| Ask AI | Episode-scoped Q&A |
| Themes | Topic tags extracted from episode |
| Entities | Organizations mentioned with relevance |
| People | People mentioned with relevance |

---

### 3.2 Analysis Tab

The Analysis tab contains several sections:

#### 3.2.1 Serafis Intelligence Scores

Four scored dimensions with clickable rationale popups:

| Dimension | Scale | Description |
|-----------|-------|-------------|
| Credibility | ★★★★ (1-4) | Speaker authority and track record |
| Insight | ★★★☆ (1-4) | Novelty and depth of ideas |
| Information | ★★★☆ (1-4) | Specificity and data density |
| Entertainment | ★★☆☆ (1-4) | Engagement and storytelling |

**Credibility Rationale Example:**
> "Dhanji Prasanna demonstrates exceptional credibility as the CTO of Block, a multi-billion dollar financial technology company. Block operates major platforms like Square and Cash App, serving tens of millions of consumers and businesses globally..."

**Insight Rationale Example:**
> "The transcript offers meaningful new perspectives on AI implementation in enterprise, particularly through Block's open-source AI agent, Goose. The discussion introduces non-obvious ideas about AI agent middleware and the concept of 'vibe coding'..."

**Information Rationale Example:**
> "The transcript provides detailed insights into Block's AI initiatives, particularly their open-source AI agent, Goose. Specific technical details are shared, such as Goose's use of the Model Context Protocol (MCP) for tool integration..."

**Entertainment Rationale Example:**
> "The transcript maintains a steady flow of engaging technical discussion about AI and its implementation at Block, keeping the attention of listeners interested in technology and business..."

#### 3.2.2 Episode Summary

A paragraph-length AI-generated description of the episode content.

**Example:**
> "Block CTO Dhanji Prasanna outlines the company's enterprise-wide AI transformation, centered on their open-source AI agent, Goose. This agent orchestrates workflows across the organization, enabling engineers to save substantial time weekly and build custom applications without coding through its Model Context Protocol..."

#### 3.2.3 Key Insights Section

Top 3 takeaways with numbered explanations:

**Example:**
```
1. Goose as an open-source AI agent for enterprise productivity:
Block developed and open-sourced Goose, a general-purpose AI agent that can automate 
workflows across various enterprise systems. Goose uses the Model Context Protocol (MCP) 
to interact with different tools and capabilities...

2. AI-first transformation of Block's organizational structure:
Block underwent an organizational restructuring to become more AI-centric, moving from 
a GM structure to a functional organization...

3. The future of AI in software development:
Prasanna predicts a shift towards "swarm intelligence" in software development, where 
multiple AI agents work together to build complex applications...
```

#### 3.2.4 Data Points Section

Top 4 specific metrics and data points:

**Example:**
```
1. Manual hours saved by Goose: Block is targeting 25% of manual hours saved by their 
   AI agent Goose by the end of the year.

2. Engineer productivity gains: Engineers at Block report saving 8-10 hours per week 
   by using Goose and other AI tools.

3. AI-generated code: For AI-first teams at Block, nearly 100% of code is "vibe coded". 
   For engineers working on complex legacy codebases, 30-40% of their code is generated by AI.

4. Goose adoption: The majority of Block's employees (over 3,000 engineers) are now using Goose.
```

#### 3.2.5 Critical Views Section

Analysis of contrarian or non-consensus ideas in the episode:

**Example:**
> "Based on my analysis, this conversation contains some interesting insights but is not highly contrarian overall. I would characterize it as 'somewhat insightful' with a few novel ideas within the realm of AI implementation in enterprise settings..."

Includes specific quotes supporting the contrarian assessment.

#### 3.2.6 Top Quotes Section

3-5 insightful direct quotes from the episode:

**Example:**
```
1. "Our approach has been to not over engineer it. So we like to let Goose learn from 
   doing things. [...] We find that Goose is more capable than if you tried to figure 
   out how to make a tool Goose friendly."

2. "We have a metric internally which we track on a weekly basis and that metric is 
   very simply manual hours saved by Goose. And that metric started at 0% and now 
   it's going to hit probably 25% of manual hours saved by the end of the year."
```

---

### 3.3 Transcript Tab

**Purpose:** Full episode transcript with timestamps.

**Format:**
```
Estimated reading time: [X] minutes | [Y] words | [Z] paragraphs

00:00 - [Transcript paragraph 1...]

01:00 - [Transcript paragraph 2...]

02:15 - [Transcript paragraph 3...]
```

**Observations:**
- ❌ No speaker diarization (speaker labels not shown)
- ✅ Timestamps provided per paragraph
- ✅ Full searchable text
- ✅ Reading time estimate

---

### 3.4 Ask AI Tab (Episode-Scoped)

**Purpose:** RAG-based Q&A scoped to the specific episode.

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| Query | String (textarea) | "Ask anything" free-form question |

**Output:**
- Answer synthesized from episode content only
- Direct quotes with context
- Analysis and interpretation

**Example:**
```
Input: "What is the most bold claim in this episode?"

Output:
Looking through this transcript, the most bold claim appears to be about 
**Goose achieving complete self-modification and autonomous development**. 
Specifically, Dhanji states:

> "We also use Goose to build Goose. So the vast majority of Goose's code is 
> written by Goose. And so we almost fully bootstrapped it... our goal is for 
> it to be completely autonomous and for each release, for it to rewrite itself 
> 100% from scratch."

This is extraordinarily bold because it describes an AI system that has achieved 
recursive self-improvement...
```

---

### 3.5 Themes Tab

**Purpose:** Topic categorization of the episode.

**Two Subtabs:**
1. **Subcategories** — Granular topic tags
2. **Major Categories** — High-level thematic buckets

#### Subcategories Table:

| Column | Description |
|--------|-------------|
| Subcategory | Topic name |
| Relevance | Score (1-4) |
| Context | Why this theme applies |

**Example:**
```
AI & Machine Learning          4  The conversation primarily focuses on AI and its impact on Block's operations...
DevOps & AI Engineering        3  The discussion delves deeply into how AI, particularly Goose, is changing software development...
Product Development & GTM      3  The conversation covers how Block is integrating AI into its product suite...
Hiring, Culture, & Team        2  The discussion touches on Block's remote-first culture and how it impacts hiring...
Open Source AI Development     3  A significant portion of the conversation focuses on Block's commitment to open-source AI...
Organizational AI Integration  3  The conversation extensively covers how Block is integrating AI across its organization...
```

#### Major Categories Table:

| Column | Description |
|--------|-------------|
| Category | High-level theme |
| Relevance | Score (1-4) |
| Context | Why this category applies |

**Example:**
```
Technology & AI                    4  This is the primary focus of the conversation, discussing Block's AI agent Goose...
Startups, Growth & Founder Journeys 3  The conversation extensively covers Block's journey in adopting AI, organizational changes...
Crypto & Web3                      1  While not a central focus, the transcript meaningfully discusses Block's involvement in Bitcoin...
```

---

### 3.6 Entities Tab

**Purpose:** Organizations and companies mentioned in the episode.

**Table Structure:**

| Column | Description |
|--------|-------------|
| Entity | Company/org name (with checkbox for selection) |
| Relevance | Score (0-4) |
| Context | Summary of how entity is discussed |

**Example:**
```
☑ Block     4  Block is the primary focus of the conversation, as the interviewee Dhanji Prasanna is the CTO...
☑ Goose     4  Goose, an open-source AI agent developed by Block, is a central topic of discussion...
☑ Square    2  Square is discussed as one of Block's main pillars, serving merchants and sellers...
☑ Cash App  2  Cash App is mentioned as another main pillar of Block, serving consumers...
☐ Tidal     1  Tidal is briefly mentioned as Block's music streaming service...
☐ BitKey    1  BitKey is mentioned as one of Block's open source initiatives...
☐ Sequoia   1  Sequoia is mentioned in the context of the interviewer's affiliation...
☐ Anthropic 1  Anthropic is briefly mentioned as a collaborator with Block in advancing MCP...
☐ Klarna    0  Klarna is mentioned in passing, referencing a conversation with Sebastian...
☐ MIT       0  MIT is briefly mentioned in reference to a report about Fortune 500 companies...
```

**Observations:**
- ✅ Per-episode entity extraction working well
- ✅ Context snippets are useful
- ✅ Checkboxes for user selection (purpose unclear — possibly for export/filtering)
- ⚠️ Relevance scores (0–4) differ from search relevance (0.0–1.0)
- ⚠️ No claim extraction, just "how they were discussed"

---

### 3.7 People Tab

**Purpose:** Individuals mentioned in the episode.

**Table Structure:**

| Column | Description |
|--------|-------------|
| Person | Name (with checkbox) |
| Title | Role/position |
| Relevance | Score (0-4) |
| Context | Summary of person's role in discussion |

**Example:**
```
☑ Dhanji Prasanna  CTO at Block              4  Dhanji Prasanna was the primary guest on the episode, discussing Block's AI initiatives...
☑ Jack Dorsey      Founder of Block          2  Jack Dorsey was mentioned multiple times throughout the conversation, particularly...
☐ Brad Axson       [blank]                   1  Brad Axson was mentioned as the engineer who initially developed Goose at Block...
☐ Bob Lee          Former CTO of Block       0  Bob Lee was briefly mentioned as Block's first CTO...
☐ Brian            Former Cash App CEO       0  Brian was briefly mentioned as the former Cash App CEO...
☐ Sebastian        [blank]                   0  Sebastian from Klarna was briefly mentioned in relation to vibe coding...
```

**Observations:**
- ✅ Title/role metadata is present (when available)
- ✅ Distinguishes primary guest vs mentioned figures via relevance
- ⚠️ Some titles are blank
- ⚠️ Credibility weighting not visible in ranking
- ⚠️ No speaker-level claim attribution

---

## Feature 4: Other Features

### 4.1 Bookmarks

**Purpose:** Save episodes for later reference.

**Observations:**
- Standard bookmarking functionality
- Accessible from episode detail view header

---

### 4.2 AI Queries

**Purpose:** History of previous Ask AI queries.

**Observations:**
- Query log for reference
- Enables revisiting previous research

---

## Summary: Feature Gap Analysis

| Feature | Strength | Gap |
|---------|----------|-----|
| **Org Search** | Great for major entities | Zero fallback for emerging orgs |
| **Person Search** | Strong entity resolution | No credibility weighting in ranking |
| **Theme Search** | Topic exploration | Lower coverage, less tested |
| **Ask AI** | Finds anything, synthesizes well | No relevance scores, no speaker attribution |
| **Episode Analysis** | Rich scoring (Credibility, Insight, etc.) | Scores not used in search ranking |
| **Episode Entities** | Good extraction | Episode-level, not claim-level |
| **Episode People** | Title metadata exists | Not used for search ranking |

---

## The Critical Discovery Gap

```
┌─────────────────────────────────────────────────────────────────┐
│  USER SEARCHES: "Etched"                                         │
├─────────────────────────────────────────────────────────────────┤
│  ORG SEARCH (Structured)    →  ❌ Zero Results (not in graph)   │
│  ASK AI (RAG)               →  ✅ "Etched is an AI chip company…"│
└─────────────────────────────────────────────────────────────────┘

The product has the data. The structured workflow can't access it.
This is the "Org Discovery Bridge" opportunity.
```

---

## Relevance Score Systems (Observed)

**Search Results (0.0–1.0 scale):**
- 0.9 = Primary focus of episode
- 0.7–0.8 = Significant discussion
- 0.6–0.65 = Moderate mention
- <0.6 = Passing reference

**Episode Detail Entity/People (0–4 scale):**
- 4 = Central topic / Primary guest
- 3 = Significant discussion
- 2 = Moderate mention
- 1 = Brief mention
- 0 = Passing reference

**Episode Analysis Scores (★ 1–4 scale):**
- Credibility: Speaker authority and domain expertise
- Insight: Novelty and depth of ideas
- Information: Data density and specificity
- Entertainment: Engagement and storytelling quality

**Dropdown Scores (`n=X / score=Y`):**
- `n` = Raw mention count across corpus
- `score` = Aggregate relevance (formula unclear, appears to be n × weight)

---

## Key Product Observations

### What Exists (Valuable)
1. **Credibility/Insight/Information scoring** — Episode-level quality metrics exist
2. **Critical Views extraction** — Non-consensus idea detection is attempted
3. **Data Points extraction** — Specific claims/metrics are extracted
4. **Top Quotes extraction** — Key quotes are surfaced
5. **Theme categorization** — Hierarchical topic tagging

### What's Missing (Gaps)
1. **Claim-level search** — Cannot search for specific claims, only episodes
2. **Speaker attribution in search** — Cannot filter by "claims made by CEOs"
3. **Credibility-weighted ranking** — Episode scores don't influence search results
4. **Non-consensus signal in search** — Critical Views exist but aren't searchable
5. **Emerging entity fallback** — Org Search fails silently for new companies
6. **Transcript diarization** — No speaker labels in raw transcript
