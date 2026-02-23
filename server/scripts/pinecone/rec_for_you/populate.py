#!/usr/bin/env python3
"""
Populate rec_for_you Pinecone index with episode embeddings.

Entry point for merge alignment: api_svc/scripts/pinecone/rec_for_you/populate
Uses PINECONE_REC_FOR_YOU_INDEX (default: rec-for-you), separate from RAG indexes.

Usage:
  python -m server.scripts.pinecone.rec_for_you.populate --source firestore
  python -m server.scripts.pinecone.rec_for_you.populate --source dataset --dataset eval_909_feb2026
"""

import sys
from pathlib import Path

# Ensure repo root on path
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from server.scripts.populate_pinecone import main

if __name__ == "__main__":
    sys.exit(main())
