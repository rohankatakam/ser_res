"""
Mock Episodes API — Firestore-like episode catalog for testing.

Serves episodes and series from the file-based dataset (e.g. datasets/eval_909_feb2026)
so you can test the same contract that production will use (Firestore or HTTP API)
without touching Firestore.

Run:
  From repo root:
    python -m server.mock_episodes_api
  Or:
    uvicorn server.mock_episodes_api:app --reload --port 8001

  Then point the main server at it with EPISODE_SOURCE=http and EPISODES_API_URL=http://localhost:8001
"""

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

# Default: dataset path relative to repo root (parent of server/)
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = REPO_ROOT / "datasets" / "eval_909_feb2026"


def _load_data():
    """Load episodes and series from DATASET_PATH env or default."""
    path = os.environ.get("DATASET_PATH", str(DEFAULT_DATASET))
    base = Path(path)
    if not base.exists():
        raise FileNotFoundError(f"Dataset path not found: {base}")

    episodes_path = base / "episodes.json"
    series_path = base / "series.json"
    if not episodes_path.exists():
        raise FileNotFoundError(f"episodes.json not found in {base}")

    with open(episodes_path) as f:
        episodes = json.load(f)
    series = []
    if series_path.exists():
        with open(series_path) as f:
            series = json.load(f)

    # Build lookups
    episode_map = {e["id"]: e for e in episodes}
    episode_by_content_id = {e["content_id"]: e for e in episodes if e.get("content_id")}
    return episodes, series, episode_map, episode_by_content_id


# Load once at startup
_episodes: list = []
_series: list = []
_episode_map: dict = {}
_episode_by_content_id: dict = {}


app = FastAPI(
    title="Mock Episodes API",
    description="Firestore-like episode catalog for testing (data from datasets/eval_909_feb2026)",
    version="1.0.0",
)


@app.on_event("startup")
def startup():
    global _episodes, _series, _episode_map, _episode_by_content_id
    try:
        _episodes, _series, _episode_map, _episode_by_content_id = _load_data()
        print(f"Mock Episodes API: loaded {len(_episodes)} episodes, {len(_series)} series")
    except FileNotFoundError as e:
        print(f"WARNING: {e}. Set DATASET_PATH to a folder containing episodes.json and optional series.json.")


@app.get("/health")
def health():
    return {"status": "ok", "episodes_loaded": len(_episodes), "series_loaded": len(_series)}


@app.get("/episodes")
def get_episodes(
    limit: int = Query(None, description="Max number to return; omit for all"),
    offset: int = Query(0, ge=0),
    since: str = Query(None, description="ISO date; only episodes published_at >= since"),
    until: str = Query(None, description="ISO date; only episodes published_at <= until"),
    episode_ids: str = Query(None, description="Comma-separated episode ids to filter"),
):
    """
    List episodes with optional pagination and filters.
    Mimics a Firestore-style query API.
    """
    out = list(_episodes)

    if episode_ids:
        id_set = {x.strip() for x in episode_ids.split(",") if x.strip()}
        out = [e for e in out if e.get("id") in id_set or e.get("content_id") in id_set]

    if since:
        out = [e for e in out if (e.get("published_at") or "") >= since]
    if until:
        out = [e for e in out if (e.get("published_at") or "") <= until]

    if offset:
        out = out[offset:]
    if limit is not None:
        out = out[:limit]

    return {"episodes": out, "total": len(out)}


@app.get("/episodes/{episode_id}")
def get_episode(episode_id: str):
    """Get one episode by id or content_id."""
    ep = _episode_map.get(episode_id) or _episode_by_content_id.get(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    return ep


@app.get("/series")
def get_series():
    """List all series (for UI/discovery)."""
    return {"series": _series}


@app.get("/episode-by-content-id-map")
def get_episode_by_content_id_map():
    """
    Return content_id -> episode map for engagement resolution.
    Optional endpoint so HttpEpisodeProvider can avoid fetching all episodes.
    """
    return _episode_by_content_id


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8001")))
