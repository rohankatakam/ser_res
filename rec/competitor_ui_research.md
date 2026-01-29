# Podcast App UI Research — Spotify & Apple Podcasts

> *Detailed documentation of recommendation UI patterns from Spotify and Apple Podcasts for design reference.*

**Date:** January 29, 2026  
**Author:** Rohan Katakam  
**Purpose:** UI/UX reference for Serafis mobile app design

---

## 1. Spotify Podcast Recommendations

### 1.1 Section Architecture

| Section | Content Type | Algorithm | UI Pattern |
|---------|--------------|-----------|------------|
| **Subscribed Shows Bar** | Series | User subscriptions | Horizontal icon strip at top |
| **Featured Episodes** | Episodes | Editorial + trending | Large cards with rich metadata |
| **"Popular with listeners of [X]"** | Series | Collaborative filtering | Horizontal scroll carousel |
| **Colored Episode Cards** | Episodes | Trending/curated | Full-bleed cards with descriptions |

### 1.2 Episode Card Design

Spotify uses large, visually prominent episode cards:

```
┌─────────────────────────────────────────────────────────────┐
│  Episode Title (bold, 2 lines max)                          │
│  ▶ Video • Series Name                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    [LARGE ARTWORK]                          │
│                    (Square, prominent)                      │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Jan 21 • 31 min 59 sec • (0:00) Description preview        │
│  text that continues for several lines giving context       │
│  on what this episode covers and who is featured...         │
└─────────────────────────────────────────────────────────────┘
```

**Metadata displayed:**
- Episode title (bold, prominent)
- Content type badge ("Video" or "Episode")
- Series name
- Large square artwork
- Publish date (e.g., "Jan 21")
- Duration (precise: "31 min 59 sec")
- Description snippet with timestamp references (e.g., "(0:00)", "(1:31)")

### 1.3 Series Card Design

For series recommendations ("Popular with listeners of X"):

```
┌────────────────────────────┐
│  ┌──────────────────────┐  │
│  │                      │  │
│  │      [ARTWORK]       │  │
│  │      (Square)        │  │
│  │                      │  │
│  └──────────────────────┘  │
│  Series Name               │
│  Publisher Name            │
└────────────────────────────┘
```

**Metadata displayed:**
- Square artwork (large, prominent)
- Series name
- Publisher name

### 1.4 Subscribed Shows Bar

At the top of the Podcasts tab:

```
┌─────────────────────────────────────────────────────────────┐
│  [All] [Music] [Podcasts] [Audiobooks]    ← Content filters │
├─────────────────────────────────────────────────────────────┤
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                   │
│  │ 📷  │ │ 📷  │ │ 📷  │ │ 📷  │ │ 📷  │  → scroll         │
│  │     │ │  •  │ │     │ │     │ │     │  (• = new episode)│
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘                   │
│  The Daily  Exchanges  ...                                  │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Small circular/square thumbnails
- Blue dot indicator for new episodes
- Horizontal scroll
- Series name below thumbnail

### 1.5 "Popular with listeners of [X]" Section

Collaborative filtering section:

```
┌─────────────────────────────────────────────────────────────┐
│  Popular with listeners of                                  │
│  The Daily                                    [Show all]    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ The     │ │ WSJ     │ │ Pod Save│ │ The     │  → scroll │
│  │ Opinions│ │ What's  │ │ America │ │ Journal │           │
│  │         │ │ News    │ │         │ │         │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
│  The Opinions WSJ What's  Pod Save   The Journal            │
│  NY Times Op  Wall Street Crooked    Wall Street            │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Reference series shown in header
- Horizontal carousel of related series
- Series artwork + name + publisher

### 1.6 Featured Episode Cards (Large Format)

Full-width colored cards for featured content:

```
┌─────────────────────────────────────────────────────────────┐
│  ┌───────────────────────────────────────────────────────┐  │
│  │                                                       │  │
│  │  Trump's LA Rebuild TAKEOVER,                         │  │
│  │  Google's $68M Spying Case, UPS...                    │  │
│  │  ▶ Video • PBD Podcast                                │  │
│  │                                                       │  │
│  │         [LARGE ARTWORK / THUMBNAIL]                   │  │
│  │                                                       │  │
│  │                                                       │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  (Similar cards in horizontal scroll or grid)               │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Colored background (extracted from artwork)
- Large episode thumbnail
- Episode title (multi-line)
- Video/Episode badge
- Series name

---

## 2. Apple Podcasts Recommendations

### 2.1 Section Architecture

| Section | Content Type | Algorithm | UI Pattern |
|---------|--------------|-----------|------------|
| **"Your Top Shows"** | Series | User listening history | Horizontal scroll, category + frequency |
| **"You Might Like"** | Series | Content-based similarity | Horizontal scroll, category + frequency |
| **"New Shows for You"** | Series | Personalized discovery | Cards with ratings + descriptions |
| **"More to Discover"** | Episodes | Personalized | Grid with date + duration |
| **"If You Like [X]"** | Series | Explicit similarity | Category matching |
| **"Essential Listens"** | Series | Curated/popular | Mixed categories |
| **"Channels to Try"** | Publishers | Editorial curation | Brand logos |

### 2.2 "Your Top Shows" Section

User's most-listened series:

```
┌─────────────────────────────────────────────────────────────┐
│  Your Top Shows >                                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────┐ │
│  │ A16Z    │ │ ai+a16z │ │ The     │ │ Y Comb  │ │ Joe   │ │
│  │ SHOW    │ │         │ │ Daily   │ │         │ │ Rogan │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └───────┘ │
│  Technology  Technology  Daily News  Technology  Comedy    │
│  Updated     Updated     Updated     Updated     Updated   │
│  Daily       Weekly      Daily       Biweekly    Semiweekly│
└─────────────────────────────────────────────────────────────┘
```

**Metadata displayed:**
- Square artwork
- Series name (implicit via artwork)
- Category tag (e.g., "Technology", "Daily News", "Comedy")
- Update frequency (e.g., "Updated Daily", "Updated Weekly")

### 2.3 "You Might Like" Section

Content-based series recommendations:

```
┌─────────────────────────────────────────────────────────────┐
│  You Might Like >                                           │
│  Based on your listening.                                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────┐ │
│  │ No      │ │ This Wk │ │ BG²     │ │ Latent  │ │ Invest│ │
│  │ Priors  │ │ Startups│ │         │ │ Space   │ │ Best  │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └───────┘ │
│  Technology  Technology  Technology  Technology  Investing │
│  Updated Wk  Updated D   Updated Wk  Updated Wk  Updated Wk│
└─────────────────────────────────────────────────────────────┘
```

**Same format as "Your Top Shows"**

### 2.4 "New Shows for You" Section

New series discovery with ratings:

```
┌─────────────────────────────────────────────────────────────┐
│  New Shows for You >                                        │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────────┐ ┌───────────────────┐ ┌─────────────│
│  │                   │ │                   │ │             │
│  │    [ARTWORK]      │ │    [ARTWORK]      │ │  [ARTWORK]  │
│  │                   │ │                   │ │             │
│  │                   │ │                   │ │             │
│  ├───────────────────┤ ├───────────────────┤ ├─────────────│
│  │ From turning      │ │ The internet has  │ │ James Patt  │
│  │ points to trans-  │ │ warped public     │ │ erson—the   │
│  │ formations, NXT   │ │ life: Politicians │ │ world's     │
│  │ Chapter with T.D. │ │ behave like inf-  │ │ bestselling │
│  │ Jakes explores... │ │ luencers, the...  │ │ author...   │
│  ├───────────────────┤ ├───────────────────┤ ├─────────────│
│  │ ★ 4.9 (165)       │ │ ★ 4.5 (1.1K)      │ │ ★ 3.9 (34)  │
│  │ SELF-IMPROVEMENT  │ │ TECHNOLOGY        │ │ PERSONAL    │
│  ├───────────────────┤ ├───────────────────┤ ├─────────────│
│  │ [▶ Trailer]  [+]  │ │ [▶ Trailer]  [+]  │ │ [▶ Trailer] │
│  └───────────────────┘ └───────────────────┘ └─────────────│
└─────────────────────────────────────────────────────────────┘
```

**Metadata displayed:**
- Large artwork
- Description preview (2-3 lines)
- **User ratings** (★ 4.5 with review count) — unique to Apple
- Category tag (ALL CAPS)
- Trailer button
- Follow/Add button (+)

### 2.5 "More to Discover" Section

Episode recommendations in grid format:

```
┌─────────────────────────────────────────────────────────────┐
│  More to Discover >                                         │
│  Based on your listening.                                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────┐ ┌─────────────────────────│
│  │ ┌────┐  JAN 21              │ │ ┌────┐  JAN 22          │
│  │ │    │  Context Engineering │ │ │    │  No Priors Live: │
│  │ │ 📷 │  Our Way to Long-    │ │ │ 📷 │  Building Durable│
│  │ │    │  Horizon Agents:     │ │ │    │  Software in the │
│  │ └────┘  LangChain's Harrison│ │ └────┘  AI Age with...  │
│  │         Chase, cofounder... │ │         Why are there   │
│  │         ─────────────────── │ │         only a handful  │
│  │         40 min              │ │         37 min          │
│  ├─────────────────────────────┤ ├─────────────────────────│
│  │ ┌────┐  3D AGO              │ │ ┌────┐  3D AGO          │
│  │ │    │  Jason Momoa         │ │ │    │  20VC: From Only │
│  │ │ 📷 │  Jason Momoa is an   │ │ │ 📷 │  OpenAI to Die-  │
│  │ │    │  actor and producer  │ │ │    │  Hard Anthropic: │
│  │ └────┘  known for Game of   │ │ └────┘  The Downfall... │
│  │         Thrones, Aquaman... │ │         ─────────────── │
│  │         1h 27m              │ │         1h 3m           │
│  └─────────────────────────────┘ └─────────────────────────│
└─────────────────────────────────────────────────────────────┘
```

**Metadata displayed:**
- Small square thumbnail (left-aligned)
- Relative date ("JAN 21" or "3D AGO")
- Episode title (multi-line)
- Description snippet
- Duration

### 2.6 "If You Like [X]" Section

Explicit similarity-based recommendations:

```
┌─────────────────────────────────────────────────────────────┐
│  If You Like                                                │
│  No Priors: Artificial Intelligence | Technology | Startups>│
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────┐ │
│  │ Latent  │ │ ai+a16z │ │ Dwarkesh│ │ A16Z    │ │ 20VC  │ │
│  │ Space   │ │         │ │ Podcast │ │ Show    │ │       │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └───────┘ │
│  Technology  Technology  Technology  Technology  Investing │
│  Updated Wk  Updated Wk  Updated Wk  Updated D   Updated D │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Reference series in header with category tags
- Related series with same format as "You Might Like"
- Transparent reasoning (user understands why these are recommended)

### 2.7 "Channels to Try" Section

Publisher/network-level recommendations:

```
┌─────────────────────────────────────────────────────────────┐
│  Channels to Try >                                          │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐   │
│  │           │ │           │ │           │ │           │   │
│  │ The New   │ │ DR.       │ │   TIM     │ │ SiriusXM  │   │
│  │ York      │ │ HYMAN+    │ │ FERRISS   │ │ PODCASTS  │   │
│  │ Times     │ │           │ │           │ │           │   │
│  │           │ │           │ │           │ │           │   │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Brand/publisher logos
- Larger cards than series
- No metadata (brand recognition)

---

## 3. Comparison Summary

### 3.1 Episode Card Comparison

| Element | Spotify | Apple |
|---------|---------|-------|
| Artwork size | Large, prominent | Small thumbnail |
| Title | Bold, 2 lines | Multi-line allowed |
| Date format | "Jan 21" | "JAN 21" or "3D AGO" |
| Duration | Precise ("31 min 59 sec") | Rounded ("40 min") |
| Description | Long preview | Short preview |
| Quality signal | None | None |
| Video badge | Yes | No |

### 3.2 Series Card Comparison

| Element | Spotify | Apple |
|---------|---------|-------|
| Artwork | Square, large | Square, medium |
| Series name | Below artwork | Below artwork |
| Publisher | Yes | No |
| Category | No | Yes |
| Update frequency | No | Yes |
| User ratings | No | Yes (on discovery cards) |

### 3.3 Section Types

| Section Type | Spotify | Apple |
|--------------|---------|-------|
| Subscriptions | Bar at top | "Your Top Shows" |
| Personalized episodes | Featured cards | "More to Discover" |
| Series recommendations | "Popular with listeners of" | "You Might Like" |
| Similarity-based | — | "If You Like [X]" |
| New discovery | — | "New Shows for You" |
| Curated | — | "Essential Listens" |
| Publisher-level | — | "Channels to Try" |

---

## 4. UI Patterns for Serafis

### 4.1 Patterns to Adopt

| Pattern | Source | Why |
|---------|--------|-----|
| Date • Duration format | Spotify | Clean, scannable |
| Description previews | Both | Context before clicking |
| Category tags on cards | Apple | Quick topic identification |
| Horizontal scroll carousels | Both | Mobile-friendly |
| Large artwork | Both | Visual appeal |
| Explicit similarity framing | Apple | "If You Like X" is transparent |

### 4.2 Patterns to Skip

| Pattern | Source | Why Skip |
|---------|--------|----------|
| Collaborative filtering | Spotify | Requires massive user base |
| User ratings | Apple | Serafis has AI quality scores instead |
| Trailers | Apple | Not core value for research tool |
| Publisher channels | Apple | Lower priority |
| Video badges | Spotify | Serafis doesn't differentiate video |

### 4.3 Serafis-Specific Additions

| Element | Description | Competitive Advantage |
|---------|-------------|----------------------|
| **Quality badges** | 💎 High Insight, ⭐ High Credibility | Neither competitor has this |
| **Key insight preview** | 1-sentence insight instead of description | Research-oriented value |
| **Entity relevance** | "OpenAI discussed (High Relevance)" | Entity-based discovery |
| **Contrarian flag** | 🔥 badge for non-consensus ideas | Unique to Serafis |

---

## 5. Screenshot References

Screenshots analyzed (stored in project assets):

| File | Platform | Content |
|------|----------|---------|
| `image-009e55ab-*.png` | Spotify | Episode cards with metadata |
| `image-47a72203-*.png` | Spotify | "Popular with listeners of" section |
| `image-297ee313-*.png` | Apple | "Your Top Shows" and "You Might Like" |
| `image-239dec86-*.png` | Apple | "New Shows for You" and "More to Discover" |
| `image-6d2229e5-*.png` | Apple | "If You Like X" and "Channels to Try" |

---

## 6. Detailed Observations

### 6.1 Spotify Strengths

1. **Rich metadata display** — Date, duration, description all visible
2. **Large, visually appealing artwork** — Strong visual hierarchy
3. **Collaborative filtering at scale** — "Popular with listeners of X" is powerful
4. **Video differentiation** — Badge system for content types
5. **Precise timestamps** — Description includes "(0:00)" markers

### 6.2 Spotify Weaknesses

1. **No quality/insight scoring** — Popular ≠ valuable
2. **Generic content** — Not investor-focused
3. **No entity-based discovery** — Can't search by company
4. **No speaker credibility signals** — All speakers treated equally

### 6.3 Apple Strengths

1. **User ratings** — ★ 4.5 (1.1K) provides social proof
2. **Category tags prominently displayed** — Easy topic identification
3. **Update frequency shown** — "Updated Weekly" sets expectations
4. **"If You Like X" framing** — Transparent recommendation reasoning
5. **Clean, information-dense layout** — Efficient use of space

### 6.4 Apple Weaknesses

1. **No quality/insight scoring** — Ratings can be gamed
2. **Generic content** — Not investor-focused
3. **No entity-based discovery** — Can't search by company
4. **No speaker credibility signals** — Ratings don't reflect expertise
