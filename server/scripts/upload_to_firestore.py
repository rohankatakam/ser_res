#!/usr/bin/env python3
"""
Upload episodes and series from a dataset directory to Cloud Firestore.

Creates collections:
  - episodes  (document ID = episode id)
  - series    (document ID = series id)
  - users     (empty; for future user/engagement persistence)

Requires:
  - GOOGLE_APPLICATION_CREDENTIALS env var pointing to a Firebase service account JSON key.
    Download from Firebase Console > Project Settings > Service Accounts > Generate new key.

Usage:
  From repo root (with credentials file path):
    python -m server.scripts.upload_to_firestore --credentials path/to/serviceAccountKey.json
  Or set env and run:
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/serviceAccountKey.json
    python -m server.scripts.upload_to_firestore
  Custom dataset path:
    python -m server.scripts.upload_to_firestore --credentials path/to/serviceAccountKey.json --dataset-path evaluation/fixtures/eval_909_feb2026
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add server parent so we can run as python -m server.scripts.upload_to_firestore
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    print("Install firebase-admin: pip install firebase-admin")
    sys.exit(1)

BATCH_SIZE = 500  # Firestore batch write limit


def _load_json(path: Path) -> list:
    with open(path) as f:
        return json.load(f)


def _sanitize_for_firestore(obj):
    """Recursively convert values for Firestore (no None in nested dicts if needed)."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_firestore(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_sanitize_for_firestore(x) for x in obj]
    return obj


def upload_episodes(db, episodes: list) -> int:
    coll = db.collection("episodes")
    total = 0
    for i in range(0, len(episodes), BATCH_SIZE):
        batch = db.batch()
        chunk = episodes[i : i + BATCH_SIZE]
        for ep in chunk:
            doc_id = ep.get("id") or ep.get("content_id")
            if not doc_id:
                continue
            ref = coll.document(doc_id)
            data = _sanitize_for_firestore(ep)
            batch.set(ref, data)
            total += 1
        batch.commit()
        print(f"  episodes: committed batch {i // BATCH_SIZE + 1} ({len(chunk)} docs)")
    return total


def upload_series(db, series: list) -> int:
    coll = db.collection("series")
    total = 0
    for i in range(0, len(series), BATCH_SIZE):
        batch = db.batch()
        chunk = series[i : i + BATCH_SIZE]
        for s in chunk:
            doc_id = s.get("id")
            if not doc_id:
                continue
            ref = coll.document(doc_id)
            data = _sanitize_for_firestore(s)
            batch.set(ref, data)
            total += 1
        batch.commit()
        print(f"  series: committed batch {i // BATCH_SIZE + 1} ({len(chunk)} docs)")
    return total


def ensure_users_collection(db) -> None:
    """Ensure users collection exists (one placeholder doc so the collection shows up)."""
    coll = db.collection("users")
    # Optional: add a placeholder so the collection is visible in the console.
    # For a real app you'd add users when they sign up. Leave empty or add one.
    ref = coll.document("_placeholder")
    ref.set({"created": True, "purpose": "Reserve users collection"})
    print("  users: collection initialized (placeholder doc)")


def main():
    parser = argparse.ArgumentParser(description="Upload episodes and series to Firestore")
    parser.add_argument(
        "--dataset-path",
        type=str,
        default=os.environ.get("DATASET_PATH", str(_REPO_ROOT / "evaluation" / "fixtures" / "eval_909_feb2026")),
        help="Path to dataset directory containing episodes.json and series.json",
    )
    parser.add_argument(
        "--skip-users",
        action="store_true",
        help="Do not create/update users collection",
    )
    parser.add_argument(
        "--credentials",
        type=str,
        default=None,
        metavar="PATH",
        help="Path to Firebase service account JSON key (e.g. secrets/firebase-credentials.json). Else uses GOOGLE_APPLICATION_CREDENTIALS.",
    )
    args = parser.parse_args()
    dataset_path = Path(args.dataset_path)

    if not dataset_path.is_dir():
        print(f"Dataset path not found: {dataset_path}")
        sys.exit(1)

    episodes_path = dataset_path / "episodes.json"
    series_path = dataset_path / "series.json"
    if not episodes_path.exists():
        print(f"Missing {episodes_path}")
        sys.exit(1)
    if not series_path.exists():
        print(f"Missing {series_path}")
        sys.exit(1)

    cred_path = args.credentials or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path:
        print("Provide --credentials PATH or set GOOGLE_APPLICATION_CREDENTIALS.")
        print("Download key from Firebase Console > Project Settings > Service Accounts > Generate new key.")
        sys.exit(1)
    cred_path = Path(cred_path)
    if not cred_path.is_absolute():
        cred_path = (_REPO_ROOT / cred_path).resolve()
    if not cred_path.exists():
        print(f"Credentials file not found: {cred_path}")
        sys.exit(1)

    print("Loading data...")
    episodes = _load_json(episodes_path)
    series = _load_json(series_path)
    print(f"  {len(episodes)} episodes, {len(series)} series")

    print("Initializing Firebase Admin...")
    if not firebase_admin._apps:
        cred = credentials.Certificate(str(cred_path))
        firebase_admin.initialize_app(cred)
    db = firestore.client()

    print("Uploading to Firestore...")
    n_ep = upload_episodes(db, episodes)
    n_ser = upload_series(db, series)
    if not args.skip_users:
        ensure_users_collection(db)
    print(f"Done. episodes={n_ep}, series={n_ser}")


if __name__ == "__main__":
    main()
