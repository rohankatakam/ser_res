#!/usr/bin/env python3
"""
Evaluation Test Runner

Executes test cases against the recommendation API and validates results.

Usage:
    python runner.py                    # Run all tests (deterministic only)
    python runner.py --with-llm         # Run all tests with LLM evaluation
    python runner.py --test 01          # Run specific test
    python runner.py --test 01 --with-llm  # Run specific test with LLM
    python runner.py --method deterministic  # Only deterministic tests
    python runner.py --verbose          # Show detailed output
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# Optional LLM judge import
try:
    from llm_judge import evaluate_with_llm
    HAS_LLM_JUDGE = True
except ImportError:
    HAS_LLM_JUDGE = False

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
# API Client
# ============================================================================

def call_api(engagements: List[Dict], excluded_ids: List[str]) -> Dict:
    """Call the recommendation API."""
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
    """Call the API using a profile's engagements."""
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
# Test Validators
# ============================================================================

class TestResult:
    """Result of a single test."""
    def __init__(self, test_id: str, name: str, evaluation_method: str = "deterministic"):
        self.test_id = test_id
        self.name = name
        self.evaluation_method = evaluation_method
        self.passed = True
        self.criteria_results = []
        self.error = None
        self.api_response = None
        self.llm_evaluation = None
    
    def add_criterion(self, criterion_id: str, description: str, passed: bool, details: str = ""):
        self.criteria_results.append({
            "criterion_id": criterion_id,
            "description": description,
            "passed": passed,
            "details": details
        })
        if not passed:
            self.passed = False
    
    def set_error(self, error: str):
        self.error = error
        self.passed = False
    
    def set_llm_evaluation(self, llm_result: Dict):
        """Add LLM evaluation result."""
        self.llm_evaluation = llm_result
        # Add LLM scores as additional criteria if available
        if llm_result and "error" not in llm_result:
            self.add_criterion(
                "llm_relevance",
                f"LLM relevance score (1-5)",
                llm_result.get("relevance_score", 0) >= 3,
                f"score={llm_result.get('relevance_score')}"
            )
            self.add_criterion(
                "llm_quality",
                f"LLM quality score (1-5)",
                llm_result.get("quality_score", 0) >= 3,
                f"score={llm_result.get('quality_score')}"
            )
            self.add_criterion(
                "llm_test_pass",
                "LLM judge test pass",
                llm_result.get("test_pass", False),
                f"pass={llm_result.get('test_pass')}, rationale={llm_result.get('rationale', '')[:100]}..."
            )
    
    def to_dict(self) -> Dict:
        return {
            "test_id": self.test_id,
            "name": self.name,
            "evaluation_method": self.evaluation_method,
            "passed": self.passed,
            "criteria_results": self.criteria_results,
            "error": self.error,
            "llm_evaluation": self.llm_evaluation
        }


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
    
    result.add_criterion(
        "similarity_increase",
        "VC Partner has higher avg similarity_score than cold start",
        avg_vc_sim > avg_cold_sim,
        f"cold_avg={avg_cold_sim:.3f}, vc_avg={avg_vc_sim:.3f}"
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
            
            # Check series match
            series_match = any(kw in series_name for kw in series_keywords)
            # Check content match
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


def validate_bookmark_weighting(bookmark_response: Dict, click_response: Dict, test_case: Dict) -> TestResult:
    """Test 06: Bookmarks Outweigh Clicks"""
    result = TestResult("06_bookmark_weighting", test_case["name"])
    
    # Get similarity scores
    bookmark_sims = [ep.get("similarity_score", 0) or 0 for ep in bookmark_response.get("episodes", [])[:10]]
    click_sims = [ep.get("similarity_score", 0) or 0 for ep in click_response.get("episodes", [])[:10]]
    
    avg_bookmark_sim = sum(bookmark_sims) / len(bookmark_sims) if bookmark_sims else 0
    avg_click_sim = sum(click_sims) / len(click_sims) if click_sims else 0
    
    result.add_criterion(
        "higher_similarity",
        "Bookmarks have higher avg similarity_score than clicks",
        avg_bookmark_sim > avg_click_sim,
        f"bookmark_avg={avg_bookmark_sim:.4f}, click_avg={avg_click_sim:.4f}"
    )
    
    return result


def validate_recency_scoring(response: Dict, test_case: Dict) -> TestResult:
    """Test 07: Recency Scoring Works"""
    result = TestResult("07_recency_scoring", test_case["name"])
    result.api_response = response
    
    episodes = response.get("episodes", [])
    
    # Find the test episodes
    recent_id = "10FJ6iMqTrV0LJul40zA"
    older_id = "azcjy2HqnbPneTMU5Ylp"
    
    recent_ep = next((ep for ep in episodes if ep["id"] == recent_id), None)
    older_ep = next((ep for ep in episodes if ep["id"] == older_id), None)
    
    if recent_ep and older_ep:
        # Criterion 1: Recency score ordering
        recent_rec_score = recent_ep.get("recency_score", 0) or 0
        older_rec_score = older_ep.get("recency_score", 0) or 0
        result.add_criterion(
            "recency_score_ordering",
            "Recent episode has higher recency_score than older",
            recent_rec_score > older_rec_score,
            f"recent={recent_rec_score:.4f}, older={older_rec_score:.4f}"
        )
        
        # Criterion 2: Ranking order
        recent_pos = recent_ep.get("queue_position", 999)
        older_pos = older_ep.get("queue_position", 999)
        result.add_criterion(
            "ranking_reflects_recency",
            "Recent episode ranks higher (lower position) than older",
            recent_pos < older_pos,
            f"recent_pos={recent_pos}, older_pos={older_pos}"
        )
        
        # Criterion 3: Final score
        recent_final = recent_ep.get("final_score", 0) or 0
        older_final = older_ep.get("final_score", 0) or 0
        result.add_criterion(
            "final_score_difference",
            "Recent episode has higher final_score",
            recent_final > older_final,
            f"recent_final={recent_final:.4f}, older_final={older_final:.4f}"
        )
    else:
        result.add_criterion(
            "episodes_found",
            "Both test episodes found in response",
            False,
            f"recent_found={recent_ep is not None}, older_found={older_ep is not None}"
        )
    
    return result


# ============================================================================
# Test Runner
# ============================================================================

def run_llm_evaluation(
    test_id: str,
    test_case: Dict,
    profile: Dict,
    response: Dict,
    verbose: bool = False
) -> Optional[Dict]:
    """Run LLM evaluation for a test if applicable."""
    if not HAS_LLM_JUDGE:
        if verbose:
            print("  [LLM] Skipped - llm_judge module not available")
        return None
    
    try:
        if verbose:
            print("  [LLM] Running evaluation...")
        llm_result = evaluate_with_llm(profile, response, test_case)
        if verbose:
            if "error" in llm_result:
                print(f"  [LLM] Error: {llm_result['error']}")
            else:
                print(f"  [LLM] Relevance: {llm_result.get('relevance_score')}/5, "
                      f"Quality: {llm_result.get('quality_score')}/5, "
                      f"Pass: {llm_result.get('test_pass')}")
        return llm_result
    except Exception as e:
        if verbose:
            print(f"  [LLM] Error: {e}")
        return {"error": str(e)}


def run_test(test_id: str, profiles: Dict[str, Dict], verbose: bool = False, with_llm: bool = False) -> TestResult:
    """Run a single test case."""
    test_case = load_test_case(test_id)
    evaluation_method = test_case.get("evaluation_method", "deterministic")
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Running: {test_case['name']}")
        print(f"Type: {test_case['type']} | Method: {evaluation_method}")
        print(f"{'='*60}")
    
    # Check if LLM evaluation is needed
    needs_llm = with_llm and evaluation_method in ("deterministic_llm", "llm_only")
    
    try:
        if test_id == "01_cold_start_quality":
            profile = profiles.get("01_cold_start", {"engagements": [], "excluded_ids": []})
            response = call_api_with_profile(profile)
            result = validate_cold_start_quality(response, test_case)
            result.evaluation_method = evaluation_method
            
            # Add LLM evaluation
            if needs_llm:
                llm_result = run_llm_evaluation(test_id, test_case, profile, response, verbose)
                if llm_result:
                    result.set_llm_evaluation(llm_result)
            
            return result
        
        elif test_id == "02_personalization_differs":
            cold_profile = profiles.get("01_cold_start", {"engagements": [], "excluded_ids": []})
            vc_profile = profiles.get("02_vc_partner_ai_tech")
            
            cold_response = call_api_with_profile(cold_profile)
            vc_response = call_api_with_profile(vc_profile)
            
            result = validate_personalization_differs(cold_response, vc_response, test_case)
            result.evaluation_method = evaluation_method
            
            # Add LLM evaluation (evaluate the personalized response)
            if needs_llm:
                llm_result = run_llm_evaluation(test_id, test_case, vc_profile, vc_response, verbose)
                if llm_result:
                    result.set_llm_evaluation(llm_result)
            
            return result
        
        elif test_id == "03_quality_gates_credibility":
            responses = {}
            for profile_id, profile in profiles.items():
                responses[profile_id] = call_api_with_profile(profile)
            result = validate_quality_gates(responses, test_case)
            result.evaluation_method = evaluation_method
            return result
        
        elif test_id == "04_excluded_episodes":
            profile = profiles.get("02_vc_partner_ai_tech").copy()
            excluded_ids = test_case["setup"]["modifications"]["excluded_ids"]
            profile["excluded_ids"] = excluded_ids
            response = call_api_with_profile(profile)
            result = validate_excluded_episodes(response, excluded_ids, test_case)
            result.evaluation_method = evaluation_method
            return result
        
        elif test_id == "05_category_personalization":
            ai_profile = profiles.get("02_vc_partner_ai_tech")
            crypto_profile = profiles.get("03_crypto_web3_investor")
            
            ai_response = call_api_with_profile(ai_profile)
            crypto_response = call_api_with_profile(crypto_profile)
            
            result = validate_category_personalization(ai_response, crypto_response, test_case)
            result.evaluation_method = evaluation_method
            
            # Add LLM evaluation (evaluate the AI/Tech profile response)
            if needs_llm:
                llm_result = run_llm_evaluation(test_id, test_case, ai_profile, ai_response, verbose)
                if llm_result:
                    result.set_llm_evaluation(llm_result)
            
            return result
        
        elif test_id == "06_bookmark_weighting":
            # Create custom scenarios from test case
            setup = test_case["setup"]
            
            bookmark_engagements = setup["scenario_a"]["engagements"]
            click_engagements = setup["scenario_b"]["engagements"]
            
            bookmark_response = call_api(bookmark_engagements, setup["scenario_a"]["excluded_ids"])
            click_response = call_api(click_engagements, setup["scenario_b"]["excluded_ids"])
            
            result = validate_bookmark_weighting(bookmark_response, click_response, test_case)
            result.evaluation_method = evaluation_method
            
            # Add LLM evaluation (evaluate the bookmark scenario)
            if needs_llm:
                # Create a synthetic profile for LLM evaluation
                bookmark_profile = {
                    "profile_id": "bookmark_scenario",
                    "name": "Bookmark Scenario User",
                    "description": "User who bookmarked 3 AI episodes",
                    "engagements": setup["scenario_a"]["engagements"]
                }
                llm_result = run_llm_evaluation(test_id, test_case, bookmark_profile, bookmark_response, verbose)
                if llm_result:
                    result.set_llm_evaluation(llm_result)
            
            return result
        
        elif test_id == "07_recency_scoring":
            profile = profiles.get("01_cold_start", {"engagements": [], "excluded_ids": []})
            response = call_api_with_profile(profile)
            result = validate_recency_scoring(response, test_case)
            result.evaluation_method = evaluation_method
            return result
        
        else:
            result = TestResult(test_id, f"Unknown test: {test_id}", evaluation_method)
            result.set_error(f"No validator implemented for test: {test_id}")
            return result
    
    except Exception as e:
        result = TestResult(test_id, test_case.get("name", test_id), evaluation_method)
        result.set_error(str(e))
        return result


def run_all_tests(verbose: bool = False, with_llm: bool = False, method_filter: str = None) -> List[TestResult]:
    """Run all test cases.
    
    Args:
        verbose: Show detailed output
        with_llm: Run LLM evaluation for applicable tests
        method_filter: Only run tests with this evaluation_method (deterministic, deterministic_llm, llm_only)
    """
    profiles = load_all_profiles()
    test_cases = load_all_test_cases()
    
    results = []
    for test_id in sorted(test_cases.keys()):
        test_case = test_cases[test_id]
        evaluation_method = test_case.get("evaluation_method", "deterministic")
        
        # Filter by method if specified
        if method_filter:
            if method_filter == "deterministic" and evaluation_method != "deterministic":
                continue
            elif method_filter == "llm" and evaluation_method not in ("deterministic_llm", "llm_only"):
                continue
        
        result = run_test(test_id, profiles, verbose, with_llm)
        results.append(result)
        
        if verbose:
            status = "✓ PASSED" if result.passed else "✗ FAILED"
            print(f"\nResult: {status}")
            for cr in result.criteria_results:
                cr_status = "✓" if cr["passed"] else "✗"
                print(f"  {cr_status} {cr['criterion_id']}: {cr['details']}")
            if result.error:
                print(f"  ERROR: {result.error}")
    
    return results


def print_summary(results: List[TestResult]):
    """Print test summary."""
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    llm_count = sum(1 for r in results if r.llm_evaluation is not None)
    
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total: {len(results)} | Passed: {passed} | Failed: {failed}")
    if llm_count > 0:
        print(f"LLM Evaluated: {llm_count}")
    print(f"{'='*60}")
    
    for result in results:
        status = "✓" if result.passed else "✗"
        method_label = f"[{result.evaluation_method}]" if result.evaluation_method != "deterministic" else ""
        print(f"{status} {result.test_id}: {result.name} {method_label}")
        if not result.passed:
            for cr in result.criteria_results:
                if not cr["passed"]:
                    print(f"    ✗ {cr['criterion_id']}: {cr['details']}")
            if result.error:
                print(f"    ERROR: {result.error}")
        
        # Show LLM summary if available
        if result.llm_evaluation and "error" not in result.llm_evaluation:
            llm = result.llm_evaluation
            print(f"    [LLM] R:{llm.get('relevance_score')}/5 D:{llm.get('diversity_score')}/5 "
                  f"Q:{llm.get('quality_score')}/5 Pass:{llm.get('test_pass')}")


def save_report(results: List[TestResult]):
    """Save test results to a JSON report."""
    REPORTS_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"test_report_{timestamp}.json"
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
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
    parser.add_argument("--with-llm", action="store_true", help="Run LLM evaluation for applicable tests")
    parser.add_argument("--method", type=str, choices=["deterministic", "llm", "all"], 
                        default="all", help="Filter tests by evaluation method")
    args = parser.parse_args()
    
    print(f"Serafis Evaluation Test Runner")
    print(f"API: {API_BASE_URL}")
    if args.with_llm:
        if HAS_LLM_JUDGE:
            print("LLM Judge: Enabled (Gemini)")
        else:
            print("LLM Judge: Not available (llm_judge module not found)")
    
    profiles = load_all_profiles()
    print(f"Loaded {len(profiles)} profiles")
    
    # Determine method filter
    method_filter = None if args.method == "all" else args.method
    
    if args.test:
        test_id = f"{args.test.zfill(2)}_" if len(args.test) <= 2 else args.test
        # Find matching test
        test_cases = load_all_test_cases()
        matching = [tid for tid in test_cases if tid.startswith(test_id)]
        
        if not matching:
            print(f"No test found matching: {args.test}")
            sys.exit(1)
        
        results = [run_test(matching[0], profiles, args.verbose, args.with_llm)]
    else:
        results = run_all_tests(args.verbose, args.with_llm, method_filter)
    
    print_summary(results)
    
    if args.save:
        save_report(results)
    
    # Exit with error code if any tests failed
    failed = sum(1 for r in results if not r.passed)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
