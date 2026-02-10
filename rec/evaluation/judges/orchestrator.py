"""
Multi-LLM Orchestrator

Coordinates multi-LLM evaluation with parallel execution. For each LLM criterion,
runs N samples across all enabled providers. For deterministic criteria, executes
the Python function directly.

Usage:
    from evaluation.judges.orchestrator import evaluate_criterion, evaluate_all_criteria
    
    # Single criterion
    result = await evaluate_criterion(
        criterion=criterion_def,
        profile=user_profile,
        response=api_response,
        test_case=test_case,
        config=judge_config
    )
    
    # All criteria for a test
    results = await evaluate_all_criteria(
        criteria=criteria_list,
        profile=user_profile,
        response=api_response,
        test_case=test_case,
        config=judge_config
    )
"""

import asyncio
import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .client import call_llm, get_available_providers, is_provider_available
from .prompt_builder import build_criterion_prompt


# ============================================================================
# Configuration Loading
# ============================================================================

def load_judge_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load judge configuration from config.json.
    
    Args:
        config_path: Path to config.json (defaults to judges/config.json)
    
    Returns:
        Configuration dict
    """
    if config_path is None:
        config_path = Path(__file__).parent / "config.json"
    
    if not config_path.exists():
        # Return defaults if config doesn't exist
        return {
            "judges": [
                {"provider": "openai", "enabled": True},
                {"provider": "gemini", "enabled": True},
                {"provider": "anthropic", "enabled": False}
            ],
            "default_n": 3,
            "temperature": 0.8,
            "consensus_threshold": 1.5,
            "flag_low_consensus": True,
            "report_uncertainty": True
        }
    
    with open(config_path) as f:
        return json.load(f)


def get_enabled_judges(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get list of enabled judges that have valid API keys.
    
    Args:
        config: Judge configuration
    
    Returns:
        List of enabled judge configs with available API keys
    """
    enabled = []
    for judge in config.get("judges", []):
        if judge.get("enabled", False):
            provider = judge.get("provider")
            if is_provider_available(provider):
                enabled.append(judge)
    return enabled


# ============================================================================
# Deterministic Criterion Execution
# ============================================================================

def load_deterministic_function(criterion: Dict[str, Any]) -> callable:
    """
    Load the Python function for a deterministic criterion.
    
    Args:
        criterion: Criterion definition with 'function' field
    
    Returns:
        Callable function from logic.py
    """
    criterion_id = criterion.get("id")
    function_name = criterion.get("function")
    
    if not function_name:
        raise ValueError(f"Deterministic criterion '{criterion_id}' missing 'function' field")
    
    # Find the logic.py file
    criteria_dir = Path(__file__).parent.parent / "criteria" / criterion_id
    logic_path = criteria_dir / "logic.py"
    
    if not logic_path.exists():
        raise FileNotFoundError(f"logic.py not found for criterion '{criterion_id}' at {logic_path}")
    
    # Load the module dynamically
    spec = importlib.util.spec_from_file_location(f"criteria.{criterion_id}.logic", logic_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Get the function
    if not hasattr(module, function_name):
        raise AttributeError(f"Function '{function_name}' not found in {logic_path}")
    
    return getattr(module, function_name)


def run_deterministic_criterion(
    criterion: Dict[str, Any],
    response: Dict[str, Any],
    test_case: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Execute a deterministic criterion.
    
    Args:
        criterion: Criterion definition
        response: API response with recommendations
        test_case: Test case (for threshold overrides)
    
    Returns:
        Criterion result dict
    """
    criterion_id = criterion.get("id")
    
    try:
        # Load and execute the function
        func = load_deterministic_function(criterion)
        
        # Build parameters (merge defaults with test case overrides)
        params = dict(criterion.get("parameters", {}))
        
        # Check for threshold override in test case
        if test_case:
            for tc_criterion in test_case.get("criteria", []):
                if tc_criterion.get("id") == criterion_id:
                    if "threshold" in tc_criterion:
                        params["threshold"] = tc_criterion["threshold"]
                    # Merge any additional params
                    params.update(tc_criterion.get("params", {}))
                    break
        
        # Use default threshold if not specified
        if "threshold" not in params:
            params["threshold"] = criterion.get("scoring", {}).get("default_threshold", 6.0)
        
        # Execute
        result = func(response, params)
        
        return {
            "criterion_id": criterion_id,
            "criterion_type": "deterministic",
            "score": result.get("score", 0),
            "passed": result.get("passed", False),
            "threshold": params.get("threshold"),
            "details": result.get("details", ""),
            "extra": {k: v for k, v in result.items() if k not in ("score", "passed", "details")}
        }
    
    except Exception as e:
        return {
            "criterion_id": criterion_id,
            "criterion_type": "deterministic",
            "error": str(e),
            "passed": False
        }


# ============================================================================
# LLM Criterion Execution
# ============================================================================

async def evaluate_llm_criterion(
    criterion: Dict[str, Any],
    profile: Optional[Dict[str, Any]],
    response: Dict[str, Any],
    test_case: Optional[Dict[str, Any]],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluate a single LLM criterion across all enabled judges.
    
    Runs N samples per judge in parallel, then aggregates results.
    
    Args:
        criterion: Criterion definition
        profile: User profile
        response: API response with recommendations
        test_case: Test case being evaluated
        config: Judge configuration
    
    Returns:
        Raw results from all judges (to be aggregated)
    """
    from .aggregator import aggregate_within_model, aggregate_across_models
    
    criterion_id = criterion.get("id")
    
    # Build prompt
    try:
        prompt = build_criterion_prompt(criterion, profile, response, test_case)
    except ValueError as e:
        return {
            "criterion_id": criterion_id,
            "criterion_type": "llm",
            "error": str(e),
            "passed": False
        }
    
    # Get enabled judges
    enabled_judges = get_enabled_judges(config)
    
    if not enabled_judges:
        available = get_available_providers()
        return {
            "criterion_id": criterion_id,
            "criterion_type": "llm",
            "error": f"No enabled judges with valid API keys. Available providers: {available}",
            "passed": False
        }
    
    temperature = config.get("temperature", 0.8)
    default_n = config.get("default_n", 3)
    response_schema = criterion.get("response_schema", {"score": "number", "reasoning": "string"})
    
    model_results = {}
    
    # Run each judge
    for judge in enabled_judges:
        provider = judge.get("provider")
        n_samples = judge.get("n", default_n)
        
        try:
            # Run N samples in parallel for this model
            tasks = [
                call_llm(provider, prompt, temperature, response_schema)
                for _ in range(n_samples)
            ]
            samples = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Separate successes and failures
            valid_samples = []
            errors = []
            for s in samples:
                if isinstance(s, Exception):
                    errors.append(str(s))
                else:
                    valid_samples.append(s)
            
            if valid_samples:
                model_results[provider] = aggregate_within_model(
                    criterion_id,
                    valid_samples
                )
                if errors:
                    model_results[provider]["partial_errors"] = errors
            else:
                model_results[provider] = {
                    "error": f"All {n_samples} samples failed",
                    "errors": errors,
                    "skipped": True
                }
        
        except Exception as e:
            model_results[provider] = {
                "error": str(e),
                "skipped": True
            }
    
    # Check if any model succeeded
    valid_results = {k: v for k, v in model_results.items() if not v.get("skipped")}
    
    if not valid_results:
        return {
            "criterion_id": criterion_id,
            "criterion_type": "llm",
            "error": "All judges failed",
            "model_results": model_results,
            "passed": False
        }
    
    # Aggregate across models
    return aggregate_across_models(criterion, valid_results, test_case, config)


# ============================================================================
# Main Orchestration
# ============================================================================

async def evaluate_criterion(
    criterion: Dict[str, Any],
    profile: Optional[Dict[str, Any]],
    response: Dict[str, Any],
    test_case: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluate a single criterion (LLM or deterministic).
    
    Args:
        criterion: Criterion definition
        profile: User profile
        response: API response
        test_case: Test case being evaluated
        config: Judge configuration (loads default if not provided)
    
    Returns:
        Criterion evaluation result
    """
    if config is None:
        config = load_judge_config()
    
    criterion_type = criterion.get("type", "llm")
    
    if criterion_type == "deterministic":
        return run_deterministic_criterion(criterion, response, test_case)
    else:
        return await evaluate_llm_criterion(criterion, profile, response, test_case, config)


async def evaluate_all_criteria(
    criteria: List[Dict[str, Any]],
    profile: Optional[Dict[str, Any]],
    response: Dict[str, Any],
    test_case: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Evaluate all criteria for a test case.
    
    Deterministic criteria are computed directly.
    LLM criteria are sent to multi-LLM judges in parallel.
    
    Args:
        criteria: List of criterion definitions
        profile: User profile
        response: API response
        test_case: Test case being evaluated
        config: Judge configuration
    
    Returns:
        List of criterion results
    """
    if config is None:
        config = load_judge_config()
    
    results = []
    llm_tasks = []
    llm_criteria_map = {}  # Track which task corresponds to which criterion
    
    for criterion in criteria:
        criterion_type = criterion.get("type", "llm")
        criterion_id = criterion.get("id")
        
        if criterion_type == "deterministic":
            # Run deterministic criterion directly
            result = run_deterministic_criterion(criterion, response, test_case)
            results.append(result)
        else:
            # Queue LLM criterion for parallel execution
            task = evaluate_llm_criterion(criterion, profile, response, test_case, config)
            llm_tasks.append(task)
            llm_criteria_map[len(llm_tasks) - 1] = criterion_id
    
    # Run all LLM criteria in parallel
    if llm_tasks:
        llm_results = await asyncio.gather(*llm_tasks, return_exceptions=True)
        for i, result in enumerate(llm_results):
            if isinstance(result, Exception):
                results.append({
                    "criterion_id": llm_criteria_map.get(i, "unknown"),
                    "criterion_type": "llm",
                    "error": str(result),
                    "passed": False
                })
            else:
                results.append(result)
    
    return results


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "evaluate_criterion",
    "evaluate_all_criteria",
    "load_judge_config",
    "get_enabled_judges",
    "run_deterministic_criterion",
    "evaluate_llm_criterion"
]
