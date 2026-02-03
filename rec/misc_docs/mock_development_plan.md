# Serafis Recommendation Engine — Mock Development Plan

> *A practical guide to building and testing the recommendation system without backend/frontend code access.*

**Date:** January 29, 2026  
**Author:** Rohan Katakam  
**Status:** Draft  
**Related:** [Recommendation Engine Spec](./recommendation_engine_spec.md) | [Strategic Positioning](./strategic_positioning.md)

---

## 1. Overview

### 1.1 Goal

Build a fully functional mock recommendation system that:
- Uses real episode data extracted from the Serafis website
- Implements the recommendation algorithms from the spec
- Demonstrates the mobile app experience via a prototype UI
- Validates the approach before integration with production systems

### 1.2 Constraints

| Constraint | Implication |
|------------|-------------|
| No backend code access | Must reverse-engineer data model from UI |
| No frontend code access | Build standalone prototype |
| Have Serafis account | Can extract real data via browser automation |
| Prosumer-only focus | Single user profile type, simpler scope |

### 1.3 Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MOCK DEVELOPMENT STACK                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│  │  SERAFIS WEBSITE │     │   MOCK DATASET   │     │  MOCK API SERVER │    │
│  │  app.serafis.ai  │ ──► │   episodes.json  │ ──► │     FastAPI      │    │
│  │                  │     │   series.json    │     │                  │    │
│  │  (Data Source)   │     │   users.json     │     │  /api/recs/...   │    │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘    │
│         │                                                   │               │
│         │ Browser MCP                                       │ REST API      │
│         │ Extraction                                        │               │
│         ▼                                                   ▼               │
│  ┌──────────────────┐                              ┌──────────────────┐    │
│  │  EXTRACTION      │                              │  MOBILE PROTO    │    │
│  │  SCRIPTS         │                              │  React + Tailwind│    │
│  │                  │                              │  Mobile-First    │    │
│  │  Python/Node     │                              │                  │    │
│  └──────────────────┘                              └──────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Phase 1: Data Extraction

### 2.1 Target Dataset

Extract **50-100 episodes** with full metadata to enable algorithm testing.

#### Episode Data Schema

```json
{
  "id": "ep_unique_id",
  "title": "Episode Title",
  "series": {
    "id": "series_id",
    "name": "a16z Podcast",
    "artwork_url": "https://..."
  },
  "published_at": "2026-01-22T00:00:00Z",
  "duration_seconds": 3600,
  "url": "https://app.serafis.ai/#/episode/...",
  
  "scores": {
    "insight": 4,
    "credibility": 3,
    "information": 3,
    "entertainment": 2
  },
  
  "summary": "Episode summary paragraph...",
  "key_insights": [
    "Insight 1: Description...",
    "Insight 2: Description...",
    "Insight 3: Description..."
  ],
  "data_points": [
    "Data point 1...",
    "Data point 2..."
  ],
  "critical_views": "Non-consensus analysis text...",
  "top_quotes": [
    "Quote 1...",
    "Quote 2..."
  ],
  
  "categories": {
    "major": ["Technology & AI", "Startups"],
    "subcategories": ["AI & Machine Learning", "DevOps & AI Engineering"]
  },
  
  "entities": [
    {
      "id": "org_openai",
      "name": "OpenAI",
      "relevance": 4,
      "context": "OpenAI is the primary focus..."
    }
  ],
  
  "people": [
    {
      "id": "person_sam_altman",
      "name": "Sam Altman",
      "title": "CEO of OpenAI",
      "relevance": 4,
      "context": "Sam Altman was the primary guest..."
    }
  ]
}
```

#### Series Data Schema

```json
{
  "id": "series_id",
  "name": "The Twenty Minute VC",
  "artwork_url": "https://...",
  "description": "Series description...",
  "episode_count": 500,
  "popularity_score": 85
}
```

#### Mock User Data Schema

```json
{
  "id": "user_mock_1",
  "name": "Prosumer Test User",
  "category_interests": ["Technology & AI", "Crypto & Web3"],
  "subscribed_series": ["series_20vc", "series_a16z"],
  "activity": [
    {
      "entity_type": "episode",
      "entity_id": "ep_123",
      "timestamp": "2026-01-28T14:30:00Z"
    }
  ],
  "bookmarks": [
    {
      "entity_type": "episode",
      "entity_id": "ep_456",
      "timestamp": "2026-01-27T10:00:00Z"
    }
  ],
  "not_interested": ["ep_789"]
}
```

### 2.2 Extraction Strategy

Use the Browser MCP tools (`cursor-ide-browser`) to systematically navigate and extract data.

#### Step 1: Extract Episode List from Discover

```
1. Navigate to app.serafis.ai/#/discover
2. Extract Top Episodes leaderboard (episode IDs, titles, series)
3. Navigate to AI Search → Theme Search
4. For each major category (Technology & AI, Crypto, etc.):
   - Extract top episodes by category
5. Compile unique episode list (target: 100 unique episodes)
```

#### Step 2: Extract Episode Detail Data

For each episode in the list:

```
1. Navigate to episode detail page: app.serafis.ai/#/episode/{id}
2. Extract from Analysis tab:
   - Serafis Intelligence Scores (4 scores)
   - Episode Summary
   - Key Insights (3 items)
   - Data Points (4 items)
   - Critical Views
   - Top Quotes
3. Extract from Themes tab:
   - Major Categories
   - Subcategories
4. Extract from Entities tab:
   - Organization list with relevance and context
5. Extract from People tab:
   - Person list with title, relevance, and context
6. Store as JSON
```

#### Step 3: Extract Series Data

```
1. Compile unique series from episode data
2. For each series, navigate to series page
3. Extract:
   - Series name, description
   - Episode count
   - Artwork URL
4. Estimate popularity from mention counts in search dropdown
```

### 2.3 Extraction Script Outline

```python
# extraction/extract_episodes.py

import json
from datetime import datetime

class SerafisExtractor:
    """
    Uses Browser MCP to extract episode data from Serafis.
    """
    
    def __init__(self, browser_mcp):
        self.browser = browser_mcp
        self.episodes = []
        self.series = {}
    
    async def extract_discover_episodes(self, limit: int = 50):
        """Extract episode IDs from Discover page."""
        await self.browser.navigate("https://app.serafis.ai/#/discover")
        await self.browser.wait(2)
        
        # Get episode list from Top Episodes section
        snapshot = await self.browser.snapshot()
        # Parse episode IDs and titles from snapshot
        # ...
        
    async def extract_episode_detail(self, episode_id: str) -> dict:
        """Extract full metadata from episode detail page."""
        url = f"https://app.serafis.ai/#/episode/{episode_id}"
        await self.browser.navigate(url)
        await self.browser.wait(2)
        
        episode_data = {
            "id": episode_id,
            "extracted_at": datetime.utcnow().isoformat()
        }
        
        # Extract Analysis tab
        snapshot = await self.browser.snapshot()
        episode_data["scores"] = self._parse_scores(snapshot)
        episode_data["summary"] = self._parse_summary(snapshot)
        episode_data["key_insights"] = self._parse_insights(snapshot)
        episode_data["critical_views"] = self._parse_critical_views(snapshot)
        
        # Click Themes tab and extract
        await self.browser.click("Themes tab")
        await self.browser.wait(1)
        snapshot = await self.browser.snapshot()
        episode_data["categories"] = self._parse_categories(snapshot)
        
        # Click Entities tab and extract
        await self.browser.click("Entities tab")
        await self.browser.wait(1)
        snapshot = await self.browser.snapshot()
        episode_data["entities"] = self._parse_entities(snapshot)
        
        # Click People tab and extract
        await self.browser.click("People tab")
        await self.browser.wait(1)
        snapshot = await self.browser.snapshot()
        episode_data["people"] = self._parse_people(snapshot)
        
        return episode_data
    
    async def run_full_extraction(self, episode_limit: int = 100):
        """Run full extraction pipeline."""
        # Step 1: Get episode IDs
        episode_ids = await self.extract_discover_episodes(episode_limit)
        
        # Step 2: Extract each episode
        for ep_id in episode_ids:
            try:
                episode = await self.extract_episode_detail(ep_id)
                self.episodes.append(episode)
                print(f"Extracted: {episode['title']}")
            except Exception as e:
                print(f"Failed to extract {ep_id}: {e}")
        
        # Step 3: Save to file
        with open("mock_data/episodes.json", "w") as f:
            json.dump(self.episodes, f, indent=2)
        
        return self.episodes
```

### 2.4 Manual Extraction Fallback

If browser automation is unreliable, manual extraction workflow:

```
1. Open Serafis in browser
2. Navigate to episode detail page
3. Copy data from each tab into a structured template
4. Repeat for 50+ episodes
5. Compile into JSON file

Estimated time: 5-10 minutes per episode = 8-17 hours for 100 episodes
```

For efficiency, prioritize:
- Top 20 episodes from Discover
- Top 10 episodes per category (5 categories = 50 episodes)
- Top 20 episodes mentioning major entities (OpenAI, Nvidia, etc.)

---

## 3. Phase 2: Mock API Server

### 3.1 Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| API Framework | FastAPI | Fast, async, auto-docs |
| Data Storage | JSON files | Simple, no DB needed |
| Hosting | Local / ngrok | Development only |

### 3.2 Project Structure

```
mock_api/
├── main.py                    # FastAPI app entry point
├── requirements.txt           # Dependencies
├── data/
│   ├── episodes.json         # Extracted episode data
│   ├── series.json           # Extracted series data
│   └── mock_users.json       # Test user profiles
├── models/
│   ├── episode.py            # Pydantic models
│   ├── user.py
│   └── recommendation.py
├── algorithms/
│   ├── scoring.py            # Quality scoring functions
│   ├── filtering.py          # Seen/not-interested filters
│   ├── diversification.py    # Series diversity
│   └── recommendations.py    # Main recommendation functions
├── routers/
│   ├── recommendations.py    # /api/recommendations/*
│   ├── feedback.py           # /api/feedback/*
│   └── user.py               # /api/user/*
└── tests/
    ├── test_algorithms.py
    └── test_api.py
```

### 3.3 Core Algorithm Implementation

```python
# mock_api/algorithms/recommendations.py

from typing import List
from datetime import datetime, timedelta
from models.episode import Episode
from models.user import User
from algorithms.scoring import calculate_quality_score
from algorithms.filtering import filter_seen, filter_not_interested
from algorithms.diversification import diversify_by_series

def get_highest_signal(
    episodes: List[Episode],
    limit: int = 10,
    days: int = 7
) -> List[Episode]:
    """
    Top quality episodes (global, not personalized).
    This is Serafis's core value vs Spotify/Apple.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    recent = [ep for ep in episodes if ep.published_at >= cutoff]
    
    # Score by quality only
    scored = []
    for ep in recent:
        quality = calculate_quality_score(ep)
        scored.append((ep, quality))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    top = [ep for ep, _ in scored]
    
    return diversify_by_series(top, limit, max_per_series=2)


def get_insights_for_categories(
    episodes: List[Episode],
    user: User,
    limit: int = 10
) -> List[Episode]:
    """
    Episodes matching user's category interests, weighted by quality.
    """
    # Filter to matching categories
    matching = []
    for ep in episodes:
        if any(cat in user.category_interests for cat in ep.categories.major):
            matching.append(ep)
    
    # Remove seen
    matching = filter_seen(matching, user)
    matching = filter_not_interested(matching, user)
    
    # Score: 60% quality, 40% recency
    scored = []
    for ep in matching:
        quality = calculate_quality_score(ep)
        days_old = (datetime.utcnow() - ep.published_at).days
        recency = max(0, 1 - (days_old / 30))
        score = quality * 0.6 + recency * 0.4
        scored.append((ep, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    top = [ep for ep, _ in scored]
    
    return diversify_by_series(top, limit)


def get_tracking_entity(
    episodes: List[Episode],
    user: User,
    entity_name: str,
    limit: int = 10
) -> List[Episode]:
    """
    Episodes where a specific entity is discussed with high relevance.
    """
    # Find episodes mentioning entity with relevance >= 3
    matching = []
    for ep in episodes:
        for entity in ep.entities:
            if entity.name.lower() == entity_name.lower() and entity.relevance >= 3:
                matching.append((ep, entity.relevance))
                break
    
    # Remove seen
    matching = [(ep, rel) for ep, rel in matching if ep.id not in user.seen_ids]
    matching = [(ep, rel) for ep, rel in matching if ep.id not in user.not_interested]
    
    # Score: 40% entity relevance, 40% quality, 20% recency
    scored = []
    for ep, entity_rel in matching:
        quality = calculate_quality_score(ep)
        days_old = (datetime.utcnow() - ep.published_at).days
        recency = max(0, 1 - (days_old / 60))
        score = (entity_rel / 4.0) * 0.4 + quality * 0.4 + recency * 0.2
        scored.append((ep, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return [ep for ep, _ in scored[:limit]]


def get_non_consensus_ideas(
    episodes: List[Episode],
    limit: int = 10,
    days: int = 14
) -> List[Episode]:
    """
    Contrarian views from credible speakers.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    recent = [ep for ep in episodes if ep.published_at >= cutoff]
    
    # Filter to episodes with critical_views AND high credibility
    contrarian = [
        ep for ep in recent
        if ep.critical_views and len(ep.critical_views) > 50  # Has substantive analysis
        and ep.scores.credibility >= 3
    ]
    
    # Sort by insight (novel ideas) + credibility
    contrarian.sort(
        key=lambda ep: ep.scores.insight * 0.6 + ep.scores.credibility * 0.4,
        reverse=True
    )
    
    return diversify_by_series(contrarian, limit)


def get_new_from_subscriptions(
    episodes: List[Episode],
    user: User,
    limit: int = 10
) -> List[Episode]:
    """
    Latest episodes from user's subscribed series.
    """
    matching = [
        ep for ep in episodes
        if ep.series.id in user.subscribed_series
    ]
    
    # Remove seen
    matching = filter_seen(matching, user)
    
    # Sort by recency (newest first)
    matching.sort(key=lambda ep: ep.published_at, reverse=True)
    
    return matching[:limit]
```

### 3.4 API Endpoints

```python
# mock_api/routers/recommendations.py

from fastapi import APIRouter, Query
from typing import List, Optional
from models.recommendation import RecommendationSection
from algorithms import recommendations as rec
from data import load_episodes, load_user

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

@router.get("/highest-signal", response_model=RecommendationSection)
def highest_signal(
    limit: int = Query(10, le=20),
    days: int = Query(7, le=30)
):
    """Top quality episodes this week (global)."""
    episodes = load_episodes()
    results = rec.get_highest_signal(episodes, limit, days)
    return RecommendationSection(
        section="highest_signal",
        title="💎 Highest Signal This Week",
        subtitle="Top Insight + Credibility across all topics",
        episodes=results
    )

@router.get("/focus", response_model=RecommendationSection)
def insights_for_focus(
    user_id: str,
    limit: int = Query(10, le=20)
):
    """Episodes matching user's category interests."""
    episodes = load_episodes()
    user = load_user(user_id)
    results = rec.get_insights_for_categories(episodes, user, limit)
    
    categories_str = ", ".join(user.category_interests[:2])
    return RecommendationSection(
        section="insights_for_focus",
        title="📊 Insights for Your Focus",
        subtitle=f"Based on {categories_str}",
        episodes=results
    )

@router.get("/tracking/entity/{entity_name}", response_model=RecommendationSection)
def tracking_entity(
    entity_name: str,
    user_id: str,
    limit: int = Query(10, le=20)
):
    """Episodes mentioning a specific company/organization."""
    episodes = load_episodes()
    user = load_user(user_id)
    results = rec.get_tracking_entity(episodes, user, entity_name, limit)
    return RecommendationSection(
        section="tracking_entity",
        title=f"🎯 Tracking: {entity_name}",
        subtitle="Latest high-relevance episodes",
        episodes=results
    )

@router.get("/non-consensus", response_model=RecommendationSection)
def non_consensus(
    limit: int = Query(10, le=20),
    days: int = Query(14, le=30)
):
    """Contrarian views from credible speakers."""
    episodes = load_episodes()
    results = rec.get_non_consensus_ideas(episodes, limit, days)
    return RecommendationSection(
        section="non_consensus",
        title="🔥 Non-Consensus Ideas",
        subtitle="Contrarian views from credible speakers",
        episodes=results
    )

@router.get("/subscriptions", response_model=RecommendationSection)
def from_subscriptions(
    user_id: str,
    limit: int = Query(10, le=20)
):
    """New episodes from subscribed series."""
    episodes = load_episodes()
    user = load_user(user_id)
    results = rec.get_new_from_subscriptions(episodes, user, limit)
    return RecommendationSection(
        section="subscriptions",
        title="📡 New from Your Shows",
        subtitle="Latest from subscribed series",
        episodes=results
    )

@router.get("/discover", response_model=List[RecommendationSection])
def discover_page(user_id: str):
    """Full discover page with all sections."""
    return [
        insights_for_focus(user_id, limit=10),
        tracking_entity("OpenAI", user_id, limit=8),  # Example tracked entity
        non_consensus(limit=8),
        highest_signal(limit=10),
        from_subscriptions(user_id, limit=8)
    ]
```

### 3.5 Response Models

```python
# mock_api/models/recommendation.py

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class SeriesInfo(BaseModel):
    id: str
    name: str
    artwork_url: Optional[str]

class EpisodeScores(BaseModel):
    insight: int  # 1-4
    credibility: int  # 1-4
    information: int  # 1-4

class EpisodeCard(BaseModel):
    id: str
    title: str
    series: SeriesInfo
    published_at: datetime
    duration_seconds: int
    scores: EpisodeScores
    badges: List[str]  # ["high_insight", "high_credibility", "contrarian"]
    key_insight: Optional[str]  # 1-sentence preview
    categories: List[str]
    entity_relevance: Optional[float]  # If from entity tracking

class RecommendationSection(BaseModel):
    section: str
    title: str
    subtitle: str
    episodes: List[EpisodeCard]
```

---

## 4. Phase 3: Mobile Prototype UI

### 4.1 Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Framework | React | Fast iteration, familiar |
| Styling | Tailwind CSS | Mobile-first, rapid prototyping |
| State | React Query | API caching, loading states |
| Hosting | Vercel / Netlify | Free, easy deployment |

### 4.2 Project Structure

```
mobile_prototype/
├── src/
│   ├── App.tsx
│   ├── api/
│   │   └── recommendations.ts   # API client
│   ├── components/
│   │   ├── EpisodeCard.tsx      # Episode card component
│   │   ├── Section.tsx          # Horizontal scroll section
│   │   ├── QualityBadge.tsx     # Insight/Credibility badges
│   │   └── CategoryTag.tsx
│   ├── pages/
│   │   ├── Discover.tsx         # Main discover page
│   │   └── EpisodeDetail.tsx    # Episode detail view
│   └── styles/
│       └── globals.css
├── package.json
└── tailwind.config.js
```

### 4.3 Key Components

#### Episode Card

```tsx
// src/components/EpisodeCard.tsx

interface EpisodeCardProps {
  episode: Episode;
  onPress: () => void;
}

export function EpisodeCard({ episode, onPress }: EpisodeCardProps) {
  return (
    <div 
      className="w-72 bg-white rounded-xl shadow-sm p-4 flex-shrink-0"
      onClick={onPress}
    >
      {/* Header: Artwork + Title */}
      <div className="flex gap-3 mb-3">
        <img 
          src={episode.series.artwork_url} 
          className="w-16 h-16 rounded-lg"
          alt={episode.series.name}
        />
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm line-clamp-2">
            {episode.title}
          </h3>
          <p className="text-xs text-gray-500">{episode.series.name}</p>
          <p className="text-xs text-gray-400">
            {formatDate(episode.published_at)} • {formatDuration(episode.duration_seconds)}
          </p>
        </div>
      </div>
      
      {/* Quality Badges */}
      <div className="flex gap-2 mb-2">
        {episode.badges.includes('high_insight') && (
          <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">
            💎 High Insight
          </span>
        )}
        {episode.badges.includes('high_credibility') && (
          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
            ⭐ High Credibility
          </span>
        )}
        {episode.badges.includes('contrarian') && (
          <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full">
            🔥 Contrarian
          </span>
        )}
      </div>
      
      {/* Key Insight Preview */}
      {episode.key_insight && (
        <p className="text-xs text-gray-600 line-clamp-2">
          {episode.key_insight}
        </p>
      )}
      
      {/* Category Tag */}
      <div className="mt-2">
        <span className="text-xs text-gray-400">
          🏷️ {episode.categories[0]}
        </span>
      </div>
    </div>
  );
}
```

#### Discover Page

```tsx
// src/pages/Discover.tsx

import { useQuery } from '@tanstack/react-query';
import { fetchDiscoverPage } from '../api/recommendations';
import { Section } from '../components/Section';
import { EpisodeCard } from '../components/EpisodeCard';

export function Discover() {
  const { data: sections, isLoading } = useQuery({
    queryKey: ['discover'],
    queryFn: () => fetchDiscoverPage('user_mock_1')
  });

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <header className="sticky top-0 bg-white border-b px-4 py-3 flex items-center justify-between">
        <h1 className="text-xl font-bold">Discover</h1>
        <button className="p-2">🔍</button>
      </header>

      {/* Sections */}
      <div className="space-y-6 py-4">
        {sections?.map((section) => (
          <Section key={section.section} title={section.title} subtitle={section.subtitle}>
            <div className="flex gap-4 overflow-x-auto px-4 pb-2 scrollbar-hide">
              {section.episodes.map((episode) => (
                <EpisodeCard 
                  key={episode.id} 
                  episode={episode}
                  onPress={() => navigate(`/episode/${episode.id}`)}
                />
              ))}
            </div>
          </Section>
        ))}
      </div>

      {/* Bottom Nav */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t flex justify-around py-3">
        <button className="flex flex-col items-center text-blue-600">
          <span>🏠</span>
          <span className="text-xs">Discover</span>
        </button>
        <button className="flex flex-col items-center text-gray-400">
          <span>🔍</span>
          <span className="text-xs">Search</span>
        </button>
        <button className="flex flex-col items-center text-gray-400">
          <span>🔖</span>
          <span className="text-xs">Saved</span>
        </button>
        <button className="flex flex-col items-center text-gray-400">
          <span>👤</span>
          <span className="text-xs">Profile</span>
        </button>
      </nav>
    </div>
  );
}
```

### 4.4 Mobile-First Design Specs

| Element | Specification |
|---------|---------------|
| Card width | 288px (w-72) fixed, horizontal scroll |
| Card padding | 16px |
| Artwork size | 64x64px rounded-lg |
| Title font | 14px semibold, max 2 lines |
| Badge font | 12px with colored background |
| Section gap | 24px vertical between sections |
| Bottom nav | Fixed, 48px height |

---

## 5. Testing Plan

### 5.1 Algorithm Testing

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| Highest Signal returns quality-sorted | All episodes | Top insight+credibility first |
| Category filtering works | User with AI interest | Only AI-related episodes |
| Entity tracking filters by relevance | "OpenAI" | Episodes with OpenAI relevance >= 3 |
| Non-consensus requires credibility | All episodes | Only credibility >= 3 with critical_views |
| Diversification limits series | 10 episodes from 2 series | Max 2 per series |
| Seen filtering excludes viewed | User with 5 seen | Those 5 excluded |

### 5.2 API Testing

```bash
# Test highest signal
curl http://localhost:8000/api/recommendations/highest-signal?limit=5

# Test focus with user
curl http://localhost:8000/api/recommendations/focus?user_id=user_mock_1&limit=5

# Test entity tracking
curl http://localhost:8000/api/recommendations/tracking/entity/OpenAI?user_id=user_mock_1

# Test full discover page
curl http://localhost:8000/api/recommendations/discover?user_id=user_mock_1
```

### 5.3 UI Testing

| Scenario | Expected Behavior |
|----------|-------------------|
| Cold load | Show loading spinner, then sections |
| Horizontal scroll | Smooth scroll, no jank |
| Card tap | Navigate to episode detail |
| Quality badges | Correct badges based on scores |
| Empty section | Hide section or show "No results" |

---

## 6. Execution Timeline

### Week 1: Data Extraction

| Day | Task | Output |
|-----|------|--------|
| 1 | Set up extraction scripts | `extraction/` folder |
| 2-3 | Extract 50 episodes via browser MCP | `mock_data/episodes_batch1.json` |
| 4-5 | Extract remaining episodes + series | `mock_data/episodes.json`, `series.json` |

### Week 2: Mock API

| Day | Task | Output |
|-----|------|--------|
| 1 | FastAPI scaffold + data loading | `mock_api/` structure |
| 2 | Implement scoring + filtering algorithms | `algorithms/` folder |
| 3 | Implement recommendation endpoints | `routers/recommendations.py` |
| 4 | Add mock users + feedback endpoints | `routers/feedback.py` |
| 5 | Testing + documentation | `tests/`, README |

### Week 3: Mobile Prototype

| Day | Task | Output |
|-----|------|--------|
| 1 | React + Tailwind setup | `mobile_prototype/` structure |
| 2 | Episode card + section components | `components/` |
| 3 | Discover page with API integration | `pages/Discover.tsx` |
| 4 | Episode detail page | `pages/EpisodeDetail.tsx` |
| 5 | Polish + deploy to Vercel | Live demo URL |

---

## 7. Success Criteria

### 7.1 Data Extraction

- [ ] 50+ episodes extracted with full metadata
- [ ] All quality scores captured (insight, credibility, information)
- [ ] Entities and people extracted with relevance
- [ ] Categories captured (major + subcategories)
- [ ] Critical views text captured

### 7.2 Mock API

- [ ] All 5 recommendation endpoints functional
- [ ] Algorithms return sensible results
- [ ] Filtering (seen, not interested) works
- [ ] Diversification prevents series dominance
- [ ] Response times < 100ms

### 7.3 Mobile Prototype

- [ ] Discover page renders all sections
- [ ] Horizontal scroll works smoothly
- [ ] Quality badges display correctly
- [ ] Episode cards show key insight preview
- [ ] Mobile-responsive (375px - 428px width)

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Browser MCP unreliable | Delays extraction | Manual extraction fallback |
| Serafis UI changes | Breaks extraction scripts | Build resilient selectors |
| Insufficient episode variety | Algorithms don't generalize | Target diverse categories |
| Missing critical_views data | Non-consensus section empty | Fallback to high-insight only |

---

## Appendix A: Browser MCP Commands Reference

```
browser_navigate(url)      - Navigate to URL
browser_snapshot()         - Get page structure
browser_click(ref)         - Click element by ref
browser_type(ref, text)    - Type into input
browser_wait(seconds)      - Wait for page load
browser_scroll(direction)  - Scroll page
```

---

## Appendix B: Sample Mock User Profiles

```json
[
  {
    "id": "user_prosumer_ai",
    "name": "AI Prosumer",
    "category_interests": ["Technology & AI", "Startups"],
    "subscribed_series": ["series_20vc", "series_a16z", "series_nopriors"],
    "activity": [],
    "bookmarks": [],
    "not_interested": []
  },
  {
    "id": "user_prosumer_crypto",
    "name": "Crypto Prosumer",
    "category_interests": ["Crypto & Web3", "Technology & AI"],
    "subscribed_series": ["series_allin", "series_bankless"],
    "activity": [],
    "bookmarks": [],
    "not_interested": []
  },
  {
    "id": "user_prosumer_markets",
    "name": "Markets Prosumer",
    "category_interests": ["Public Markets", "Macroeconomics"],
    "subscribed_series": ["series_investbest", "series_acquired"],
    "activity": [],
    "bookmarks": [],
    "not_interested": []
  }
]
```
