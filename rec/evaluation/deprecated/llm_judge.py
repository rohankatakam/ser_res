#!/usr/bin/env python3
"""
DEPRECATED: Single-LLM Judge for Recommendation Evaluation

==============================================================================
DEPRECATION NOTICE (2026-02-09)
==============================================================================

This module has been superseded by the multi-LLM judge infrastructure:

    evaluation/judges/     - Multi-LLM orchestration package
    evaluation/criteria/   - Modular criterion definitions

Key improvements in the new system:
- Multi-provider support (OpenAI, Gemini, Anthropic) via LiteLLM
- Per-criterion LLM calls for maximum modularity
- Two-stage aggregation (within-model, then cross-model)
- Configurable N samples per judge (default: 3)
- Temperature 0.8 (research-backed for better calibration)
- Consensus metrics and uncertainty reporting
- Graceful degradation if one provider fails

Migration:
    # Old usage:
    from llm_judge import evaluate_with_llm
    result = evaluate_with_llm(profile, response, test_case)
    
    # New usage:
    from judges import evaluate_all_criteria, load_judge_config
    from criteria import get_criteria_for_test
    
    criteria = get_criteria_for_test(test_case)
    config = load_judge_config()
    results = await evaluate_all_criteria(criteria, profile, response, test_case, config)

This file is kept for reference only. Do not use in new code.
==============================================================================

Original description:
Uses Gemini to evaluate recommendation quality with structured rubrics.

Usage:
    from llm_judge import evaluate_recommendations
    result = evaluate_recommendations(profile, recommendations, test_case)

    # CLI usage:
    python llm_judge.py --profile 02_vc_partner_ai_tech --test 01_cold_start_quality

Note: Requires GEMINI_API_KEY environment variable (or uses default).
"""

import warnings

# Emit deprecation warning when imported
warnings.warn(
    "llm_judge is deprecated. Use the judges/ package instead. "
    "See evaluation/deprecated/llm_judge.py for migration guide.",
    DeprecationWarning,
    stacklevel=2
)

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
    env_path = Path(__file__).parent.parent / ".env"
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

EVALUATION_PROMPT = """You are evaluating a podcast recommendation system for investors using a profile-aware methodology based on 2026 best practices (Spotify/Netflix research).

## User Profile
{profile_summary}

## Content Hypothesis
{content_hypothesis}

## Recent Engagements
{engagements_summary}

## For You Feed (Top 10 Recommendations)
{recommendations_summary}

## Test Case Being Evaluated
{test_description}

## Evaluation Criteria

Evaluate recommendations using the user's Content Hypothesis as your primary lens:

1. **RELEVANCE** (1-5): Do the recommendations match the user's content hypothesis?
   - Consider their Specialization vs. Exploration ratio
   - Consider their Cross-Disciplinary Curiosity level
   - 5: Recommendations perfectly match the content hypothesis (right balance of depth/breadth)
   - 3: Partially matches - some content aligns, some doesn't
   - 1: Recommendations conflict with the user's stated content preferences

2. **DIVERSITY** (1-5): Does the diversity level match what the Content Hypothesis prescribes?
   - For specialists (high specialization %): variety WITHIN their domain is good, scattered recommendations are bad
   - For explorers (high exploration %): cross-sector diversity is expected and good
   - 5: Diversity level perfectly matches the user's exploration/specialization ratio
   - 3: Some mismatch in diversity expectations
   - 1: Major mismatch (e.g., scattered content for a specialist, or narrow content for an explorer)

3. **QUALITY** (1-5): Are high-quality episodes (credibility ≥3) being surfaced?
   - 5: Top recommendations are all high-quality
   - 3: Mix of quality levels
   - 1: Low-quality content is prominent

4. **CONTENT_HYPOTHESIS_ALIGNMENT** (1-5): How well do recommendations align with the explicit Content Hypothesis?
   - Consider: Exploration/Specialization ratio, Cross-Disciplinary Curiosity, any stated format preferences
   - 5: Recommendations demonstrate clear understanding of the user's content preferences
   - 3: Partial alignment with room for improvement
   - 1: Recommendations seem to ignore the Content Hypothesis entirely

5. **TEST_PASS** (true/false): Does this specific test case pass?
   - Evaluate based on the test description provided

6. **RATIONALE**: Explain your evaluation in 2-3 sentences, specifically referencing how the recommendations align (or don't) with the Content Hypothesis.

## Response Format

You MUST respond with ONLY valid JSON, no markdown code blocks, no additional text:
{{
  "relevance_score": <1-5>,
  "diversity_score": <1-5>,
  "quality_score": <1-5>,
  "content_hypothesis_alignment": <1-5>,
  "test_pass": <true or false>,
  "rationale": "<explanation referencing content hypothesis>"
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
    
    # Extract base description without Content Hypothesis
    full_desc = profile.get('description', '')
    base_desc = full_desc.split('Content Hypothesis:')[0].strip()
    
    return f"""
Name: {profile.get('name', 'Unknown')}
ICP Segment: {profile.get('icp_segment', 'Unknown')}
Duration: {profile.get('usage_duration', 'Unknown')}
Total Engagements: {total_engagements}
Description: {base_desc}
"""


def extract_content_hypothesis(profile: Dict) -> str:
    """
    Extract Content Hypothesis from profile description.
    
    The Content Hypothesis describes:
    - Exploration vs. Specialization ratio (e.g., "85% Specialization")
    - Cross-Disciplinary Curiosity level (Low/Moderate/High)
    - Format preferences (if any)
    - Specific interest areas and boundaries
    
    Args:
        profile: User profile dict
    
    Returns:
        Content Hypothesis text for LLM evaluation
    """
    description = profile.get('description', '')
    
    # Try to extract Content Hypothesis section if it exists
    if 'Content Hypothesis:' in description:
        hypothesis_part = description.split('Content Hypothesis:')[1].strip()
        return hypothesis_part
    
    # For cold start or profiles without explicit hypothesis
    if not profile.get('engagements'):
        return """Unknown specialization—first-time user with no engagement history.
Algorithm should maximize initial diversity to probe user interests across major themes.
First impression should showcase breadth of high-quality content."""
    
    # Generate basic hypothesis from expected_behavior if no explicit one
    expected = profile.get('expected_behavior', [])
    if expected:
        return f"""Inferred from expected behavior:
{chr(10).join('- ' + str(b) for b in expected[:5])}"""
    
    return "No explicit Content Hypothesis available. Evaluate based on engagement patterns."


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
    DEPRECATED: Use judges.evaluate_all_criteria() instead.
    
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
    warnings.warn(
        "evaluate_with_llm() is deprecated. Use judges.evaluate_all_criteria() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    if not HAS_GEMINI:
        return {
            "error": "google-generativeai package not installed. Run: pip install google-generativeai",
            "relevance_score": None,
            "diversity_score": None,
            "quality_score": None,
            "content_hypothesis_alignment": None,
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
            "content_hypothesis_alignment": None,
            "test_pass": None,
            "rationale": None
        }
    
    # Configure Gemini
    genai.configure(api_key=key)
    
    # Build prompt with Content Hypothesis
    prompt = EVALUATION_PROMPT.format(
        profile_summary=format_profile_summary(profile),
        content_hypothesis=extract_content_hypothesis(profile),
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
            "content_hypothesis_alignment": None,
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
    DEPRECATED: Use judges.evaluate_all_criteria() instead.
    
    Evaluate recommendations (with or without LLM).
    
    Args:
        profile: User profile dict
        response: API response with episodes
        test_case: Test case being evaluated
        use_llm: Whether to use LLM evaluation
    
    Returns:
        Evaluation result dict
    """
    warnings.warn(
        "evaluate_recommendations() is deprecated. Use judges.evaluate_all_criteria() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    result = {
        "profile_id": profile.get("profile_id", "unknown"),
        "test_id": test_case.get("test_id", "unknown")
    }
    
    # LLM evaluation (optional)
    if use_llm:
        llm_result = evaluate_with_llm(profile, response, test_case)
        result["llm_evaluation"] = llm_result
    
    return result
