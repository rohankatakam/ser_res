# Serafis Mock Recommendation API — V1.1

A functional mock API for testing the Serafis "For You" recommendation algorithms with semantic matching.

## What's New in V1.1

- **2-Stage Pipeline**: Pre-filtering + semantic matching
- **Embedding-based recommendations**: Cosine similarity between user activity vector and episode embeddings
- **Clean embedding strategy**: Only `title + key_insights` for noise reduction
- **Real-time personalization**: Recommendations update as user engages

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the server
python server.py
# Or: uvicorn server:app --reload --port 8000

# 3. (Optional) Generate embeddings for semantic matching
export OPENAI_API_KEY="sk-..."
python generate_embeddings.py

# Server runs at http://localhost:8000
```

## Embedding Generation

For semantic matching to work, you need to generate embeddings:

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="sk-your-key-here"

# Generate embeddings for all episodes (~$0.10 cost)
python generate_embeddings.py

# Check what would be done without calling API
python generate_embeddings.py --dry-run

# Force regenerate all embeddings
python generate_embeddings.py --force
```

This creates `data/embeddings.json` with 1536-dim vectors for each episode.

**Without embeddings**: The API falls back to quality-based ranking (C+I score).

## V1.1 Algorithm

### Stage A: Candidate Pool Pre-Selection

```
All Episodes (561)
    ↓ Filter: Credibility ≥ 2
    ↓ Filter: C + I ≥ 5
    ↓ Filter: Published within 30 days
    ↓ Filter: Not in user's excluded_ids
    ↓ Sort by C+I descending
    ↓ Take top 50
Candidate Pool (50 episodes)
```

### Stage B: Semantic Matching

```
User Activity Vector ←── Mean of last 5 engagement embeddings
        ↓
        ↓ Cosine similarity against each candidate
        ↓ Sort by similarity descending
        ↓ Take top 10
Final Recommendations (10 episodes)
```

## API Endpoints

### V1.1 Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/recommendations/for-you` | POST | Semantic matching recommendations |
| `GET /api/episodes` | GET | List all episodes (with pagination) |
| `GET /api/episodes/{id}` | GET | Full episode details |
| `GET /api/stats` | GET | Data statistics and config |

### For You Request

```bash
curl -X POST http://localhost:8000/api/recommendations/for-you \
  -H "Content-Type: application/json" \
  -d '{
    "engagements": [
      {"episode_id": "B7d9XwUOKOuoH7R8Tnzi", "type": "click", "timestamp": "2026-02-04T10:00:00Z"},
      {"episode_id": "lMI5IYECEDErYBlmWMSi", "type": "bookmark", "timestamp": "2026-02-04T09:00:00Z"}
    ],
    "excluded_ids": ["B7d9XwUOKOuoH7R8Tnzi", "lMI5IYECEDErYBlmWMSi"]
  }'
```

### Response

```json
{
  "section": "for_you",
  "title": "For You",
  "subtitle": "Based on your recent activity",
  "algorithm": "v1.1_semantic",
  "cold_start": false,
  "episodes": [
    {
      "id": "xyz123",
      "title": "Episode Title",
      "similarity_score": 0.847,
      "scores": {"insight": 3, "credibility": 4, ...},
      ...
    }
  ],
  "debug": {
    "candidates_count": 47,
    "user_vector_episodes": 5,
    "top_similarity_scores": [0.847, 0.823, 0.801, ...]
  }
}
```

### Legacy Endpoints (still available)

| Endpoint | Description |
|----------|-------------|
| `GET /api/recommendations/highest-signal` | Top quality episodes |
| `GET /api/recommendations/non-consensus` | Contrarian views |
| `GET /api/recommendations/discover` | Full discover page |

## Frontend Testing Harness

A React frontend is available in `../prototype/`:

```bash
cd ../prototype
npm install
npm run dev
# Open http://localhost:5173
```

### Features

- Browse all episodes
- Click episodes to view details and signal engagement
- View "For You" recommendations updating in real-time
- See similarity scores for each recommendation
- Debug panel showing user activity vector
- Cold start on refresh (no persistence)

## Folder Structure

```
mock_api/
├── data/
│   ├── episodes.json       # 561 episodes with metadata
│   ├── series.json         # 58 podcast series
│   ├── mock_users.json     # Test user profiles
│   └── embeddings.json     # Pre-computed embeddings (generated)
├── server.py               # FastAPI server (V1.1)
├── generate_embeddings.py  # Embedding generation script
├── build_dataset.py        # Dataset builder (from raw responses)
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Configuration

Default parameters in `server.py`:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `CREDIBILITY_FLOOR` | 2 | Minimum credibility score |
| `COMBINED_FLOOR` | 5 | Minimum C+I score |
| `FRESHNESS_WINDOW_DAYS` | 30 | Max age for candidates |
| `CANDIDATE_POOL_SIZE` | 50 | Pre-filtered pool size |
| `USER_VECTOR_LIMIT` | 5 | Engagements for user vector |

## Specs & Documentation

- **V1.1 Spec**: `../FOR_YOU_V1_1_SPEC.md`
- **Testing Strategy**: `../TESTING_STRATEGY.md`
- **Original Spec**: `../FOR_YOU_SPEC_FINAL.html`
- **Testing Guide**: `../FOR_YOU_TESTING_GUIDE.md`

## Current Dataset Stats

- **561 unique episodes**
- **58 series**
- **Average insight score:** ~2.5
- **Average credibility score:** ~3.2
- **Episodes with critical_views:** ~150

## Interactive API Docs

When the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
