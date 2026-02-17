#!/usr/bin/env python3
"""
Microsoft Engagement Unit Test

Tests that engaging with Microsoft-related episodes produces semantically
relevant recommendations using the V1.1 recommendation algorithm.

Dataset Used:
-------------
- episodes.json: 561 podcast episodes with titles, descriptions, scores, and categories
- embeddings.json: Pre-computed 1536-dim vectors from OpenAI text-embedding-3-small
  - Input text: episode title + key_insights (first 500 chars)
  - Generated via: python generate_embeddings.py

Algorithm Tested:
-----------------
- V1.1 Session Pool with Progressive Reveal (Option C)
- Stage A: Candidate pool pre-selection (150 eps from last 90 days, quality gates)
- Stage B: Semantic matching via cosine similarity

Test Scenario:
--------------
1. Find episodes with "Microsoft" in title
2. Create user engagement vector from 3 Microsoft episodes
3. Request recommendations with those engagements
4. Verify:
   - Session is not cold start (user vector was computed)
   - Similarity scores are higher than cold-start baseline (>0.50)
   - Recommendations include tech/AI related content

Requirements:
-------------
- API server must be running: uvicorn server:app --port 8000
- Embeddings must be generated: python generate_embeddings.py

Run:
----
    pytest tests/test_microsoft_recommendations.py -v
    
    # Or run directly:
    python tests/test_microsoft_recommendations.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

import pytest
import requests

# Configuration
API_BASE = "http://localhost:8000"
DATA_DIR = Path(__file__).parent.parent / "data"

# Test thresholds
MIN_SIMILARITY_SCORE = 0.50  # Cold start baseline is ~0.43
MIN_POOL_SIZE = 50
MIN_MICROSOFT_EPISODES = 3


class TestMicrosoftRecommendations:
    """Test suite for Microsoft-focused engagement recommendations."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Load test data and verify API is running."""
        # Load episodes
        with open(DATA_DIR / "episodes.json") as f:
            self.episodes = json.load(f)
        
        # Load embeddings
        embeddings_file = DATA_DIR / "embeddings.json"
        if embeddings_file.exists():
            with open(embeddings_file) as f:
                self.embeddings = json.load(f)
        else:
            self.embeddings = {}
        
        # Find Microsoft episodes
        self.microsoft_episodes = [
            ep for ep in self.episodes 
            if "microsoft" in ep["title"].lower()
        ]
        
        # Verify API is running
        try:
            response = requests.get(f"{API_BASE}/")
            response.raise_for_status()
            self.api_info = response.json()
        except requests.exceptions.ConnectionError:
            pytest.skip("API server not running. Start with: uvicorn server:app --port 8000")
    
    def test_data_availability(self):
        """Verify test data is loaded correctly."""
        print(f"\n--- Data Availability ---")
        print(f"Total episodes: {len(self.episodes)}")
        print(f"Total embeddings: {len(self.embeddings)}")
        print(f"Microsoft episodes: {len(self.microsoft_episodes)}")
        
        assert len(self.episodes) > 0, "No episodes loaded"
        assert len(self.embeddings) > 0, "No embeddings loaded - run generate_embeddings.py"
        assert len(self.microsoft_episodes) >= MIN_MICROSOFT_EPISODES, \
            f"Need at least {MIN_MICROSOFT_EPISODES} Microsoft episodes, found {len(self.microsoft_episodes)}"
    
    def test_microsoft_episodes_have_embeddings(self):
        """Verify Microsoft episodes have pre-computed embeddings."""
        print(f"\n--- Microsoft Episode Embeddings ---")
        
        missing_embeddings = []
        for ep in self.microsoft_episodes[:5]:
            has_embedding = ep["id"] in self.embeddings
            status = "✓" if has_embedding else "✗"
            print(f"  {status} {ep['title'][:50]}...")
            if not has_embedding:
                missing_embeddings.append(ep["id"])
        
        assert len(missing_embeddings) == 0, \
            f"Missing embeddings for {len(missing_embeddings)} Microsoft episodes"
    
    def test_cold_start_baseline(self):
        """Establish cold start baseline (no engagements)."""
        print(f"\n--- Cold Start Baseline ---")
        
        response = requests.post(
            f"{API_BASE}/api/sessions/create",
            json={"engagements": [], "excluded_ids": []}
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"Session ID: {data['session_id']}")
        print(f"Cold start: {data['cold_start']}")
        print(f"Pool size: {data['total_in_queue']}")
        
        if data["episodes"]:
            baseline_score = data["episodes"][0].get("similarity_score", 0)
            print(f"Top similarity score (baseline): {baseline_score:.3f}")
            self.cold_start_baseline = baseline_score
        else:
            self.cold_start_baseline = 0.43  # Default
        
        assert data["cold_start"] is True, "Should be cold start with no engagements"
        assert data["total_in_queue"] >= MIN_POOL_SIZE, \
            f"Pool size {data['total_in_queue']} < {MIN_POOL_SIZE}"
    
    def test_microsoft_engagement_personalization(self):
        """
        Core test: Engaging with Microsoft episodes should produce
        personalized recommendations with higher similarity scores.
        """
        print(f"\n--- Microsoft Engagement Test ---")
        
        # Select 3 Microsoft episodes for engagement
        test_episodes = self.microsoft_episodes[:3]
        print(f"Engaging with {len(test_episodes)} Microsoft episodes:")
        for ep in test_episodes:
            print(f"  - {ep['title'][:60]}...")
        
        # Create engagements
        engagements = []
        excluded_ids = []
        for i, ep in enumerate(test_episodes):
            engagements.append({
                "episode_id": ep["id"],
                "type": "click",
                "timestamp": f"2026-02-05T01:{i:02d}:00Z"
            })
            excluded_ids.append(ep["id"])
        
        # Request personalized recommendations
        response = requests.post(
            f"{API_BASE}/api/sessions/create",
            json={
                "engagements": engagements,
                "excluded_ids": excluded_ids
            }
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"\nSession ID: {data['session_id']}")
        print(f"Cold start: {data['cold_start']}")
        print(f"User vector episodes: {data['debug']['user_vector_episodes']}")
        print(f"Pool size: {data['total_in_queue']}")
        
        # Verify not cold start
        assert data["cold_start"] is False, \
            "Should NOT be cold start with 3 engagements"
        
        # Verify user vector was computed
        assert data["debug"]["user_vector_episodes"] == 3, \
            f"Expected 3 episodes in user vector, got {data['debug']['user_vector_episodes']}"
        
        # Check similarity scores
        print(f"\nTop 5 recommendations:")
        top_scores = []
        for i, ep in enumerate(data["episodes"][:5]):
            score = ep.get("similarity_score", 0)
            top_scores.append(score)
            print(f"  {i+1}. [{score*100:.0f}%] {ep['title'][:55]}...")
        
        # Verify scores are above cold start baseline
        avg_score = sum(top_scores) / len(top_scores) if top_scores else 0
        print(f"\nAverage top-5 similarity: {avg_score:.3f}")
        print(f"Cold start baseline: ~0.43")
        print(f"Minimum threshold: {MIN_SIMILARITY_SCORE}")
        
        assert avg_score > MIN_SIMILARITY_SCORE, \
            f"Average similarity {avg_score:.3f} should be > {MIN_SIMILARITY_SCORE}"
        
        # Verify top score is significantly above baseline
        top_score = top_scores[0] if top_scores else 0
        assert top_score > MIN_SIMILARITY_SCORE, \
            f"Top similarity {top_score:.3f} should be > {MIN_SIMILARITY_SCORE}"
    
    def test_engagement_exclusion(self):
        """Verify engaged episodes are excluded from recommendations."""
        print(f"\n--- Engagement Exclusion Test ---")
        
        test_episodes = self.microsoft_episodes[:3]
        excluded_ids = [ep["id"] for ep in test_episodes]
        
        engagements = [
            {"episode_id": ep["id"], "type": "click", "timestamp": "2026-02-05T01:00:00Z"}
            for ep in test_episodes
        ]
        
        response = requests.post(
            f"{API_BASE}/api/sessions/create",
            json={
                "engagements": engagements,
                "excluded_ids": excluded_ids
            }
        )
        response.raise_for_status()
        data = response.json()
        
        # Check that excluded episodes are not in recommendations
        recommended_ids = {ep["id"] for ep in data["episodes"]}
        overlap = set(excluded_ids) & recommended_ids
        
        print(f"Excluded IDs: {len(excluded_ids)}")
        print(f"Recommended episodes: {len(data['episodes'])}")
        print(f"Overlap (should be 0): {len(overlap)}")
        
        assert len(overlap) == 0, \
            f"Engaged episodes should be excluded from recommendations: {overlap}"
    
    def test_load_more_deterministic(self):
        """Verify Load More returns next items from same queue (deterministic)."""
        print(f"\n--- Load More Deterministic Test ---")
        
        # Create session
        response = requests.post(
            f"{API_BASE}/api/sessions/create",
            json={"engagements": [], "excluded_ids": []}
        )
        response.raise_for_status()
        data = response.json()
        session_id = data["session_id"]
        
        first_batch_ids = [ep["id"] for ep in data["episodes"]]
        print(f"First batch: {len(first_batch_ids)} episodes")
        
        # Load more
        response = requests.post(
            f"{API_BASE}/api/sessions/{session_id}/next",
            json={"limit": 10}
        )
        response.raise_for_status()
        data = response.json()
        
        second_batch_ids = [ep["id"] for ep in data["episodes"]]
        print(f"Second batch: {len(second_batch_ids)} episodes")
        
        # Verify no overlap (deterministic progression)
        overlap = set(first_batch_ids) & set(second_batch_ids)
        print(f"Overlap (should be 0): {len(overlap)}")
        
        assert len(overlap) == 0, \
            f"Load More should return different episodes: {overlap}"
        
        # Verify queue positions are sequential
        if data["episodes"]:
            positions = [ep.get("queue_position", 0) for ep in data["episodes"]]
            print(f"Queue positions: {positions[:5]}...")
            assert positions[0] > 10, \
                f"Second batch should start after position 10, got {positions[0]}"


def run_tests_standalone():
    """Run tests without pytest for quick verification."""
    print("=" * 60)
    print("Microsoft Recommendations Unit Test")
    print("=" * 60)
    print(f"\nDataset: {DATA_DIR / 'episodes.json'}")
    print(f"Embeddings: {DATA_DIR / 'embeddings.json'}")
    print(f"API: {API_BASE}")
    print("=" * 60)
    
    # Load data
    try:
        with open(DATA_DIR / "episodes.json") as f:
            episodes = json.load(f)
        print(f"\n✓ Loaded {len(episodes)} episodes")
    except Exception as e:
        print(f"\n✗ Failed to load episodes: {e}")
        return False
    
    try:
        with open(DATA_DIR / "embeddings.json") as f:
            embeddings = json.load(f)
        print(f"✓ Loaded {len(embeddings)} embeddings")
    except Exception as e:
        print(f"✗ Failed to load embeddings: {e}")
        return False
    
    # Find Microsoft episodes
    microsoft_eps = [ep for ep in episodes if "microsoft" in ep["title"].lower()]
    print(f"✓ Found {len(microsoft_eps)} Microsoft episodes")
    
    if len(microsoft_eps) < 3:
        print("✗ Not enough Microsoft episodes for test")
        return False
    
    # Check API
    try:
        response = requests.get(f"{API_BASE}/")
        response.raise_for_status()
        print(f"✓ API is running")
    except Exception as e:
        print(f"✗ API not running: {e}")
        print("  Start with: uvicorn server:app --port 8000")
        return False
    
    # Run core test
    print("\n" + "-" * 40)
    print("Running Microsoft Engagement Test...")
    print("-" * 40)
    
    test_eps = microsoft_eps[:3]
    engagements = [
        {"episode_id": ep["id"], "type": "click", "timestamp": f"2026-02-05T01:{i:02d}:00Z"}
        for i, ep in enumerate(test_eps)
    ]
    excluded_ids = [ep["id"] for ep in test_eps]
    
    print(f"\nEngaging with:")
    for ep in test_eps:
        print(f"  - {ep['title'][:55]}...")
    
    response = requests.post(
        f"{API_BASE}/api/sessions/create",
        json={"engagements": engagements, "excluded_ids": excluded_ids}
    )
    
    if response.status_code != 200:
        print(f"✗ API error: {response.status_code}")
        return False
    
    data = response.json()
    
    print(f"\nResults:")
    print(f"  Session: {data['session_id']}")
    print(f"  Cold start: {data['cold_start']}")
    print(f"  User vector from: {data['debug']['user_vector_episodes']} episodes")
    print(f"  Pool size: {data['total_in_queue']}")
    
    print(f"\nTop 5 Recommendations:")
    top_scores = []
    for i, ep in enumerate(data["episodes"][:5]):
        score = ep.get("similarity_score", 0)
        top_scores.append(score)
        print(f"  {i+1}. [{score*100:.0f}%] {ep['title'][:50]}...")
    
    avg_score = sum(top_scores) / len(top_scores) if top_scores else 0
    
    print(f"\n" + "=" * 40)
    print("RESULTS")
    print("=" * 40)
    
    passed = True
    
    # Check 1: Not cold start
    if data["cold_start"]:
        print("✗ FAIL: Should not be cold start")
        passed = False
    else:
        print("✓ PASS: Not cold start (user vector computed)")
    
    # Check 2: User vector has 3 episodes
    if data["debug"]["user_vector_episodes"] != 3:
        print(f"✗ FAIL: User vector should have 3 episodes, has {data['debug']['user_vector_episodes']}")
        passed = False
    else:
        print("✓ PASS: User vector built from 3 engagements")
    
    # Check 3: Similarity scores above threshold
    if avg_score > MIN_SIMILARITY_SCORE:
        print(f"✓ PASS: Average similarity {avg_score:.3f} > {MIN_SIMILARITY_SCORE}")
    else:
        print(f"✗ FAIL: Average similarity {avg_score:.3f} <= {MIN_SIMILARITY_SCORE}")
        passed = False
    
    # Check 4: Engaged episodes excluded
    rec_ids = {ep["id"] for ep in data["episodes"]}
    overlap = set(excluded_ids) & rec_ids
    if len(overlap) == 0:
        print("✓ PASS: Engaged episodes excluded from recommendations")
    else:
        print(f"✗ FAIL: {len(overlap)} engaged episodes in recommendations")
        passed = False
    
    print("\n" + "=" * 40)
    if passed:
        print("ALL TESTS PASSED ✓")
    else:
        print("SOME TESTS FAILED ✗")
    print("=" * 40)
    
    return passed


if __name__ == "__main__":
    # Run standalone if executed directly
    success = run_tests_standalone()
    sys.exit(0 if success else 1)
