"""
Two-Stage Aggregation for Multi-LLM Consensus

Implements research-backed aggregation strategy:
1. Within-model aggregation: Mean of N samples from same model
2. Cross-model aggregation: Mean of model means for final score

Also reports uncertainty metrics:
- Standard deviation within each model
- Standard deviation across models
- Consensus level (STRONG/GOOD/PARTIAL/LOW)
- Flag for human review when consensus is low

Usage:
    from evaluation.judges.aggregator import aggregate_within_model, aggregate_across_models
    
    # Stage 1: Aggregate samples from one model
    model_result = aggregate_within_model("relevance", samples)
    
    # Stage 2: Aggregate across all models
    final_result = aggregate_across_models(criterion, model_results, test_case, config)
"""

import math
from typing import Any, Dict, List, Optional


# ============================================================================
# Statistical Helpers
# ============================================================================

def compute_mean(values: List[float]) -> float:
    """Compute arithmetic mean."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def compute_std(values: List[float]) -> float:
    """Compute population standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = compute_mean(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return math.sqrt(variance)


# ============================================================================
# Consensus Classification
# ============================================================================

def categorize_consensus(std: float) -> str:
    """
    Categorize consensus based on cross-model standard deviation.
    
    Based on research showing that std < 0.5 indicates strong agreement,
    while std > 1.5 indicates significant disagreement requiring review.
    
    Args:
        std: Standard deviation across model means
    
    Returns:
        Consensus level: STRONG, GOOD, PARTIAL, or LOW
    """
    if std < 0.5:
        return "STRONG"
    elif std < 1.0:
        return "GOOD"
    elif std < 1.5:
        return "PARTIAL"
    else:
        return "LOW"


# ============================================================================
# Threshold Resolution
# ============================================================================

def get_threshold(
    criterion: Dict[str, Any],
    test_case: Optional[Dict[str, Any]] = None
) -> float:
    """
    Get threshold from test case criteria list or criterion default.
    
    Priority:
    1. Test case criterion override
    2. Criterion default_threshold
    3. Fallback to 6.0
    
    Args:
        criterion: Criterion definition
        test_case: Test case (may have criterion overrides)
    
    Returns:
        Threshold value
    """
    criterion_id = criterion.get("id")
    
    # Look for override in test case
    if test_case:
        for tc_criterion in test_case.get("criteria", []):
            if tc_criterion.get("id") == criterion_id:
                if "threshold" in tc_criterion:
                    return tc_criterion["threshold"]
    
    # Fall back to criterion default
    scoring = criterion.get("scoring", {})
    return scoring.get("default_threshold", 6.0)


# ============================================================================
# Stage 1: Within-Model Aggregation
# ============================================================================

def aggregate_within_model(
    criterion_id: str,
    samples: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Aggregate N samples from the same model.
    
    Computes mean score and standard deviation to measure
    within-model consistency.
    
    Args:
        criterion_id: The criterion being evaluated
        samples: List of LLM responses (each with "score" and "reasoning")
    
    Returns:
        Aggregated result with:
        - samples: Raw scores
        - mean_score: Mean of samples
        - std: Within-model standard deviation
        - n: Number of valid samples
        - reasoning_samples: All reasoning texts
    """
    if not samples:
        return {
            "samples": [],
            "mean_score": 0.0,
            "std": 0.0,
            "n": 0,
            "reasoning_samples": [],
            "error": "No valid samples"
        }
    
    # Extract scores (handle missing gracefully)
    scores = []
    reasoning_samples = []
    
    for s in samples:
        score = s.get("score")
        if score is not None:
            try:
                scores.append(float(score))
            except (TypeError, ValueError):
                pass
        reasoning = s.get("reasoning", "")
        if reasoning:
            reasoning_samples.append(reasoning)
    
    if not scores:
        return {
            "samples": [],
            "mean_score": 0.0,
            "std": 0.0,
            "n": 0,
            "reasoning_samples": reasoning_samples,
            "error": "No valid scores in samples"
        }
    
    return {
        "samples": scores,
        "mean_score": round(compute_mean(scores), 2),
        "std": round(compute_std(scores), 2),
        "n": len(scores),
        "reasoning_samples": reasoning_samples
    }


# ============================================================================
# Stage 2: Cross-Model Aggregation
# ============================================================================

def aggregate_across_models(
    criterion: Dict[str, Any],
    model_results: Dict[str, Dict[str, Any]],
    test_case: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Aggregate across all models for final consensus score.
    
    Takes the mean of each model's mean score, then computes
    cross-model statistics for uncertainty reporting.
    
    Args:
        criterion: Criterion definition
        model_results: Dict of provider -> within-model aggregation
        test_case: Test case (for threshold lookup)
        config: Judge configuration (for consensus settings)
    
    Returns:
        Final criterion result with:
        - criterion_id: Criterion identifier
        - criterion_type: "llm"
        - model_results: Per-model breakdown
        - final_score: Cross-model mean
        - cross_model_std: Standard deviation across models
        - consensus_level: STRONG/GOOD/PARTIAL/LOW
        - threshold: Pass threshold used
        - passed: Whether final_score >= threshold
        - flag_for_review: True if low consensus
    """
    criterion_id = criterion.get("id", "unknown")
    
    if not model_results:
        return {
            "criterion_id": criterion_id,
            "criterion_type": "llm",
            "error": "No model results to aggregate",
            "passed": False
        }
    
    # Get config settings
    if config is None:
        config = {}
    consensus_threshold = config.get("consensus_threshold", 1.5)
    flag_low_consensus = config.get("flag_low_consensus", True)
    report_uncertainty = config.get("report_uncertainty", True)
    
    # Extract model means
    model_scores = []
    for provider, result in model_results.items():
        mean_score = result.get("mean_score")
        if mean_score is not None:
            model_scores.append(mean_score)
    
    if not model_scores:
        return {
            "criterion_id": criterion_id,
            "criterion_type": "llm",
            "model_results": model_results,
            "error": "No valid scores from any model",
            "passed": False
        }
    
    # Compute cross-model statistics
    final_score = round(compute_mean(model_scores), 2)
    cross_model_std = round(compute_std(model_scores), 2)
    consensus_level = categorize_consensus(cross_model_std)
    
    # Get threshold
    threshold = get_threshold(criterion, test_case)
    
    # Determine pass/fail
    passed = final_score >= threshold
    
    # Flag for review if low consensus
    flag_for_review = flag_low_consensus and cross_model_std > consensus_threshold
    
    # Build result
    result = {
        "criterion_id": criterion_id,
        "criterion_type": "llm",
        "model_results": model_results,
        "final_score": final_score,
        "threshold": threshold,
        "passed": passed
    }
    
    # Add uncertainty metrics if configured
    if report_uncertainty:
        result["cross_model_std"] = cross_model_std
        result["consensus_level"] = consensus_level
        result["flag_for_review"] = flag_for_review
        result["n_models"] = len(model_scores)
    
    # Collect representative reasoning
    all_reasoning = []
    for provider, model_result in model_results.items():
        reasoning_samples = model_result.get("reasoning_samples", [])
        if reasoning_samples:
            # Take first reasoning from each model
            all_reasoning.append(f"[{provider}] {reasoning_samples[0]}")
    
    if all_reasoning:
        result["reasoning_summary"] = all_reasoning
    
    return result


# ============================================================================
# Utility Functions
# ============================================================================

def summarize_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Summarize a list of criterion results.
    
    Args:
        results: List of criterion evaluation results
    
    Returns:
        Summary with pass/fail counts, overall score, flags
    """
    if not results:
        return {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "overall_score": 0.0,
            "flagged_for_review": []
        }
    
    passed = 0
    failed = 0
    errors = 0
    scores = []
    flagged = []
    
    for r in results:
        if r.get("error"):
            errors += 1
        elif r.get("passed"):
            passed += 1
        else:
            failed += 1
        
        score = r.get("final_score") or r.get("score")
        if score is not None:
            scores.append(score)
        
        if r.get("flag_for_review"):
            flagged.append(r.get("criterion_id"))
    
    overall_score = round(compute_mean(scores), 2) if scores else 0.0
    
    return {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "overall_score": overall_score,
        "flagged_for_review": flagged,
        "all_passed": failed == 0 and errors == 0
    }


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "aggregate_within_model",
    "aggregate_across_models",
    "categorize_consensus",
    "get_threshold",
    "summarize_results",
    "compute_mean",
    "compute_std"
]
