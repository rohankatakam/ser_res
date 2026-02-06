#!/usr/bin/env python3
"""
LLM-as-Judge for Recommendation Evaluation

Uses Gemini to evaluate recommendation quality with structured rubrics.

Usage:
    from llm_judge import evaluate_recommendations
    result = evaluate_recommendations(profile, recommendations, test_case)

    # CLI usage:
    python llm_judge.py --profile 02_vc_partner_ai_tech --test 01_cold_start_quality

Note: Requires GEMINI_API_KEY environment variable (or uses default).
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

# Try to import google generative AI, but make it optional
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# Try to import dotenv for .env file loading
try:
    from dotenv import load_dotenv
    # Load .env file from the evaluation directory
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # dotenv not installed, rely on environment variables


# ============================================================================
# Configuration
# ============================================================================

DEFAULT_MODEL = "gemini-2.5-flash"
MAX_OUTPUT_TOKENS = 65535  # Maximum for gemini-2.5-flash


# ============================================================================
# Prompt Templates
# ============================================================================

EVALUATION_PROMPT = """You are evaluating a podcast recommendation system for investors.

## User Profile
{profile_summary}

## Recent Engagements
{engagements_summary}

## For You Feed (Top 10 Recommendations)
{recommendations_summary}

## Test Case Being Evaluated
{test_description}

## Evaluation Criteria

Please evaluate the recommendations on these criteria (1-5 scale):

1. **RELEVANCE** (1-5): Do the recommendations relate to the user's demonstrated interests?
   - 5: All recommendations are highly relevant to user interests
   - 3: Mix of relevant and irrelevant content
   - 1: Recommendations seem random or unrelated

2. **DIVERSITY** (1-5): Is there appropriate variety without being scattered?
   - 5: Good variety within the user's interest areas
   - 3: Some repetition or gaps in coverage
   - 1: Too repetitive or too scattered

3. **QUALITY** (1-5): Are high-quality episodes (credibility ≥3) being surfaced?
   - 5: Top recommendations are all high-quality
   - 3: Mix of quality levels
   - 1: Low-quality content is prominent

4. **TEST_PASS** (true/false): Does this specific test case pass?
   - Evaluate based on the test description provided

5. **RATIONALE**: Explain your evaluation in 2-3 sentences.

## Response Format

You MUST respond with ONLY valid JSON, no markdown code blocks, no additional text:
{{
  "relevance_score": <1-5>,
  "diversity_score": <1-5>,
  "quality_score": <1-5>,
  "test_pass": <true or false>,
  "rationale": "<explanation>"
}}
"""


# ============================================================================
# Helper Functions
# ============================================================================

def format_profile_summary(profile: Dict) -> str:
    """Format profile for LLM prompt."""
    total_engagements = len(profile.get("engagements", []))
    stats = profile.get("stats", {})
    if stats:
        total_engagements = stats.get("total_engagements", total_engagements)
    
    return f"""
Name: {profile.get('name', 'Unknown')}
ICP Segment: {profile.get('icp_segment', 'Unknown')}
Duration: {profile.get('usage_duration', 'Unknown')}
Total Engagements: {total_engagements}
Description: {profile.get('description', '')}
"""


def format_engagements_summary(engagements: List[Dict]) -> str:
    """Format engagements for LLM prompt."""
    if not engagements:
        return "No engagements (cold start user)"
    
    lines = []
    for eng in engagements[-10:]:  # Last 10
        eng_type = eng.get("type", "click")
        title = eng.get("title", eng.get("episode_id", "Unknown"))
        series = eng.get("series", "Unknown")
        lines.append(f"- [{eng_type.upper()}] {title} ({series})")
    
    return "\n".join(lines)


def format_recommendations_summary(episodes: List[Dict]) -> str:
    """Format recommendations for LLM prompt."""
    if not episodes:
        return "No recommendations returned"
    
    lines = []
    for i, ep in enumerate(episodes[:10], 1):
        title = ep.get("title", "Unknown")
        series = ep.get("series", {}).get("name", "Unknown")
        cred = ep.get("scores", {}).get("credibility", 0)
        insight = ep.get("scores", {}).get("insight", 0)
        sim = ep.get("similarity_score", 0) or 0
        final = ep.get("final_score", 0) or 0
        key_insight = ep.get("key_insight", "")[:100] if ep.get("key_insight") else ""
        
        lines.append(
            f"{i}. {title}\n"
            f"   Series: {series} | Credibility:{cred} | Insight:{insight} | "
            f"Similarity:{sim:.3f} | Final:{final:.3f}\n"
            f"   Key insight: {key_insight}..."
        )
    
    return "\n".join(lines)


def parse_json_response(content: str) -> Optional[Dict]:
    """Parse JSON from LLM response, handling various formats."""
    # Try direct JSON parse first
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find any JSON object
    json_match = re.search(r'\{[\s\S]*\}', content)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    return None


# ============================================================================
# LLM Evaluation
# ============================================================================

def evaluate_with_llm(
    profile: Dict,
    response: Dict,
    test_case: Dict,
    model: str = DEFAULT_MODEL,
    api_key: str = None
) -> Dict:
    """
    Evaluate recommendations using Gemini as judge.
    
    Args:
        profile: User profile dict
        response: API response with episodes
        test_case: Test case being evaluated
        model: Gemini model to use
        api_key: Optional API key (uses default if not provided)
    
    Returns:
        Evaluation result dict
    """
    if not HAS_GEMINI:
        return {
            "error": "google-generativeai package not installed. Run: pip install google-generativeai",
            "relevance_score": None,
            "diversity_score": None,
            "quality_score": None,
            "test_pass": None,
            "rationale": None
        }
    
    # Get API key from argument, environment, or .env file
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return {
            "error": "GEMINI_API_KEY not set and no default available",
            "relevance_score": None,
            "diversity_score": None,
            "quality_score": None,
            "test_pass": None,
            "rationale": None
        }
    
    # Configure Gemini
    genai.configure(api_key=key)
    
    # Build prompt
    prompt = EVALUATION_PROMPT.format(
        profile_summary=format_profile_summary(profile),
        engagements_summary=format_engagements_summary(profile.get("engagements", [])),
        recommendations_summary=format_recommendations_summary(response.get("episodes", [])),
        test_description=f"{test_case.get('name', 'Unknown')}: {test_case.get('description', '')}"
    )
    
    try:
        # Create model with configuration
        generation_config = genai.GenerationConfig(
            temperature=0.0,  # Deterministic for evaluation
            max_output_tokens=MAX_OUTPUT_TOKENS,
            response_mime_type="application/json"  # Request JSON response
        )
        
        gemini_model = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config
        )
        
        # Generate response
        gemini_response = gemini_model.generate_content(prompt)
        
        # Get text content
        content = gemini_response.text
        
        # Parse JSON from response
        result = parse_json_response(content)
        if result:
            result["raw_response"] = content
            result["model"] = model
            return result
        else:
            return {
                "error": "Could not parse JSON from LLM response",
                "raw_response": content,
                "model": model
            }
    
    except Exception as e:
        return {
            "error": str(e),
            "relevance_score": None,
            "diversity_score": None,
            "quality_score": None,
            "test_pass": None,
            "rationale": None
        }


def evaluate_recommendations(
    profile: Dict,
    response: Dict,
    test_case: Dict,
    use_llm: bool = True
) -> Dict:
    """
    Evaluate recommendations (with or without LLM).
    
    Args:
        profile: User profile dict
        response: API response with episodes
        test_case: Test case being evaluated
        use_llm: Whether to use LLM evaluation
    
    Returns:
        Evaluation result dict
    """
    # Basic metrics (always computed)
    from metrics import compute_all_metrics
    metrics = compute_all_metrics(response)
    
    result = {
        "profile_id": profile.get("profile_id", "unknown"),
        "test_id": test_case.get("test_id", "unknown"),
        "metrics": metrics
    }
    
    # LLM evaluation (optional)
    if use_llm:
        llm_result = evaluate_with_llm(profile, response, test_case)
        result["llm_evaluation"] = llm_result
    
    return result


# ============================================================================
# Batch Evaluation
# ============================================================================

def evaluate_all_profiles(
    profiles: Dict[str, Dict],
    responses: Dict[str, Dict],
    test_case: Dict,
    use_llm: bool = True
) -> List[Dict]:
    """
    Evaluate all profiles against a test case.
    
    Args:
        profiles: Dict of profile_id -> profile
        responses: Dict of profile_id -> API response
        test_case: Test case being evaluated
        use_llm: Whether to use LLM evaluation
    
    Returns:
        List of evaluation results
    """
    results = []
    
    for profile_id, profile in profiles.items():
        response = responses.get(profile_id, {})
        result = evaluate_recommendations(profile, response, test_case, use_llm)
        results.append(result)
        print(f"  Evaluated: {profile_id}")
    
    return results


def run_full_evaluation(use_llm: bool = True) -> Dict:
    """
    Run full evaluation across all profiles and test cases.
    
    Returns:
        Complete evaluation report
    """
    import requests
    from pathlib import Path
    from datetime import datetime
    
    PROFILES_DIR = Path(__file__).parent / "profiles"
    TEST_CASES_DIR = Path(__file__).parent / "test_cases"
    API_URL = "http://localhost:8000"
    
    # Load all profiles
    profiles = {}
    for path in PROFILES_DIR.glob("*.json"):
        with open(path) as f:
            profile = json.load(f)
            profiles[profile["profile_id"]] = profile
    
    # Load all test cases
    test_cases = {}
    for path in TEST_CASES_DIR.glob("*.json"):
        with open(path) as f:
            test_case = json.load(f)
            test_cases[test_case["test_id"]] = test_case
    
    # Get API responses for all profiles
    responses = {}
    for profile_id, profile in profiles.items():
        engagements = [
            {
                "episode_id": e["episode_id"],
                "type": e.get("type", "click"),
                "timestamp": e.get("timestamp", "")
            }
            for e in profile.get("engagements", [])
        ]
        
        resp = requests.post(
            f"{API_URL}/api/sessions/create",
            json={"engagements": engagements, "excluded_ids": profile.get("excluded_ids", [])}
        )
        
        if resp.ok:
            responses[profile_id] = resp.json()
        else:
            print(f"Warning: API error for {profile_id}: {resp.status_code}")
            responses[profile_id] = {}
    
    # Evaluate each profile with each relevant test case
    report = {
        "timestamp": datetime.now().isoformat(),
        "profiles_count": len(profiles),
        "test_cases_count": len(test_cases),
        "evaluations": []
    }
    
    for test_id, test_case in test_cases.items():
        print(f"\nEvaluating test: {test_case['name']}")
        
        # Get profiles for this test
        test_profiles = test_case.get("profiles", list(profiles.keys()))
        
        for profile_id in test_profiles:
            if profile_id in profiles and profile_id in responses:
                result = evaluate_recommendations(
                    profiles[profile_id],
                    responses[profile_id],
                    test_case,
                    use_llm=use_llm
                )
                report["evaluations"].append(result)
                
                if use_llm and "llm_evaluation" in result:
                    llm = result["llm_evaluation"]
                    if "error" not in llm:
                        print(f"  {profile_id}: relevance={llm.get('relevance_score')}, "
                              f"quality={llm.get('quality_score')}, pass={llm.get('test_pass')}")
                    else:
                        print(f"  {profile_id}: ERROR - {llm.get('error')}")
    
    return report


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import argparse
    import requests
    from pathlib import Path
    
    parser = argparse.ArgumentParser(description="LLM evaluation of recommendations")
    parser.add_argument("--profile", type=str, default="02_vc_partner_ai_tech", help="Profile to evaluate")
    parser.add_argument("--test", type=str, default="01_cold_start_quality", help="Test case")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM evaluation")
    parser.add_argument("--all", action="store_true", help="Run full evaluation on all profiles")
    args = parser.parse_args()
    
    if args.all:
        # Run full evaluation
        print("Running full LLM evaluation...")
        report = run_full_evaluation(use_llm=not args.no_llm)
        
        # Save report
        reports_dir = Path(__file__).parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        from datetime import datetime
        report_path = reports_dir / f"llm_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved: {report_path}")
    else:
        # Single profile evaluation
        print(f"Evaluating profile: {args.profile}")
        print(f"Test case: {args.test}")
        print(f"Using LLM: {not args.no_llm}")
        print("-" * 50)
        
        # Load profile
        profile_path = Path(__file__).parent / "profiles" / f"{args.profile}.json"
        with open(profile_path) as f:
            profile = json.load(f)
        
        # Load test case
        test_path = Path(__file__).parent / "test_cases" / f"{args.test}.json"
        with open(test_path) as f:
            test_case = json.load(f)
        
        # Call API
        engagements = [
            {
                "episode_id": e["episode_id"],
                "type": e.get("type", "click"),
                "timestamp": e.get("timestamp", "")
            }
            for e in profile.get("engagements", [])
        ]
        
        response = requests.post(
            "http://localhost:8000/api/sessions/create",
            json={"engagements": engagements, "excluded_ids": profile.get("excluded_ids", [])}
        )
        
        if response.ok:
            result = evaluate_recommendations(
                profile,
                response.json(),
                test_case,
                use_llm=not args.no_llm
            )
            print(json.dumps(result, indent=2))
        else:
            print(f"API error: {response.status_code}")
