# Serafis Mock Recommendation API

A functional mock API for testing the Serafis recommendation algorithms without backend access.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Build dataset from extracted API responses
python build_dataset.py

# Start the server
python server.py
# Or: uvicorn server:app --reload --port 8000

# Server runs at http://localhost:8000
```

## Data Extraction

The dataset is built from JSON responses captured from the Serafis web app.

### Folder Structure

```
mock_api/
├── org_search/           # Organization search responses
│   ├── openai_response.json
│   ├── google_response.json
│   └── nvidia_response.json
├── people_search/        # People search responses
│   ├── samaltman_response.json
│   ├── elonmusk_response.json
│   └── ...
├── theme_search/         # Theme search responses
│   ├── major_categories/
│   │   ├── crypto_web3_response.json
│   │   └── startups_growth_founder_journeys_response.json
│   └── sub_categories/
│       ├── energyclimate_response.json
│       └── defensetech_response.json
├── data/                 # Generated dataset (after running build_dataset.py)
│   ├── episodes.json     # Unified episode data
│   ├── series.json       # Series metadata
│   ├── mock_users.json   # Test user profiles
│   └── stats.json        # Dataset statistics
├── build_dataset.py      # Dataset builder script
├── server.py             # FastAPI server
└── requirements.txt      # Dependencies
```

### How to Extract More Data

1. Open the Serafis web app (app.serafis.ai)
2. Open browser DevTools → Network tab
3. Run a search (org, people, or theme)
4. Find the POST request to `agent.superblocks.com/v2/execute`
5. Copy the response JSON
6. Save to appropriate folder (e.g., `org_search/anthropic_response.json`)
7. Run `python build_dataset.py` to rebuild the dataset

## API Endpoints

### Recommendation Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/recommendations/discover?user_id=...` | Full discover page with all sections |
| `GET /api/recommendations/insights-for-you?user_id=...` | Category-matched episodes |
| `GET /api/recommendations/highest-signal?user_id=...` | Top quality episodes (global) |
| `GET /api/recommendations/non-consensus?user_id=...` | Contrarian views from credible speakers |
| `GET /api/recommendations/new-from-shows?user_id=...` | From subscribed series |
| `GET /api/recommendations/trending/{category}?user_id=...` | Popular in category |

### Other Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | API info and stats |
| `GET /api/users` | List mock users |
| `GET /api/episodes?limit=20` | List episodes |
| `GET /api/series` | List series |
| `POST /api/feedback/not-interested` | Mark episode as not interested |

## Mock Users

| User ID | Category Interests | Subscribed Series |
|---------|-------------------|-------------------|
| `user_prosumer_ai` | Startups & Founders | a16z, 20VC, Unsupervised Learning |
| `user_prosumer_crypto` | Crypto, Startups | Unchained, Bankless |
| `user_prosumer_markets` | Startups & Founders | Invest Like Best, All-In |
| `user_cold_start` | (none) | (none) |

## Example Usage

```bash
# Get full discover page for a user
curl "http://localhost:8000/api/recommendations/discover?user_id=user_prosumer_crypto"

# Get highest signal episodes
curl "http://localhost:8000/api/recommendations/highest-signal?user_id=user_prosumer_ai&limit=5"

# Get trending in a category
curl "http://localhost:8000/api/recommendations/trending/Crypto%20%26%20Web3?user_id=user_prosumer_crypto"
```

## Algorithm Details

See [recommendation_engine_spec.md](../recommendation_engine_spec.md) for full algorithm specifications.

### Quality Score Formula

```
quality = (insight * 0.45 + credibility * 0.40 + information * 0.15) / 4.0
```

### Badge Thresholds

- 💎 High Insight: `insight_score >= 3`
- ⭐ High Credibility: `credibility_score >= 3`
- 📊 Data-Rich: `information_score >= 3`
- 🔥 Contrarian: Has critical views

## Current Dataset Stats

- **387 unique episodes**
- **58 series**
- **Average insight score:** 2.54
- **Average credibility score:** 3.16

## Interactive API Docs

When the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
