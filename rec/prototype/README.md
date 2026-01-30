# Serafis Mobile Recommendation Prototype

A mobile-first React prototype demonstrating the Serafis recommendation engine.

## Quick Start

### 1. Start the API Server

```bash
cd ../mock_api
python3 server.py
```

API runs at: http://localhost:8000

### 2. Start the React App

```bash
cd prototype
npm install
npm run dev
```

App runs at: http://localhost:5173

## Features

### Discover Page Sections

| Section | Description |
|---------|-------------|
| 📊 Insights for You | Episodes matching user's category interests |
| 💎 Highest Signal This Week | Top quality episodes globally |
| 🔥 Non-Consensus Ideas | Contrarian views from credible speakers |
| 📡 New from Your Shows | Latest from subscribed series |
| 🌟 Trending in [Category] | Popular in user's interest category |

### Episode Cards

- **Quality Badges**: High Insight, High Credibility, Data-Rich, Contrarian
- **Key Insight Preview**: 1-sentence preview from episode analysis
- **Category Tags**: Major category classification
- **Actions**: Save (bookmark) and "Not for me" (negative feedback)

### User Profiles

Switch between mock user profiles to see personalized recommendations:

| Profile | Interests |
|---------|-----------|
| 🤖 AI Prosumer | Technology & AI, Startups |
| ₿ Crypto Prosumer | Crypto & Web3, Technology |
| 📈 Markets Prosumer | Macro & Markets, Venture |
| 👤 Cold Start | No preferences (global recommendations) |

## Tech Stack

- **React** with Vite
- **Tailwind CSS** for styling
- **FastAPI** backend (mock_api)

## Mobile Testing

1. Open http://localhost:5173 in Chrome
2. Open DevTools (F12)
3. Toggle device toolbar (Ctrl+Shift+M)
4. Select iPhone or any mobile device

## API Endpoints

All endpoints require `user_id` query parameter:

```
GET /api/recommendations/discover?user_id=user_prosumer_ai
GET /api/recommendations/insights-for-you?user_id=...
GET /api/recommendations/highest-signal?user_id=...
GET /api/recommendations/non-consensus?user_id=...
GET /api/recommendations/new-from-shows?user_id=...
GET /api/recommendations/trending/{category}?user_id=...
POST /api/feedback/not-interested
```

## Project Structure

```
prototype/
├── src/
│   ├── api.js                    # API client
│   ├── App.jsx                   # Main app with user selector
│   ├── components/
│   │   ├── Badge.jsx             # Quality badges
│   │   ├── DiscoverPage.jsx      # Main discover page
│   │   ├── EpisodeCard.jsx       # Episode card component
│   │   └── RecommendationSection.jsx  # Horizontal scroll section
│   ├── index.css                 # Tailwind styles
│   └── main.jsx                  # Entry point
├── index.html
├── package.json
├── tailwind.config.js
└── README.md
```
