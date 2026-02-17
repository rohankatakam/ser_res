#!/usr/bin/env python3
"""
Quality Gate Tests

Tests that the recommendation pipeline correctly filters episodes based on
quality gates (credibility floor and combined score floor).

Dataset Used:
-------------
- episodes.json: 561 podcast episodes with credibility and insight scores

Quality Gates (V1.1):
---------------------
- Gate 1: Credibility ≥ 2 (rejects low-credibility sources)
- Gate 2: Credibility + Insight ≥ 5 (ensures minimum quality threshold)

NOTE: Episodes also need to:
- Be within freshness window (90 days)
- Be in top CANDIDATE_POOL_SIZE (150) by quality score

This means C+I=5 episodes may not appear in recommendations if there are
enough higher-quality (C+I >= 6) episodes available. This is expected.

Ground Truth Episodes:
----------------------
Should be FILTERED (C < 2):
- FrouruKTAyVTraWbvKID: C=1, I=3 (The Contrarian Bet on a Digital Agency)
- awOikzMkofxxhvXW1yc7: C=1, I=1 (Sandisk Stock Surges on AI Boom)

Should be FILTERED (C≥2 but C+I < 5):
- WtabxXmJJFkq6F9S9XSp: C=2, I=2 (Story Of The Most Important Founder)
- 8ilc26bfKx3ANb0QK2eH: C=2, I=2 (Vibe Check: Claude Cowork)

Run:
----
    pytest tests/test_quality_gates.py -v
    python tests/test_quality_gates.py
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Set

import pytest
import requests

# Configuration
API_BASE = "http://localhost:8000"
DATA_DIR = Path(__file__).parent.parent / "data"

# Quality gate thresholds (must match server.py)
CREDIBILITY_FLOOR = 2
COMBINED_FLOOR = 5

# Ground truth episode IDs
SHOULD_FILTER_LOW_CRED = [
    "FrouruKTAyVTraWbvKID",  # C=1, I=3 - The Contrarian Bet on a Digital Agency
    "awOikzMkofxxhvXW1yc7",  # C=1, I=1 - Sandisk Stock Surges on AI Boom
]

SHOULD_FILTER_LOW_SUM = [
    "WtabxXmJJFkq6F9S9XSp",  # C=2, I=2 - Story Of The Most Important Founder
    "8ilc26bfKx3ANb0QK2eH",  # C=2, I=2 - Vibe Check: Claude Cowork
]


class TestQualityGates:
    """Test suite for quality gate filtering."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Load test data and verify API is running."""
        with open(DATA_DIR / "episodes.json") as f:
            self.episodes = json.load(f)
        self.episode_map = {ep["id"]: ep for ep in self.episodes}
        
        try:
            response = requests.get(f"{API_BASE}/")
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            pytest.skip("API server not running")
    
    def _get_all_recommendation_ids(self) -> Set[str]:
        """Get all episode IDs that can appear in recommendations."""
        # Create session and load all from queue
        response = requests.post(
            f"{API_BASE}/api/sessions/create",
            json={"engagements": [], "excluded_ids": []}
        )
        result = response.json()
        
        all_ids = {ep["id"] for ep in result["episodes"]}
        session_id = result["session_id"]
        
        # Load more until queue is exhausted
        while result["remaining_count"] > 0:
            response = requests.post(
                f"{API_BASE}/api/sessions/{session_id}/next",
                json={"limit": 50}
            )
            result = response.json()
            all_ids.update(ep["id"] for ep in result["episodes"])
        
        return all_ids
    
    def test_ground_truth_episode_scores(self):
        """Verify ground truth episodes have expected scores."""
        print("\n--- Ground Truth Episode Validation ---")
        
        # Check low credibility episodes
        print("\nShould FILTER (C < 2):")
        for ep_id in SHOULD_FILTER_LOW_CRED:
            assert ep_id in self.episode_map, f"Episode {ep_id} not found"
            ep = self.episode_map[ep_id]
            scores = ep.get("scores", {})
            c = scores.get("credibility", 0)
            i = scores.get("insight", 0)
            print(f"  {ep_id}: C={c}, I={i}, C+I={c+i} | {ep['title'][:40]}...")
            assert c < CREDIBILITY_FLOOR, f"Episode {ep_id} should have C < {CREDIBILITY_FLOOR}"
        
        # Check low sum episodes
        print("\nShould FILTER (C≥2, C+I < 5):")
        for ep_id in SHOULD_FILTER_LOW_SUM:
            assert ep_id in self.episode_map, f"Episode {ep_id} not found"
            ep = self.episode_map[ep_id]
            scores = ep.get("scores", {})
            c = scores.get("credibility", 0)
            i = scores.get("insight", 0)
            print(f"  {ep_id}: C={c}, I={i}, C+I={c+i} | {ep['title'][:40]}...")
            assert c >= CREDIBILITY_FLOOR, f"Episode {ep_id} should have C ≥ {CREDIBILITY_FLOOR}"
            assert (c + i) < COMBINED_FLOOR, f"Episode {ep_id} should have C+I < {COMBINED_FLOOR}"
    
    def test_low_credibility_filtered(self):
        """Episodes with credibility < 2 should never appear in recommendations."""
        print("\n--- Low Credibility Filter Test ---")
        
        all_rec_ids = self._get_all_recommendation_ids()
        print(f"Total recommendable episodes: {len(all_rec_ids)}")
        
        for ep_id in SHOULD_FILTER_LOW_CRED:
            ep = self.episode_map[ep_id]
            is_recommended = ep_id in all_rec_ids
            status = "✗ FOUND (BAD)" if is_recommended else "✓ FILTERED"
            print(f"  {ep_id}: {status} | {ep['title'][:40]}...")
            assert not is_recommended, f"Episode {ep_id} with C<2 should be filtered"
        
        print("\n✓ All low-credibility episodes correctly filtered")
    
    def test_low_combined_score_filtered(self):
        """Episodes with C+I < 5 should never appear in recommendations."""
        print("\n--- Low Combined Score Filter Test ---")
        
        all_rec_ids = self._get_all_recommendation_ids()
        
        for ep_id in SHOULD_FILTER_LOW_SUM:
            ep = self.episode_map[ep_id]
            is_recommended = ep_id in all_rec_ids
            status = "✗ FOUND (BAD)" if is_recommended else "✓ FILTERED"
            print(f"  {ep_id}: {status} | {ep['title'][:40]}...")
            assert not is_recommended, f"Episode {ep_id} with C+I<5 should be filtered"
        
        print("\n✓ All low-combined-score episodes correctly filtered")
    
    def test_all_recommendations_pass_gates(self):
        """Every recommended episode should pass quality gates."""
        print("\n--- All Recommendations Quality Check ---")
        
        response = requests.post(
            f"{API_BASE}/api/sessions/create",
            json={"engagements": [], "excluded_ids": []}
        )
        result = response.json()
        
        violations = []
        for ep in result["episodes"]:
            ep_id = ep["id"]
            full_ep = self.episode_map.get(ep_id, {})
            scores = full_ep.get("scores", {})
            c = scores.get("credibility", 0)
            i = scores.get("insight", 0)
            
            if c < CREDIBILITY_FLOOR:
                violations.append(f"{ep_id}: C={c} < {CREDIBILITY_FLOOR}")
            elif (c + i) < COMBINED_FLOOR:
                violations.append(f"{ep_id}: C+I={c+i} < {COMBINED_FLOOR}")
        
        print(f"Checked {len(result['episodes'])} recommendations")
        
        if violations:
            print("Violations found:")
            for v in violations:
                print(f"  ✗ {v}")
        else:
            print("✓ All recommendations pass quality gates")
        
        assert len(violations) == 0, f"Found {len(violations)} quality gate violations"
    
    def test_pool_quality_distribution(self):
        """Verify the quality distribution of the recommendation pool."""
        print("\n--- Pool Quality Distribution ---")
        
        all_rec_ids = self._get_all_recommendation_ids()
        
        # Count by quality score
        quality_dist = {5: 0, 6: 0, 7: 0}
        for ep_id in all_rec_ids:
            ep = self.episode_map.get(ep_id, {})
            scores = ep.get("scores", {})
            c = scores.get("credibility", 0)
            i = scores.get("insight", 0)
            total = c + i
            if total in quality_dist:
                quality_dist[total] += 1
            elif total > 7:
                quality_dist[7] = quality_dist.get(7, 0) + 1
        
        print(f"Pool size: {len(all_rec_ids)}")
        print(f"Quality distribution:")
        for score in sorted(quality_dist.keys()):
            label = f"C+I={score}" if score < 7 else "C+I≥7"
            print(f"  {label}: {quality_dist[score]} episodes")
        
        # Verify minimum quality
        min_score = min(
            self.episode_map.get(ep_id, {}).get("scores", {}).get("credibility", 0) +
            self.episode_map.get(ep_id, {}).get("scores", {}).get("insight", 0)
            for ep_id in all_rec_ids
        )
        print(f"\nMinimum quality in pool: C+I={min_score}")
        assert min_score >= COMBINED_FLOOR, f"Found episode with C+I={min_score} < {COMBINED_FLOOR}"


def run_tests_standalone():
    """Run tests without pytest for quick verification."""
    print("=" * 60)
    print("Quality Gate Tests")
    print("=" * 60)
    print(f"\nQuality Gates:")
    print(f"  - Credibility Floor: ≥ {CREDIBILITY_FLOOR}")
    print(f"  - Combined Floor (C+I): ≥ {COMBINED_FLOOR}")
    
    # Load data
    try:
        with open(DATA_DIR / "episodes.json") as f:
            episodes = json.load(f)
        episode_map = {ep["id"]: ep for ep in episodes}
        print(f"\n✓ Loaded {len(episodes)} episodes")
    except Exception as e:
        print(f"\n✗ Failed to load episodes: {e}")
        return False
    
    # Check API
    try:
        response = requests.get(f"{API_BASE}/")
        response.raise_for_status()
        print(f"✓ API is running")
    except Exception as e:
        print(f"✗ API not running: {e}")
        return False
    
    # Get all recommendable episode IDs
    print("\nFetching all recommendable episodes...")
    response = requests.post(
        f"{API_BASE}/api/sessions/create",
        json={"engagements": [], "excluded_ids": []}
    )
    result = response.json()
    all_rec_ids = {ep["id"] for ep in result["episodes"]}
    session_id = result["session_id"]
    
    while result["remaining_count"] > 0:
        response = requests.post(
            f"{API_BASE}/api/sessions/{session_id}/next",
            json={"limit": 50}
        )
        result = response.json()
        all_rec_ids.update(ep["id"] for ep in result["episodes"])
    
    print(f"✓ {len(all_rec_ids)} episodes in recommendation pool")
    
    all_passed = True
    
    # Test 1: Low credibility filtered
    print("\n" + "=" * 40)
    print("TEST 1: Low Credibility Filter (C < 2)")
    print("=" * 40)
    
    for ep_id in SHOULD_FILTER_LOW_CRED:
        ep = episode_map[ep_id]
        scores = ep.get("scores", {})
        is_filtered = ep_id not in all_rec_ids
        status = "✓ FILTERED" if is_filtered else "✗ NOT FILTERED"
        print(f"  {status}: C={scores.get('credibility')}, I={scores.get('insight')} | {ep['title'][:35]}...")
        if not is_filtered:
            all_passed = False
    
    # Test 2: Low combined filtered
    print("\n" + "=" * 40)
    print("TEST 2: Low Combined Filter (C+I < 5)")
    print("=" * 40)
    
    for ep_id in SHOULD_FILTER_LOW_SUM:
        ep = episode_map[ep_id]
        scores = ep.get("scores", {})
        is_filtered = ep_id not in all_rec_ids
        status = "✓ FILTERED" if is_filtered else "✗ NOT FILTERED"
        print(f"  {status}: C={scores.get('credibility')}, I={scores.get('insight')} | {ep['title'][:35]}...")
        if not is_filtered:
            all_passed = False
    
    # Test 3: All recommendations pass gates
    print("\n" + "=" * 40)
    print("TEST 3: All Recommendations Pass Gates")
    print("=" * 40)
    
    violations = 0
    for ep_id in all_rec_ids:
        ep = episode_map.get(ep_id, {})
        scores = ep.get("scores", {})
        c = scores.get("credibility", 0)
        i = scores.get("insight", 0)
        if c < CREDIBILITY_FLOOR or (c + i) < COMBINED_FLOOR:
            print(f"  ✗ Violation: {ep_id} C={c} I={i}")
            violations += 1
    
    if violations == 0:
        print(f"  ✓ All {len(all_rec_ids)} episodes pass quality gates")
    else:
        print(f"  ✗ Found {violations} violations")
        all_passed = False
    
    # Test 4: Quality distribution
    print("\n" + "=" * 40)
    print("TEST 4: Pool Quality Distribution")
    print("=" * 40)
    
    quality_dist = {}
    for ep_id in all_rec_ids:
        ep = episode_map.get(ep_id, {})
        scores = ep.get("scores", {})
        total = scores.get("credibility", 0) + scores.get("insight", 0)
        quality_dist[total] = quality_dist.get(total, 0) + 1
    
    for score in sorted(quality_dist.keys(), reverse=True):
        print(f"  C+I={score}: {quality_dist[score]} episodes")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED ✓")
    else:
        print("SOME TESTS FAILED ✗")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = run_tests_standalone()
    sys.exit(0 if success else 1)
