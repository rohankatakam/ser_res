#!/usr/bin/env python3
"""
Evaluation Test Runner

Executes test cases against the recommendation API and validates results.
Uses multi-LLM judge infrastructure for qualitative evaluation.

Features (matching original infrastructure):
- 4 standard LLM criteria per test: relevance, diversity, quality, hypothesis_alignment
- Per-test LLM summary with observations and suggestions
- Criterion weights and confidence scores
- Aggregate scores per test and overall
- Multi-LLM consensus with uncertainty metrics

Usage:
    python runner.py                    # Run all tests (LLM evaluation is core)
    python runner.py --test 01          # Run specific test
    python runner.py --verbose          # Show detailed output
    python runner.py --save             # Save report to file
    python runner.py --deterministic-only  # Skip LLM evaluation (for quick checks)
    python runner.py --legacy           # Use legacy single-LLM evaluation (for comparison)

Note: LLM evaluation is enabled by default. At least one LLM API key required
(OPENAI_API_KEY or GEMINI_API_KEY).
"""

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Load project root .env so API keys and API_URL are available when running from CLI
try:
    from dotenv import load_dotenv
    _root_env = Path(__file__).resolve().parent.parent / ".env"
    if _root_env.exists():
        load_dotenv(_root_env)
except ImportError:
    pass

import requests

# Import judges package for multi-LLM evaluation
try:
    from judges import (
        evaluate_all_criteria,
        load_judge_config,
        get_available_providers,
        summarize_results as summarize_llm_results,
    )
    from judges.client import call_llm
    from criteria import get_criteria_for_test, list_criteria, get_criterion
    HAS_JUDGES = True
except ImportError as e:
    HAS_JUDGES = False
    _JUDGES_IMPORT_ERROR = str(e)

# Import legacy single-LLM evaluation (for comparison)
import warnings
try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from deprecated.llm_judge import evaluate_with_llm as legacy_evaluate_with_llm
    HAS_LEGACY = True
except ImportError:
    HAS_LEGACY = False

# ============================================================================
# Standard LLM Criteria and Weights
# ============================================================================

# The 4 standard LLM criteria evaluated for every LLM-enabled test
STANDARD_LLM_CRITERIA = ["relevance", "diversity", "quality", "hypothesis_alignment"]

# Default weights for each criterion type
CRITERION_WEIGHTS = {
    # Deterministic criteria
    "cold_start_flag": 1.0,
    "avg_credibility": 1.5,
    "min_credibility": 1.0,
    "top_quality_score": 1.5,
    "episode_difference": 1.5,
    "similarity_increase": 1.0,
    "cold_start_flag_off": 1.0,
    "credibility_floor": 2.0,
    "combined_floor": 2.0,
    "known_bad_excluded": 1.5,
    "exclusions_respected": 2.0,
    "still_returns_results": 1.0,
    "ai_tech_category_match": 1.5,
    "crypto_category_match": 1.5,
    "both_in_top_10": 1.0,
    "recency_score_ordering": 1.5,
    "ranking_reflects_recency": 1.5,
    "different_results": 1.0,
    "crypto_dominance_in_b": 1.5,
    "max_per_series": 1.5,
    "no_adjacent_same_series": 1.5,
    # LLM criteria
    "llm_relevance": 1.0,
    "llm_diversity": 1.0,
    "llm_quality": 1.0,
    "llm_hypothesis_alignment": 1.0,
    "llm_topic_breadth": 1.0,
}

# Default thresholds for LLM criteria
LLM_THRESHOLDS = {
    "relevance": 6.0,
    "diversity": 6.0,
    "quality": 6.0,
    "hypothesis_alignment": 6.0,
    "topic_breadth": 6.0,
}

# Configuration
API_BASE_URL = os.getenv("API_URL", "http://localhost:8000")
PROFILES_DIR = Path(__file__).parent / "profiles"
TEST_CASES_DIR = Path(__file__).parent / "test_cases"
REPORTS_DIR = Path(__file__).parent / "reports"


# ============================================================================
# Data Loading
# ============================================================================

def load_profile(profile_id: str) -> Dict:
    """Load a profile JSON file."""
    profile_path = PROFILES_DIR / f"{profile_id}.json"
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile not found: {profile_path}")
    with open(profile_path) as f:
        return json.load(f)


def load_test_case(test_id: str) -> Dict:
    """Load a test case JSON file."""
    test_path = TEST_CASES_DIR / f"{test_id}.json"
    if not test_path.exists():
        raise FileNotFoundError(f"Test case not found: {test_path}")
    with open(test_path) as f:
        return json.load(f)


def load_all_profiles() -> Dict[str, Dict]:
    """Load all profile JSON files."""
    profiles = {}
    for path in PROFILES_DIR.glob("*.json"):
        with open(path) as f:
            profile = json.load(f)
            profiles[profile["profile_id"]] = profile
    return profiles


def load_all_test_cases() -> Dict[str, Dict]:
    """Load all test case JSON files."""
    test_cases = {}
    for path in TEST_CASES_DIR.glob("*.json"):
        with open(path) as f:
            test_case = json.load(f)
            test_cases[test_case["test_id"]] = test_case
    return test_cases


# ============================================================================
# Engine Context and Direct Execution
# ============================================================================

class EngineContext:
    """Context for running tests with direct engine access (no API calls)."""
    
    def __init__(
        self,
        engine_module,
        episodes: List[Dict],
        embeddings: Dict[str, List[float]],
        episode_by_content_id: Dict[str, Dict],
        algo_config: Optional[Any] = None
    ):
        self.engine_module = engine_module
        self.episodes = episodes
        self.embeddings = embeddings
        self.episode_by_content_id = episode_by_content_id
        self.algo_config = algo_config


def call_engine_directly(
    engagements: List[Dict],
    excluded_ids: set,
    engine_context: EngineContext
) -> Dict:
    """
    Call the recommendation engine directly (no API).
    
    This is used when runner.py is imported by server.py.
    Returns the same format as the API would return.
    """
    # Auto-exclude engaged episodes
    all_excluded = excluded_ids.copy()
    for eng in engagements:
        all_excluded.add(eng.get("episode_id", ""))
    
    # Use pre-parsed config when available; convert dict to RecommendationConfig only when needed
    config = engine_context.algo_config
    if config is not None and isinstance(config, dict) and hasattr(engine_context.engine_module, "RecommendationConfig"):
        config = engine_context.engine_module.RecommendationConfig.from_dict(config)
    
    # Call engine
    queue, cold_start, user_vector_episodes = engine_context.engine_module.create_recommendation_queue(
        engagements=engagements,
        excluded_ids=all_excluded,
        episodes=engine_context.episodes,
        embeddings=engine_context.embeddings,
        episode_by_content_id=engine_context.episode_by_content_id,
        config=config,
    )
    
    # Convert to API response format (episode must be dict for item assignment)
    episodes = []
    for i, scored_ep in enumerate(queue[:10]):
        if hasattr(scored_ep.episode, "model_dump"):
            ep = scored_ep.episode.model_dump()
        elif hasattr(scored_ep.episode, "dict"):
            ep = scored_ep.episode.dict()
        else:
            ep = dict(scored_ep.episode) if isinstance(scored_ep.episode, dict) else {}
        ep["similarity_score"] = scored_ep.similarity_score
        ep["quality_score"] = scored_ep.quality_score
        ep["recency_score"] = scored_ep.recency_score
        ep["final_score"] = scored_ep.final_score
        ep["queue_position"] = i + 1
        episodes.append(ep)
    
    return {
        "episodes": episodes,
        "cold_start": cold_start,
        "user_vector_episodes": user_vector_episodes,
        "total_in_queue": len(queue)
    }


# ============================================================================
# API Client (for CLI standalone mode)
# ============================================================================

def call_api(engagements: List[Dict], excluded_ids: List[str]) -> Dict:
    """Call the recommendation API (for CLI mode only)."""
    url = f"{API_BASE_URL}/api/sessions/create"
    payload = {
        "engagements": engagements,
        "excluded_ids": excluded_ids
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        raise ConnectionError(f"Cannot connect to API at {API_BASE_URL}. Is the server running?")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API request failed: {e}")


def call_api_with_profile(profile: Dict) -> Dict:
    """Call the API using a profile's engagements (for CLI mode only)."""
    engagements = []
    for eng in profile.get("engagements", []):
        engagements.append({
            "episode_id": eng["episode_id"],
            "type": eng.get("type", "click"),
            "timestamp": eng.get("timestamp", datetime.now().isoformat())
        })
    
    excluded_ids = profile.get("excluded_ids", [])
    return call_api(engagements, excluded_ids)


# ============================================================================
# Test Result Class
# ============================================================================

class TestResult:
    """Result of a single test with weights, confidence, and aggregate scoring."""
    
    def __init__(self, test_id: str, name: str, evaluation_method: str = "deterministic_llm", test_type: str = "MFT"):
        self.test_id = test_id
        self.name = name
        self.test_type = test_type
        self.evaluation_method = evaluation_method
        self.passed = True
        self.criteria_results = []
        self.error = None
        self.api_response = None
        self.llm_results = []  # Multi-LLM results
        self.llm_evaluation = None  # Per-test LLM summary with observations/suggestions
        self._llm_judge_context = None  # Profile + recommendations context for debugging
    
    def set_llm_judge_context(self, profile: Optional[Dict], recommendations: List[Dict]):
        """Store profile and recommendations for debugging/analysis."""
        self._llm_judge_context = {
            "profile": profile,
            "recommendations": recommendations
        }
    
    def add_criterion(self, criterion_id: str, description: str, passed: bool, 
                      details: str = "", score: Optional[float] = None,
                      threshold: Optional[float] = None,
                      confidence: float = 1.0,
                      weight: Optional[float] = None,
                      consensus_level: Optional[str] = None,
                      flag_for_review: bool = False,
                      model_results: Optional[Dict] = None,
                      cross_model_std: Optional[float] = None):
        """Add a criterion result with weights and confidence."""
        # Compute score from pass/fail if not provided (10 for pass, 1 for fail)
        if score is None:
            score = 10.0 if passed else 1.0
        
        # Get weight from defaults if not provided
        if weight is None:
            weight = CRITERION_WEIGHTS.get(criterion_id, 1.0)
        
        # Get threshold from defaults
        if threshold is None:
            base_id = criterion_id.replace("llm_", "") if criterion_id.startswith("llm_") else criterion_id
            threshold = LLM_THRESHOLDS.get(base_id, 7.0)
        
        result = {
            "criterion_id": criterion_id,
            "description": description,
            "score": round(score, 2),
            "threshold": threshold,
            "confidence": confidence,
            "passed": passed,
            "details": details,
            "weight": weight
        }
        if consensus_level:
            result["consensus_level"] = consensus_level
        if flag_for_review:
            result["flag_for_review"] = True
        if model_results:
            result["model_results"] = model_results
            result["criterion_type"] = "llm"  # Mark as LLM criterion
        if cross_model_std is not None:
            result["cross_model_std"] = cross_model_std
        
        self.criteria_results.append(result)
        if not passed:
            self.passed = False
    
    def add_llm_results(self, llm_results: List[Dict[str, Any]]):
        """Add LLM evaluation results from the judges package."""
        self.llm_results = llm_results
        
        for r in llm_results:
            if r.get("error"):
                continue
            
            criterion_id = r.get("criterion_id", "unknown")
            criterion_type = r.get("criterion_type", "llm")
            score = r.get("final_score") or r.get("score", 0)
            threshold = r.get("threshold", 6.0)
            passed = r.get("passed", False)
            consensus = r.get("consensus_level", "")
            
            # Map score from 1-10 to confidence
            # High scores with strong consensus = high confidence
            confidence = 0.9 if consensus == "STRONG" else 0.8 if consensus == "GOOD" else 0.7
            
            # Build details string
            details = f"score={score:.1f}"
            if criterion_type == "llm":
                if consensus:
                    details += f", consensus={consensus}"
                std = r.get("cross_model_std")
                if std is not None:
                    details += f", std={std:.2f}"
            
            # Map criterion IDs to LLM descriptions
            criterion_descriptions = {
                "relevance": "LLM Judge: Recommendations match user interests and Content Hypothesis",
                "diversity": "LLM Judge: Appropriate variety for user's exploration/specialization profile",
                "quality": "LLM Judge: High-quality, credible sources surfaced",
                "hypothesis_alignment": "LLM Judge: Recommendations align with Content Hypothesis",
                "topic_breadth": "LLM Judge: Topic breadth covers major themes",
            }
            
            self.add_criterion(
                f"llm_{criterion_id}",
                criterion_descriptions.get(criterion_id, f"LLM Judge: {criterion_id}"),
                passed,
                details=details,
                score=score,
                threshold=threshold,
                confidence=confidence,
                consensus_level=consensus,
                flag_for_review=r.get("flag_for_review", False),
                model_results=r.get("model_results"),  # Per-provider breakdown
                cross_model_std=r.get("cross_model_std")  # Cross-model standard deviation
            )
    
    def set_llm_evaluation(self, evaluation: Dict[str, Any]):
        """Set the per-test LLM evaluation summary."""
        self.llm_evaluation = evaluation
    
    def compute_aggregate_scores(self) -> Dict[str, Any]:
        """Compute weighted aggregate scores for the test."""
        if not self.criteria_results:
            return {
                "aggregate_score": 0.0,
                "aggregate_confidence": 0.0,
                "criteria_count": 0,
                "passed_count": 0
            }
        
        total_weighted_score = 0.0
        total_weight = 0.0
        total_weighted_confidence = 0.0
        passed_count = 0
        
        for cr in self.criteria_results:
            weight = cr.get("weight", 1.0)
            score = cr.get("score", 0)
            confidence = cr.get("confidence", 1.0)
            
            total_weighted_score += score * weight
            total_weight += weight
            total_weighted_confidence += confidence * weight
            
            if cr.get("passed"):
                passed_count += 1
        
        aggregate_score = round(total_weighted_score / total_weight, 2) if total_weight > 0 else 0.0
        aggregate_confidence = round(total_weighted_confidence / total_weight, 2) if total_weight > 0 else 0.0
        
        return {
            "aggregate_score": aggregate_score,
            "aggregate_confidence": aggregate_confidence,
            "criteria_count": len(self.criteria_results),
            "passed_count": passed_count
        }
    
    def set_error(self, error: str):
        self.error = error
        self.passed = False
    
    def to_dict(self) -> Dict:
        scores = self.compute_aggregate_scores()
        
        result = {
            "test_id": self.test_id,
            "name": self.name,
            "type": self.test_type,
            "evaluation_method": self.evaluation_method,
            "passed": self.passed,
            "criteria_results": self.criteria_results,
            "error": self.error,
            "llm_evaluation": self.llm_evaluation,
            "scores": scores
        }
        if self.llm_results:
            result["llm_results"] = self.llm_results
        if self._llm_judge_context:
            result["_llm_judge_context"] = self._llm_judge_context
        return result


# ============================================================================
# Deterministic Validators (existing logic preserved)
# ============================================================================

def validate_cold_start_quality(response: Dict, test_case: Dict) -> TestResult:
    """Test 01: Cold Start Returns Quality Content"""
    result = TestResult("01_cold_start_quality", test_case["name"])
    result.api_response = response
    
    episodes = response.get("episodes", [])
    
    # Criterion 1: cold_start flag
    cold_start = response.get("cold_start", False)
    result.add_criterion(
        "cold_start_flag",
        "API response includes cold_start: true",
        cold_start == True,
        f"cold_start={cold_start}"
    )
    
    # Criterion 2: Average credibility >= 3.0
    if episodes:
        credibilities = [ep["scores"]["credibility"] for ep in episodes[:10]]
        avg_cred = sum(credibilities) / len(credibilities)
        result.add_criterion(
            "avg_credibility",
            "Average credibility of top 10 >= 3.0",
            avg_cred >= 3.0,
            f"avg_credibility={avg_cred:.2f}"
        )
    
    # Criterion 3: No episode with credibility < 2
    min_cred = min(ep["scores"]["credibility"] for ep in episodes[:10]) if episodes else 0
    result.add_criterion(
        "min_credibility",
        "No episode in top 10 has credibility < 2",
        min_cred >= 2,
        f"min_credibility={min_cred}"
    )
    
    # Criterion 4: Top 3 quality scores >= 0.7
    if episodes:
        top_3_quality = [ep.get("quality_score", 0) for ep in episodes[:3]]
        all_high_quality = all(q >= 0.7 for q in top_3_quality)
        result.add_criterion(
            "top_quality_score",
            "Top 3 episodes have quality_score >= 0.7",
            all_high_quality,
            f"top_3_quality_scores={top_3_quality}"
        )
    
    return result


def validate_personalization_differs(cold_response: Dict, vc_response: Dict, test_case: Dict) -> TestResult:
    """Test 02: Personalization Differs from Cold Start"""
    result = TestResult("02_personalization_differs", test_case["name"])
    
    cold_ids = set(ep["id"] for ep in cold_response.get("episodes", [])[:10])
    vc_ids = set(ep["id"] for ep in vc_response.get("episodes", [])[:10])
    
    # Criterion 1: At least 5 different episodes
    different_count = len(vc_ids - cold_ids)
    result.add_criterion(
        "episode_difference",
        "At least 5 of top 10 episodes are different",
        different_count >= 5,
        f"different_episodes={different_count}"
    )
    
    # Criterion 2: VC has higher similarity scores
    cold_sim = [ep.get("similarity_score", 0) or 0 for ep in cold_response.get("episodes", [])[:10]]
    vc_sim = [ep.get("similarity_score", 0) or 0 for ep in vc_response.get("episodes", [])[:10]]
    
    avg_cold_sim = sum(cold_sim) / len(cold_sim) if cold_sim else 0
    avg_vc_sim = sum(vc_sim) / len(vc_sim) if vc_sim else 0
    
    delta_sim = avg_vc_sim - avg_cold_sim
    result.add_criterion(
        "similarity_increase",
        "VC Partner has higher avg similarity_score than cold start",
        avg_vc_sim > avg_cold_sim,
        f"cold_avg={avg_cold_sim:.3f}, vc_avg={avg_vc_sim:.3f}, delta={delta_sim:.3f}"
    )
    
    # Criterion 3: VC cold_start flag is false
    vc_cold_start = vc_response.get("cold_start", True)
    result.add_criterion(
        "cold_start_flag_off",
        "VC Partner cold_start flag is false",
        vc_cold_start == False,
        f"vc_cold_start={vc_cold_start}"
    )
    
    return result


def validate_quality_gates(responses: Dict[str, Dict], test_case: Dict) -> TestResult:
    """Test 03: Quality Gates Enforce Credibility Floor"""
    result = TestResult("03_quality_gates_credibility", test_case["name"])
    
    all_episodes = []
    for profile_id, response in responses.items():
        episodes = response.get("episodes", [])
        for ep in episodes:
            ep["_profile"] = profile_id
        all_episodes.extend(episodes)
    
    # Criterion 1: No credibility < 2
    low_cred = [ep for ep in all_episodes if ep["scores"]["credibility"] < 2]
    result.add_criterion(
        "credibility_floor",
        "No episode with credibility < 2 in any response",
        len(low_cred) == 0,
        f"low_credibility_count={len(low_cred)}"
    )
    
    # Criterion 2: All C + I >= 5
    low_combined = [
        ep for ep in all_episodes 
        if ep["scores"]["credibility"] + ep["scores"]["insight"] < 5
    ]
    result.add_criterion(
        "combined_floor",
        "All episodes have C + I >= 5",
        len(low_combined) == 0,
        f"low_combined_count={len(low_combined)}"
    )
    
    # Criterion 3: Known bad episode never appears
    known_bad_id = "LexVsfaBFuk0MWokZOhY"
    bad_found = any(ep["id"] == known_bad_id for ep in all_episodes)
    result.add_criterion(
        "known_bad_excluded",
        f"Known low-credibility episode {known_bad_id} never appears",
        not bad_found,
        f"found={bad_found}"
    )
    
    return result


def validate_excluded_episodes(response: Dict, excluded_ids: List[str], test_case: Dict) -> TestResult:
    """Test 04: Excluded Episodes Never Reappear"""
    result = TestResult("04_excluded_episodes", test_case["name"])
    result.api_response = response
    
    episode_ids = [ep["id"] for ep in response.get("episodes", [])]
    
    # Criterion 1: No excluded IDs appear
    excluded_found = [eid for eid in excluded_ids if eid in episode_ids]
    result.add_criterion(
        "exclusions_respected",
        "None of the excluded episode IDs appear",
        len(excluded_found) == 0,
        f"excluded_found={excluded_found}"
    )
    
    # Criterion 2: Still returns 10 results
    episode_count = len(response.get("episodes", []))
    result.add_criterion(
        "still_returns_results",
        "System still returns 10 valid recommendations",
        episode_count == 10,
        f"episode_count={episode_count}"
    )
    
    return result


def validate_category_personalization(ai_response: Dict, crypto_response: Dict, test_case: Dict) -> TestResult:
    """Test 05: Category Engagement → Category Recommendations"""
    result = TestResult("05_category_personalization", test_case["name"])
    
    category_config = test_case.get("category_detection", {})
    
    def count_category_matches(episodes: List[Dict], category: str) -> int:
        config = category_config.get(category, {})
        series_keywords = [k.lower() for k in config.get("series_keywords", [])]
        content_keywords = [k.lower() for k in config.get("content_keywords", [])]
        
        count = 0
        for ep in episodes[:10]:
            series_name = ep.get("series", {}).get("name", "").lower()
            key_insight = (ep.get("key_insight") or "").lower()
            
            series_match = any(kw in series_name for kw in series_keywords)
            content_match = any(kw in key_insight for kw in content_keywords)
            
            if series_match or content_match:
                count += 1
        
        return count
    
    # Criterion 1: AI/Tech profile gets AI content
    ai_match_count = count_category_matches(ai_response.get("episodes", []), "ai_tech")
    result.add_criterion(
        "ai_tech_category_match",
        "Profile 02 (AI/Tech): At least 5 of top 10 are AI/Tech related",
        ai_match_count >= 5,
        f"ai_tech_matches={ai_match_count}/10"
    )
    
    # Criterion 2: Crypto profile gets crypto content
    crypto_match_count = count_category_matches(crypto_response.get("episodes", []), "crypto_web3")
    result.add_criterion(
        "crypto_category_match",
        "Profile 03 (Crypto): At least 5 of top 10 are Crypto/Web3 related",
        crypto_match_count >= 5,
        f"crypto_matches={crypto_match_count}/10"
    )
    
    return result


def validate_recency_scoring(response: Dict, test_case: Dict) -> TestResult:
    """Test 06: Recency Scoring Works"""
    result = TestResult("06_recency_scoring", test_case["name"])
    result.api_response = response
    
    episodes = response.get("episodes", [])
    
    test_pair = test_case.get("setup", {}).get("test_episode_pair", {})
    recent_id = test_pair.get("recent", {}).get("id", "uJLuvlba870Dje0TDoOo")
    older_id = test_pair.get("older", {}).get("id", "JEQEzGoCESXzJtBGb4Dl")
    
    recent_ep = next((ep for ep in episodes if ep["id"] == recent_id), None)
    older_ep = next((ep for ep in episodes if ep["id"] == older_id), None)
    
    both_found = recent_ep is not None and older_ep is not None
    result.add_criterion(
        "both_in_top_10",
        "Both test episodes found in top 10 cold start results",
        both_found,
        f"recent_found={recent_ep is not None}, older_found={older_ep is not None}"
    )
    
    if both_found:
        recent_rec_score = recent_ep.get("recency_score", 0) or 0
        older_rec_score = older_ep.get("recency_score", 0) or 0
        recency_delta = recent_rec_score - older_rec_score
        result.add_criterion(
            "recency_score_ordering",
            "Recent episode has higher recency_score than older",
            recent_rec_score > older_rec_score,
            f"recent={recent_rec_score:.4f}, older={older_rec_score:.4f}, delta={recency_delta:.4f}"
        )
        
        recent_pos = recent_ep.get("queue_position", 999)
        older_pos = older_ep.get("queue_position", 999)
        pos_delta = older_pos - recent_pos  # Positive means recent ranks better
        result.add_criterion(
            "ranking_reflects_recency",
            "Recent episode ranks higher (lower position) than older",
            recent_pos < older_pos,
            f"recent_pos={recent_pos}, older_pos={older_pos}, delta={pos_delta}"
        )
    
    return result


def validate_bookmark_weighting(bookmark_response: Dict, click_response: Dict, test_case: Dict) -> TestResult:
    """Test 07: Bookmark Weighting"""
    result = TestResult("07_bookmark_weighting", test_case["name"])
    
    scenario_a_ids = set(ep["id"] for ep in bookmark_response.get("episodes", [])[:10])
    scenario_b_ids = set(ep["id"] for ep in click_response.get("episodes", [])[:10])
    
    different_episodes = len(scenario_a_ids.symmetric_difference(scenario_b_ids))
    result.add_criterion(
        "different_results",
        "Scenarios produce different recommendations (at least 2 different episodes)",
        different_episodes >= 2,
        details=f"different_episodes={different_episodes}"
    )
    
    crypto_keywords = ['crypto', 'bitcoin', 'ethereum', 'web3', 'blockchain', 'defi', 'btc', 'eth']
    
    def count_crypto(response):
        count = 0
        for ep in response.get("episodes", [])[:10]:
            title = ep.get("title", "").lower()
            insight = (ep.get("key_insight", "") or "").lower()
            if any(kw in title or kw in insight for kw in crypto_keywords):
                count += 1
        return count
    
    scenario_a_crypto = count_crypto(bookmark_response)
    scenario_b_crypto = count_crypto(click_response)
    crypto_delta = scenario_b_crypto - scenario_a_crypto
    
    result.add_criterion(
        "crypto_dominance_in_b",
        "Scenario B (bookmark crypto) has more crypto episodes than Scenario A",
        scenario_b_crypto > scenario_a_crypto,
        details=f"scenario_a_crypto={scenario_a_crypto}/10, scenario_b_crypto={scenario_b_crypto}/10, delta={crypto_delta}"
    )
    
    return result


def validate_series_diversity(response: Dict, test_case: Dict) -> TestResult:
    """Test 08: Series Diversity (max 2 per series, no adjacent same series)"""
    result = TestResult("08_series_diversity", test_case["name"])
    result.api_response = response

    episodes = response.get("episodes", [])[:10]

    # Criterion 1: Still returns 10 results
    episode_count = len(episodes)
    result.add_criterion(
        "still_returns_results",
        "System returns 10 valid recommendations",
        episode_count == 10,
        f"episode_count={episode_count}"
    )

    if len(episodes) < 10:
        return result

    # Extract series ids (episode.series.id)
    def _series_id(ep: Dict) -> str:
        ser = ep.get("series")
        if ser and isinstance(ser, dict):
            return ser.get("id") or ""
        return ""

    series_ids = [_series_id(ep) for ep in episodes]

    # Criterion 2: Max 2 per series
    counts = Counter(sid for sid in series_ids if sid)
    max_count = max(counts.values()) if counts else 0
    max_per_series_ok = max_count <= 2
    result.add_criterion(
        "max_per_series",
        "No series appears more than 2 times in top 10",
        max_per_series_ok,
        f"max_per_series={max_count}, counts={dict(counts)}"
    )

    # Criterion 3: No adjacent same series
    adjacent_violations = []
    for i in range(len(series_ids) - 1):
        if series_ids[i] and series_ids[i] == series_ids[i + 1]:
            adjacent_violations.append((i + 1, i + 2, series_ids[i]))
    no_adjacent_ok = len(adjacent_violations) == 0
    result.add_criterion(
        "no_adjacent_same_series",
        "No two consecutive episodes in top 10 are from the same series",
        no_adjacent_ok,
        f"violations={adjacent_violations}" if adjacent_violations else "none"
    )

    return result


# ============================================================================
# LLM Evaluation (Multi-LLM Judge)
# ============================================================================

async def run_llm_evaluation(
    test_case: Dict,
    profile: Optional[Dict],
    response: Dict,
    verbose: bool = False
) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Run multi-LLM evaluation for a test case.
    
    Evaluates all 4 standard LLM criteria (relevance, diversity, quality, hypothesis_alignment)
    plus any additional criteria specified in the test case.
    
    Also generates a per-test LLM summary with observations and suggestions.
    
    Returns:
        Tuple of (criterion_results, llm_evaluation_summary)
    """
    if not HAS_JUDGES:
        if verbose:
            print(f"  [LLM] Skipped - judges package not available: {_JUDGES_IMPORT_ERROR}")
        return [], None
    
    # Get criteria for this test
    llm_config = test_case.get("llm_criteria", {})
    if not llm_config.get("enabled", True):
        if verbose:
            print("  [LLM] Skipped - llm_criteria.enabled is false")
        return [], None
    
    # Always include the 4 standard LLM criteria
    criteria_ids = set(STANDARD_LLM_CRITERIA)
    
    # Add any additional focus areas from test case
    focus_areas = llm_config.get("focus_areas", [])
    criteria_ids.update(focus_areas)
    
    # Load all requested criteria
    llm_criteria = []
    for cid in criteria_ids:
        criterion = get_criterion(cid)
        if criterion and criterion.get("type") == "llm":
            llm_criteria.append(criterion)
    
    if not llm_criteria:
        if verbose:
            print("  [LLM] Skipped - no LLM criteria available")
        return [], None
    
    if verbose:
        providers = get_available_providers()
        criteria_names = [c.get("id") for c in llm_criteria]
        print(f"  [LLM] Running evaluation with {len(llm_criteria)} criteria: {criteria_names}")
        print(f"  [LLM] Providers: {providers}")
    
    try:
        config = load_judge_config()
        results = await evaluate_all_criteria(
            criteria=llm_criteria,
            profile=profile,
            response=response,
            test_case=test_case,
            config=config
        )
        
        if verbose:
            for r in results:
                if r.get("error"):
                    print(f"  [LLM] {r.get('criterion_id')}: ERROR - {r.get('error')}")
                else:
                    score = r.get("final_score") or r.get("score", 0)
                    consensus = r.get("consensus_level", "N/A")
                    passed = "✓" if r.get("passed") else "✗"
                    print(f"  [LLM] {r.get('criterion_id')}: {passed} score={score:.1f} consensus={consensus}")
        
        # Generate per-test summary with observations and suggestions
        llm_evaluation = await generate_test_summary(
            test_case=test_case,
            profile=profile,
            response=response,
            criterion_results=results,
            config=config,
            verbose=verbose
        )
        
        return results, llm_evaluation
    
    except Exception as e:
        if verbose:
            print(f"  [LLM] Error: {e}")
        return [{"error": str(e)}], None


async def generate_test_summary(
    test_case: Dict,
    profile: Optional[Dict],
    response: Dict,
    criterion_results: List[Dict],
    config: Dict,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Generate a per-test LLM summary with observations and suggestions.
    
    This mirrors the old infrastructure's llm_evaluation block with:
    - summary: 1-2 sentence overview
    - quality_score: 1-5 overall quality rating
    - observations: Array of specific findings
    - suggestions: Array of actionable improvements
    """
    from judges.prompt_builder import format_profile_summary, format_recommendations_summary
    
    # Build context for summary generation
    test_name = test_case.get("name", "Unknown Test")
    test_description = test_case.get("description", "")
    
    # Format criterion results
    criterion_summary_lines = []
    for r in criterion_results:
        if r.get("error"):
            continue
        cid = r.get("criterion_id", "unknown")
        score = r.get("final_score") or r.get("score", 0)
        passed = "PASSED" if r.get("passed") else "FAILED"
        reasoning = ""
        if r.get("reasoning_summary"):
            reasoning = r["reasoning_summary"][0].split("]", 1)[-1].strip()[:200]
        criterion_summary_lines.append(f"- {cid}: {score}/10 ({passed}) - {reasoning}")
    
    criterion_summary = "\n".join(criterion_summary_lines) if criterion_summary_lines else "No criteria evaluated"
    
    # Profile summary
    profile_summary = "Cold start user (no engagements)"
    if profile and profile.get("engagements"):
        profile_summary = format_profile_summary(profile)
    
    # Build prompt for summary generation
    summary_prompt = f"""You are analyzing the results of a recommendation system evaluation test.

## Test Case
Name: {test_name}
Description: {test_description}

## User Profile
{profile_summary}

## LLM Criterion Results
{criterion_summary}

## Task
Generate a structured evaluation summary. You must respond with ONLY valid JSON:

{{
    "summary": "<1-2 sentence overview of test performance>",
    "quality_score": <1-5 integer: 1=critical failure, 3=partial success, 5=excellent>,
    "observations": [
        "<specific finding 1>",
        "<specific finding 2>",
        "<specific finding 3>"
    ],
    "suggestions": [
        "<actionable improvement 1>",
        "<actionable improvement 2>"
    ]
}}

Focus on:
- Whether the test passed or failed and why
- Specific strengths or weaknesses observed
- Actionable improvements if any criteria failed

Respond with ONLY the JSON object, no markdown."""

    try:
        # Use primary available provider for summary
        providers = get_available_providers()
        if not providers:
            return None
        
        provider = providers[0]  # Use first available
        
        result = await call_llm(
            provider=provider,
            prompt=summary_prompt,
            temperature=0.3,  # Lower temperature for consistent summaries
        )
        
        # Add timestamp
        result["evaluated_at"] = datetime.now().isoformat()
        
        if verbose:
            quality = result.get("quality_score", "?")
            print(f"  [LLM] Summary generated: quality_score={quality}")
        
        return result
    
    except Exception as e:
        if verbose:
            print(f"  [LLM] Summary generation error: {e}")
        return {
            "summary": "Summary generation failed",
            "quality_score": 0,
            "observations": [f"Error generating summary: {str(e)}"],
            "suggestions": [],
            "evaluated_at": datetime.now().isoformat()
        }


# ============================================================================
# Legacy Single-LLM Evaluation (for comparison)
# ============================================================================

def run_legacy_llm_evaluation(
    test_case: Dict,
    profile: Optional[Dict],
    response: Dict,
    verbose: bool = False
) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Run legacy single-LLM evaluation using the deprecated llm_judge.
    
    This matches the original infrastructure output format for comparison.
    
    Returns:
        Tuple of (criterion_results, llm_evaluation)
    """
    if not HAS_LEGACY:
        if verbose:
            print("  [LEGACY] Not available - deprecated/llm_judge.py not found")
        return [], None
    
    if verbose:
        print("  [LEGACY] Running single-LLM evaluation (Gemini)")
    
    try:
        # Call legacy evaluation
        llm_result = legacy_evaluate_with_llm(profile or {}, response, test_case)
        
        if llm_result.get("error"):
            if verbose:
                print(f"  [LEGACY] Error: {llm_result.get('error')}")
            return [], None
        
        # Convert legacy scores (1-5) to new format (1-10) with confidence
        criterion_results = []
        
        # Map legacy scores to criterion results
        legacy_mapping = {
            "relevance": ("relevance_score", "LLM Judge: Recommendations match user interests and Content Hypothesis"),
            "diversity": ("diversity_score", "LLM Judge: Appropriate variety for user's exploration/specialization profile"),
            "quality": ("quality_score", "LLM Judge: High-quality, credible sources surfaced"),
            "hypothesis_alignment": ("content_hypothesis_alignment", "LLM Judge: Recommendations align with Content Hypothesis"),
        }
        
        for criterion_id, (legacy_key, description) in legacy_mapping.items():
            score_1_5 = llm_result.get(legacy_key)
            if score_1_5 is not None:
                # Convert 1-5 to 1-10 scale
                score_1_10 = score_1_5 * 2
                threshold = 6.0
                passed = score_1_10 >= threshold
                
                criterion_results.append({
                    "criterion_id": criterion_id,
                    "criterion_type": "llm",
                    "final_score": score_1_10,
                    "threshold": threshold,
                    "passed": passed,
                    "confidence": 0.9,  # Legacy has no multi-model consensus
                    "consensus_level": "SINGLE_MODEL",
                    "n_models": 1,
                    "reasoning_summary": [f"[gemini] {llm_result.get('rationale', '')}"],
                    "model_results": {
                        "gemini": {
                            "samples": [score_1_10],
                            "mean_score": score_1_10,
                            "std": 0.0,
                            "n": 1
                        }
                    }
                })
        
        # Build llm_evaluation summary (legacy format already has this)
        llm_evaluation = {
            "summary": llm_result.get("rationale", ""),
            "quality_score": llm_result.get("quality_score", 3),
            "observations": [
                f"Relevance: {llm_result.get('relevance_score', 'N/A')}/5",
                f"Diversity: {llm_result.get('diversity_score', 'N/A')}/5",
                f"Quality: {llm_result.get('quality_score', 'N/A')}/5",
                f"Hypothesis Alignment: {llm_result.get('content_hypothesis_alignment', 'N/A')}/5"
            ],
            "suggestions": [],
            "test_pass": llm_result.get("test_pass", False),
            "evaluated_at": datetime.now().isoformat(),
            "mode": "legacy_single_llm"
        }
        
        if verbose:
            for r in criterion_results:
                score = r.get("final_score", 0)
                passed = "✓" if r.get("passed") else "✗"
                print(f"  [LEGACY] {r.get('criterion_id')}: {passed} score={score:.1f}")
        
        return criterion_results, llm_evaluation
    
    except Exception as e:
        if verbose:
            print(f"  [LEGACY] Error: {e}")
        return [], None


# ============================================================================
# Test Runner
# ============================================================================

async def run_test_async(
    test_id: str,
    profiles: Dict[str, Dict],
    verbose: bool = False,
    skip_llm: bool = False,
    legacy_mode: bool = False,
    engine_context: Optional[EngineContext] = None
) -> TestResult:
    """
    Run a single test case with async LLM evaluation.
    
    Args:
        test_id: Test case identifier
        profiles: Dict of profile_id -> profile data
        verbose: Show detailed output
        skip_llm: Skip LLM evaluation (deterministic only)
        legacy_mode: Use legacy single-LLM evaluation
        engine_context: If provided, use direct engine calls. If None, use API calls.
    """
    test_case = load_test_case(test_id)
    evaluation_method = test_case.get("evaluation_method", "deterministic_llm")
    
    mode_str = " [LEGACY]" if legacy_mode else ""
    if verbose:
        print(f"\n{'='*60}")
        print(f"Running: {test_case['name']}{mode_str}")
        print(f"Type: {test_case['type']} | Method: {evaluation_method}")
        print(f"{'='*60}")
    
    # Helper to get recommendations (either via engine or API)
    def get_recommendations(profile: Dict) -> Dict:
        """Get recommendations using engine context or API."""
        if engine_context:
            engagements = [
                {"episode_id": e["episode_id"], "type": e.get("type", "click"), "timestamp": e.get("timestamp", "")}
                for e in profile.get("engagements", [])
            ]
            excluded_ids = set(profile.get("excluded_ids", []))
            return call_engine_directly(engagements, excluded_ids, engine_context)
        else:
            return call_api_with_profile(profile)
    
    try:
        # Run deterministic validation first
        if test_id == "01_cold_start_quality":
            profile = profiles.get("01_cold_start", {"engagements": [], "excluded_ids": []})
            response = get_recommendations(profile)
            result = validate_cold_start_quality(response, test_case)
            result.test_type = test_case.get("type", "MFT")
            result.set_llm_judge_context(profile, response.get("episodes", []))
            
            if not skip_llm and evaluation_method in ("deterministic_llm", "llm_only"):
                if legacy_mode:
                    llm_results, llm_evaluation = run_legacy_llm_evaluation(test_case, profile, response, verbose)
                else:
                    llm_results, llm_evaluation = await run_llm_evaluation(test_case, profile, response, verbose)
                if llm_results:
                    result.add_llm_results(llm_results)
                if llm_evaluation:
                    result.set_llm_evaluation(llm_evaluation)
        
        elif test_id == "02_personalization_differs":
            cold_profile = profiles.get("01_cold_start", {"engagements": [], "excluded_ids": []})
            vc_profile = profiles.get("02_vc_partner_ai_tech")
            
            cold_response = get_recommendations(cold_profile)
            vc_response = get_recommendations(vc_profile)
            
            result = validate_personalization_differs(cold_response, vc_response, test_case)
            result.test_type = test_case.get("type", "MFT")
            result.set_llm_judge_context(vc_profile, vc_response.get("episodes", []))
            
            if not skip_llm and evaluation_method in ("deterministic_llm", "llm_only"):
                if legacy_mode:
                    llm_results, llm_evaluation = run_legacy_llm_evaluation(test_case, vc_profile, vc_response, verbose)
                else:
                    llm_results, llm_evaluation = await run_llm_evaluation(test_case, vc_profile, vc_response, verbose)
                if llm_results:
                    result.add_llm_results(llm_results)
                if llm_evaluation:
                    result.set_llm_evaluation(llm_evaluation)
        
        elif test_id == "03_quality_gates_credibility":
            responses = {}
            for profile_id, profile in profiles.items():
                responses[profile_id] = get_recommendations(profile)
            result = validate_quality_gates(responses, test_case)
            result.test_type = test_case.get("type", "MFT")
        
        elif test_id == "04_excluded_episodes":
            profile = profiles.get("02_vc_partner_ai_tech").copy()
            excluded_ids = test_case["setup"]["modifications"]["excluded_ids"]
            profile["excluded_ids"] = excluded_ids
            response = get_recommendations(profile)
            result = validate_excluded_episodes(response, excluded_ids, test_case)
            result.test_type = test_case.get("type", "MFT")
        
        elif test_id == "05_category_personalization":
            ai_profile = profiles.get("02_vc_partner_ai_tech")
            crypto_profile = profiles.get("03_crypto_web3_investor")
            
            ai_response = get_recommendations(ai_profile)
            crypto_response = get_recommendations(crypto_profile)
            
            result = validate_category_personalization(ai_response, crypto_response, test_case)
            result.test_type = test_case.get("type", "DIR")
            result.set_llm_judge_context(ai_profile, ai_response.get("episodes", []))
            
            if not skip_llm and evaluation_method in ("deterministic_llm", "llm_only"):
                if legacy_mode:
                    llm_results, llm_evaluation = run_legacy_llm_evaluation(test_case, ai_profile, ai_response, verbose)
                else:
                    llm_results, llm_evaluation = await run_llm_evaluation(test_case, ai_profile, ai_response, verbose)
                if llm_results:
                    result.add_llm_results(llm_results)
                if llm_evaluation:
                    result.set_llm_evaluation(llm_evaluation)
        
        elif test_id == "06_recency_scoring":
            profile = profiles.get("01_cold_start", {"engagements": [], "excluded_ids": []})
            response = get_recommendations(profile)
            result = validate_recency_scoring(response, test_case)
            result.test_type = test_case.get("type", "DIR")
        
        elif test_id == "07_bookmark_weighting":
            setup = test_case["setup"]
            
            # Create temporary profiles for scenarios
            scenario_a_profile = {
                "engagements": setup["scenario_a"]["engagements"],
                "excluded_ids": setup["scenario_a"]["excluded_ids"]
            }
            scenario_b_profile = {
                "engagements": setup["scenario_b"]["engagements"],
                "excluded_ids": setup["scenario_b"]["excluded_ids"]
            }
            
            bookmark_response = get_recommendations(scenario_a_profile)
            click_response = get_recommendations(scenario_b_profile)
            
            result = validate_bookmark_weighting(bookmark_response, click_response, test_case)
            result.test_type = test_case.get("type", "DIR")
            
            # Build profile for LLM context
            scenario_b_profile = {
                "profile_id": "scenario_b_bookmark",
                "name": "Bookmark Weighting Test - Scenario B",
                "description": "User who has bookmarked crypto content.",
                "icp_segment": "Test Scenario",
                "engagements": setup["scenario_b"]["engagements"]
            }
            result.set_llm_judge_context(scenario_b_profile, click_response.get("episodes", []))
            
            if not skip_llm and evaluation_method in ("deterministic_llm", "llm_only"):
                if legacy_mode:
                    llm_results, llm_evaluation = run_legacy_llm_evaluation(test_case, scenario_b_profile, click_response, verbose)
                else:
                    llm_results, llm_evaluation = await run_llm_evaluation(test_case, scenario_b_profile, click_response, verbose)
                if llm_results:
                    result.add_llm_results(llm_results)
                if llm_evaluation:
                    result.set_llm_evaluation(llm_evaluation)
        
        elif test_id == "08_series_diversity":
            profile = profiles.get("01_cold_start", {"engagements": [], "excluded_ids": []})
            response = get_recommendations(profile)
            result = validate_series_diversity(response, test_case)
            result.test_type = test_case.get("type", "MFT")
        
        else:
            result = TestResult(test_id, f"Unknown test: {test_id}")
            result.set_error(f"No validator implemented for test: {test_id}")
        
        result.evaluation_method = evaluation_method
        return result
    
    except Exception as e:
        result = TestResult(test_id, test_case.get("name", test_id))
        result.set_error(str(e))
        return result


def run_test(test_id: str, profiles: Dict[str, Dict], verbose: bool = False, skip_llm: bool = False, legacy_mode: bool = False, engine_context: Optional[EngineContext] = None) -> TestResult:
    """Synchronous wrapper for run_test_async."""
    return asyncio.run(run_test_async(test_id, profiles, verbose, skip_llm, legacy_mode, engine_context))


async def run_all_tests_async(
    verbose: bool = False,
    skip_llm: bool = False,
    method_filter: Optional[str] = None,
    legacy_mode: bool = False,
    engine_context: Optional[EngineContext] = None
) -> List[TestResult]:
    """
    Run all test cases.
    
    Args:
        verbose: Show detailed output
        skip_llm: Skip LLM evaluation (deterministic only)
        method_filter: Filter tests by evaluation method
        legacy_mode: Use legacy single-LLM evaluation
        engine_context: If provided, use direct engine calls. If None, use API calls.
    """
    profiles = load_all_profiles()
    test_cases = load_all_test_cases()
    
    results = []
    for test_id in sorted(test_cases.keys()):
        test_case = test_cases[test_id]
        evaluation_method = test_case.get("evaluation_method", "deterministic_llm")
        
        # Filter by method if specified
        if method_filter:
            if method_filter == "deterministic" and evaluation_method != "deterministic":
                continue
            elif method_filter == "llm" and evaluation_method not in ("deterministic_llm", "llm_only"):
                continue
        
        result = await run_test_async(test_id, profiles, verbose, skip_llm, legacy_mode, engine_context)
        results.append(result)
        
        if verbose:
            status = "✓ PASSED" if result.passed else "✗ FAILED"
            print(f"\nResult: {status}")
            for cr in result.criteria_results:
                cr_status = "✓" if cr["passed"] else "✗"
                flag = " ⚠️" if cr.get("flag_for_review") else ""
                print(f"  {cr_status} {cr['criterion_id']}: {cr['details']}{flag}")
            if result.error:
                print(f"  ERROR: {result.error}")
    
    return results


def run_all_tests(verbose: bool = False, skip_llm: bool = False, method_filter: Optional[str] = None, legacy_mode: bool = False, engine_context: Optional[EngineContext] = None) -> List[TestResult]:
    """Synchronous wrapper for run_all_tests_async."""
    return asyncio.run(run_all_tests_async(verbose, skip_llm, method_filter, legacy_mode, engine_context))


# ============================================================================
# Output
# ============================================================================

def print_summary(results: List[TestResult], legacy_mode: bool = False):
    """Print test summary with LLM consensus metrics."""
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    llm_count = sum(1 for r in results if r.llm_results)
    flagged = sum(1 for r in results for cr in r.criteria_results if cr.get("flag_for_review"))
    
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total: {len(results)} | Passed: {passed} | Failed: {failed}")
    if llm_count > 0:
        providers = get_available_providers() if HAS_JUDGES else []
        print(f"LLM Evaluated: {llm_count} tests | Providers: {', '.join(providers) or 'N/A'}")
    if flagged > 0:
        print(f"⚠️  Flagged for Review: {flagged} criteria (low consensus)")
    print(f"{'='*60}")
    
    for result in results:
        status = "✓" if result.passed else "✗"
        print(f"{status} {result.test_id}: {result.name}")
        
        if not result.passed:
            for cr in result.criteria_results:
                if not cr["passed"]:
                    flag = " ⚠️" if cr.get("flag_for_review") else ""
                    print(f"    ✗ {cr['criterion_id']}: {cr['details']}{flag}")
            if result.error:
                print(f"    ERROR: {result.error}")
        
        # Show LLM summary for passed tests with LLM evaluation
        elif result.llm_results:
            llm_scores = []
            for r in result.llm_results:
                if not r.get("error"):
                    score = r.get("final_score") or r.get("score", 0)
                    llm_scores.append(f"{r.get('criterion_id')}={score:.1f}")
            if llm_scores:
                print(f"    [LLM] {', '.join(llm_scores)}")


def save_report(
    results: List[TestResult], 
    legacy_mode: bool = False,
    algorithm_version: Optional[str] = None,
    algorithm_name: Optional[str] = None,
    dataset_version: Optional[str] = None,
    dataset_episode_count: Optional[int] = None
) -> Path:
    """
    Save test results to a JSON report matching old infrastructure format.
    
    Args:
        results: List of test results
        legacy_mode: Whether legacy single-LLM mode was used
        algorithm_version: Algorithm folder name (defaults to ALGORITHM_VERSION env var)
        algorithm_name: Algorithm display name (defaults to loading from algorithm_meta.json)
        dataset_version: Dataset folder name (defaults to env var)
        dataset_episode_count: Number of episodes in dataset (defaults to env var)
    """
    REPORTS_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_suffix = "_legacy" if legacy_mode else ""
    report_path = REPORTS_DIR / f"test_report_{timestamp}{mode_suffix}.json"
    
    # Compute overall statistics
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    pass_rate = round(passed / len(results), 3) if results else 0.0
    
    # Compute per-test scores for score_breakdown
    score_breakdown = {}
    all_scores = []
    all_confidences = []
    
    for r in results:
        scores = r.compute_aggregate_scores()
        score_breakdown[r.test_id] = scores["aggregate_score"]
        all_scores.append(scores["aggregate_score"])
        all_confidences.append(scores["aggregate_confidence"])
    
    overall_score = round(sum(all_scores) / len(all_scores), 2) if all_scores else 0.0
    overall_confidence = round(sum(all_confidences) / len(all_confidences), 2) if all_confidences else 0.0
    
    # Get algorithm metadata (from parameters or env vars)
    algo_version = algorithm_version or os.getenv("ALGORITHM_VERSION", "unknown")
    algo_name = algorithm_name
    
    # If algorithm_name not provided, try to load from algorithm_meta.json
    if not algo_name:
        try:
            algo_path = Path(__file__).parent.parent / "algorithm" / "algorithm_meta.json"
            if algo_path.exists():
                with open(algo_path) as f:
                    meta = json.load(f)
                    algo_name = meta.get("name", algo_version)
            else:
                algo_name = algo_version
        except Exception:
            algo_name = algo_version
    
    # Get dataset metadata (from parameters or env vars)
    dataset_ver = dataset_version or os.getenv("DATASET_VERSION", "eval_909_feb2026")
    episode_count = dataset_episode_count
    
    # If episode_count not provided, try to load from fixtures
    if episode_count is None:
        try:
            episodes_path = Path(__file__).parent / "fixtures" / dataset_ver / "episodes.json"
            if episodes_path.exists():
                with open(episodes_path) as f:
                    episodes = json.load(f)
                    episode_count = len(episodes) if isinstance(episodes, list) else len(episodes.get("episodes", []))
            else:
                episode_count = 909  # Fallback
        except Exception:
            episode_count = 909  # Fallback
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "context": {
            "algorithm_version": algo_version,
            "algorithm_name": algo_name,
            "dataset_version": dataset_ver,
            "dataset_episode_count": episode_count,
            "llm_providers": ["gemini (legacy)"] if legacy_mode else (get_available_providers() if HAS_JUDGES else []),
            "evaluation_mode": "legacy_single_llm" if legacy_mode else "multi_llm"
        },
        "summary": {
            "total_tests": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
            "overall_score": overall_score,
            "overall_confidence": overall_confidence,
            "score_breakdown": score_breakdown
        },
        "results": [r.to_dict() for r in results]
    }
    
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nReport saved: {report_path}")
    return report_path


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Run evaluation tests")
    parser.add_argument("--test", type=str, help="Run specific test (e.g., 01, 02)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--save", "-s", action="store_true", help="Save report to file")
    parser.add_argument("--deterministic-only", action="store_true", 
                        help="Skip LLM evaluation (for quick checks)")
    parser.add_argument("--legacy", action="store_true",
                        help="Use legacy single-LLM evaluation (Gemini only, for comparison)")
    parser.add_argument("--method", type=str, choices=["deterministic", "llm", "all"], 
                        default="all", help="Filter tests by evaluation method")
    args = parser.parse_args()
    
    print("Serafis Evaluation Test Runner")
    print(f"API: {API_BASE_URL}")
    
    # Check for legacy mode
    if args.legacy:
        if not HAS_LEGACY:
            print("ERROR: Legacy evaluation not available (deprecated/llm_judge.py not found)")
            sys.exit(1)
        print("Mode: LEGACY (single-LLM Gemini evaluation)")
        # Set global flag for legacy mode
        global USE_LEGACY_MODE
        USE_LEGACY_MODE = True
    else:
        USE_LEGACY_MODE = False
        # Check LLM availability
        if HAS_JUDGES:
            providers = get_available_providers()
            if providers:
                print(f"LLM Judges: {', '.join(providers)}")
            else:
                print("LLM Judges: No API keys configured (set OPENAI_API_KEY or GEMINI_API_KEY)")
                if not args.deterministic_only:
                    print("  → Running with --deterministic-only")
                    args.deterministic_only = True
        else:
            print(f"LLM Judges: Not available ({_JUDGES_IMPORT_ERROR})")
            args.deterministic_only = True
    
    profiles = load_all_profiles()
    print(f"Loaded {len(profiles)} profiles")
    
    if HAS_JUDGES and not args.legacy:
        print(f"Available criteria: {', '.join(list_criteria())}")
    
    # Determine method filter
    method_filter = None if args.method == "all" else args.method
    
    if args.test:
        test_id = f"{args.test.zfill(2)}_" if len(args.test) <= 2 else args.test
        test_cases = load_all_test_cases()
        matching = [tid for tid in test_cases if tid.startswith(test_id)]
        
        if not matching:
            print(f"No test found matching: {args.test}")
            sys.exit(1)
        
        results = [run_test(matching[0], profiles, args.verbose, args.deterministic_only, args.legacy)]
    else:
        results = run_all_tests(args.verbose, args.deterministic_only, method_filter, args.legacy)
    
    print_summary(results, legacy_mode=args.legacy)
    
    if args.save:
        save_report(results, legacy_mode=args.legacy)
    
    # Exit with error code if any tests failed
    failed = sum(1 for r in results if not r.passed)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
