"""
Multi-LLM Judge Infrastructure

This package provides a scalable, modular multi-LLM judging system for evaluating
recommendation quality. Key features:

- LiteLLM unified interface for OpenAI, Gemini, Anthropic
- Per-criterion LLM calls (maximum modularity, better debugging)
- Two-stage aggregation (within-model mean → cross-model mean)
- Configurable N samples per judge (default: 3, adjustable via UI)
- Temperature 0.8 (research-backed for better calibration)
- Graceful degradation if one LLM provider fails
- Consensus metrics and uncertainty reporting

Usage:
    from evaluation.judges import evaluate_test_case, evaluate_criterion
    
    # Evaluate all criteria for a test case
    results = await evaluate_all_criteria(
        criteria=criteria_list,
        profile=user_profile,
        response=api_response,
        test_case=test_case
    )
    
    # Evaluate a single criterion
    result = await evaluate_criterion(
        criterion=criterion_def,
        profile=user_profile,
        response=api_response,
        test_case=test_case
    )

Modules:
    client.py         - LiteLLM async wrapper for multi-provider support
    orchestrator.py   - Multi-LLM coordination and parallel execution
    aggregator.py     - Two-stage aggregation logic
    prompt_builder.py - Dynamic prompt construction from criterion definitions
    config.json       - Externalized judge settings (N, temperature, enabled providers)

Design Principles:
    1. LLM is Core: No optional flags. LLM evaluation always runs.
    2. Per-Criterion Calls: Each criterion gets its own API call for modularity.
    3. Two Criterion Types: Deterministic (Python) and LLM (prompt-based).
    4. Scalability: Add new criteria/tests/LLM providers without code changes.
"""

__version__ = "1.0.0"

# Import main functions for convenient access
from .orchestrator import (
    evaluate_criterion,
    evaluate_all_criteria,
    load_judge_config,
    get_enabled_judges,
)

from .aggregator import (
    aggregate_within_model,
    aggregate_across_models,
    summarize_results,
    categorize_consensus,
)

from .client import (
    call_llm,
    call_llm_batch,
    get_available_providers,
    is_provider_available,
    SUPPORTED_MODELS,
)

from .prompt_builder import (
    build_criterion_prompt,
    build_batch_prompts,
)

__all__ = [
    # Orchestration
    "evaluate_criterion",
    "evaluate_all_criteria",
    "load_judge_config",
    "get_enabled_judges",
    
    # Aggregation
    "aggregate_within_model",
    "aggregate_across_models",
    "summarize_results",
    "categorize_consensus",
    
    # LLM Client
    "call_llm",
    "call_llm_batch",
    "get_available_providers",
    "is_provider_available",
    "SUPPORTED_MODELS",
    
    # Prompt Building
    "build_criterion_prompt",
    "build_batch_prompts",
]
