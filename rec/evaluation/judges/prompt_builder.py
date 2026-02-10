"""
Prompt Builder for LLM Criteria Evaluation

Constructs prompts from criterion definitions by substituting placeholders
with formatted context (profile, engagements, recommendations, test info).

Usage:
    from evaluation.judges.prompt_builder import build_criterion_prompt
    
    prompt = build_criterion_prompt(
        criterion=criterion_def,
        profile=user_profile,
        response=api_response,
        test_case=test_case
    )
"""

from typing import Any, Dict, List, Optional


# ============================================================================
# Placeholder Formatters
# ============================================================================

def format_profile_summary(profile: Dict[str, Any]) -> str:
    """
    Format profile for LLM prompt.
    
    Args:
        profile: User profile dict with name, icp_segment, description, etc.
    
    Returns:
        Formatted profile summary string
    """
    if not profile:
        return "No profile provided (cold start user)"
    
    total_engagements = len(profile.get("engagements", []))
    stats = profile.get("stats", {})
    if stats:
        total_engagements = stats.get("total_engagements", total_engagements)
    
    # Extract base description without Content Hypothesis (that goes separately)
    full_desc = profile.get('description', '')
    base_desc = full_desc.split('Content Hypothesis:')[0].strip()
    
    return f"""Name: {profile.get('name', 'Unknown')}
ICP Segment: {profile.get('icp_segment', 'Unknown')}
Duration: {profile.get('usage_duration', 'Unknown')}
Total Engagements: {total_engagements}
Description: {base_desc}"""


def format_content_hypothesis(profile: Dict[str, Any]) -> str:
    """
    Extract Content Hypothesis from profile description.
    
    The Content Hypothesis describes:
    - Exploration vs. Specialization ratio
    - Cross-Disciplinary Curiosity level
    - Format preferences (if any)
    - Specific interest areas and boundaries
    
    Args:
        profile: User profile dict
    
    Returns:
        Content Hypothesis text for LLM evaluation
    """
    if not profile:
        return """Unknown user - first-time visitor with no engagement history.
Algorithm should maximize initial diversity to probe user interests across major themes.
First impression should showcase breadth of high-quality content."""
    
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


def format_engagements_summary(profile: Dict[str, Any]) -> str:
    """
    Format engagements for LLM prompt.
    
    Args:
        profile: User profile with engagements list
    
    Returns:
        Formatted engagements summary (last 10)
    """
    engagements = profile.get("engagements", []) if profile else []
    
    if not engagements:
        return "No engagements (cold start user)"
    
    lines = []
    for eng in engagements[-10:]:  # Last 10
        eng_type = eng.get("type", "click")
        title = eng.get("title", eng.get("episode_id", "Unknown"))
        series = eng.get("series", "Unknown")
        lines.append(f"- [{eng_type.upper()}] {title} ({series})")
    
    return "\n".join(lines)


def format_recommendations_summary(response: Dict[str, Any], top_n: int = 10) -> str:
    """
    Format recommendations for LLM prompt.
    
    Args:
        response: API response with episodes list
        top_n: Number of episodes to include
    
    Returns:
        Formatted recommendations summary
    """
    episodes = response.get("episodes", [])[:top_n]
    
    if not episodes:
        return "No recommendations returned"
    
    lines = []
    for i, ep in enumerate(episodes, 1):
        title = ep.get("title", "Unknown")
        series = ep.get("series", {})
        series_name = series.get("name", "Unknown") if isinstance(series, dict) else str(series)
        
        scores = ep.get("scores", {})
        cred = scores.get("credibility", 0)
        insight = scores.get("insight", 0)
        
        sim = ep.get("similarity_score", 0) or 0
        final = ep.get("final_score", 0) or 0
        quality = ep.get("quality_score", 0) or 0
        
        key_insight = ep.get("key_insight", "")
        key_insight_preview = key_insight[:100] + "..." if key_insight and len(key_insight) > 100 else key_insight or ""
        
        lines.append(
            f"{i}. {title}\n"
            f"   Series: {series_name} | Credibility:{cred} | Insight:{insight} | "
            f"Quality:{quality:.2f} | Similarity:{sim:.3f} | Final:{final:.3f}\n"
            f"   Key insight: {key_insight_preview}"
        )
    
    return "\n".join(lines)


def format_test_description(test_case: Dict[str, Any]) -> str:
    """
    Format test case description for LLM prompt.
    
    Args:
        test_case: Test case dict with name, description, etc.
    
    Returns:
        Formatted test description
    """
    if not test_case:
        return "No test case context provided"
    
    name = test_case.get("name", "Unknown Test")
    description = test_case.get("description", "")
    
    # Include LLM prompt hint if available
    llm_criteria = test_case.get("llm_criteria", {})
    prompt_hint = llm_criteria.get("prompt_hint", "")
    
    result = f"{name}: {description}"
    
    if prompt_hint:
        result += f"\n\nEvaluation Focus: {prompt_hint}"
    
    return result


# ============================================================================
# Main Prompt Builder
# ============================================================================

def build_criterion_prompt(
    criterion: Dict[str, Any],
    profile: Optional[Dict[str, Any]],
    response: Dict[str, Any],
    test_case: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build complete prompt from criterion definition.
    
    Substitutes placeholders in the criterion's prompt_template:
    - {profile_summary} - Formatted user profile
    - {content_hypothesis} - User's content hypothesis
    - {engagements_summary} - Recent engagements
    - {recommendations_summary} - Top N recommendations
    - {test_description} - Test case context
    
    Args:
        criterion: Criterion definition dict (from definition.json)
        profile: User profile dict (can be None for cold start)
        response: API response with recommendations
        test_case: Test case being evaluated (optional)
    
    Returns:
        Complete prompt string ready for LLM
    """
    template = criterion.get("prompt_template", "")
    
    if not template:
        raise ValueError(f"Criterion '{criterion.get('id', 'unknown')}' has no prompt_template")
    
    # Build substitution context
    context = {
        "profile_summary": format_profile_summary(profile),
        "content_hypothesis": format_content_hypothesis(profile),
        "engagements_summary": format_engagements_summary(profile),
        "recommendations_summary": format_recommendations_summary(response),
        "test_description": format_test_description(test_case)
    }
    
    # Substitute placeholders
    prompt = template
    for key, value in context.items():
        placeholder = "{" + key + "}"
        if placeholder in prompt:
            prompt = prompt.replace(placeholder, value)
    
    return prompt


def build_batch_prompts(
    criteria: List[Dict[str, Any]],
    profile: Optional[Dict[str, Any]],
    response: Dict[str, Any],
    test_case: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """
    Build prompts for multiple criteria.
    
    Args:
        criteria: List of criterion definitions
        profile: User profile dict
        response: API response
        test_case: Test case being evaluated
    
    Returns:
        Dict mapping criterion_id -> prompt
    """
    prompts = {}
    
    for criterion in criteria:
        criterion_id = criterion.get("id", "unknown")
        try:
            prompts[criterion_id] = build_criterion_prompt(
                criterion, profile, response, test_case
            )
        except ValueError as e:
            # Skip criteria without templates (likely deterministic)
            prompts[criterion_id] = None
    
    return prompts


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "build_criterion_prompt",
    "build_batch_prompts",
    "format_profile_summary",
    "format_content_hypothesis",
    "format_engagements_summary",
    "format_recommendations_summary",
    "format_test_description"
]
