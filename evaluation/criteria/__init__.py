"""
Modular Criterion Definitions - Registry

This package contains individual criterion definitions for evaluating
recommendation quality. The registry auto-discovers criteria from subfolders.

Each criterion is defined in its own folder with:
- definition.json  - Criterion metadata, scoring config, prompt template (for LLM)
- README.md        - Documentation for the criterion
- logic.py         - Python function (for deterministic criteria only)

Criterion Types:
    - LLM: Prompt-based evaluation using multi-LLM judges
    - Deterministic: Python functions for computed metrics

Usage:
    from evaluation.criteria import get_criterion, get_all_criteria, get_criteria_for_test
    
    # Load a specific criterion
    relevance = get_criterion("relevance")
    
    # Get all registered criteria
    all_criteria = get_all_criteria()
    
    # Get criteria for a test case
    test_criteria = get_criteria_for_test(test_case)
"""

import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import (
    CriterionDefinition,
    CriterionType,
    DeterministicCriterion,
    LLMCriterion,
    parse_criterion,
)

__version__ = "1.0.0"

# ============================================================================
# Registry State
# ============================================================================

_CRITERIA_DIR = Path(__file__).parent
_registry: Dict[str, Dict[str, Any]] = {}
_initialized = False


# ============================================================================
# Discovery and Loading
# ============================================================================

def _discover_criteria() -> List[str]:
    """
    Discover all criterion folders in the criteria directory.
    
    A valid criterion folder contains a definition.json file.
    
    Returns:
        List of criterion IDs (folder names)
    """
    criteria_ids = []
    
    for item in _CRITERIA_DIR.iterdir():
        if item.is_dir() and not item.name.startswith("_"):
            definition_path = item / "definition.json"
            if definition_path.exists():
                criteria_ids.append(item.name)
    
    return sorted(criteria_ids)


def _load_criterion_definition(criterion_id: str) -> Dict[str, Any]:
    """
    Load a criterion definition from its folder.
    
    Args:
        criterion_id: Folder name of the criterion
    
    Returns:
        Parsed definition dict
    
    Raises:
        FileNotFoundError: If definition.json doesn't exist
    """
    definition_path = _CRITERIA_DIR / criterion_id / "definition.json"
    
    if not definition_path.exists():
        raise FileNotFoundError(f"definition.json not found for criterion '{criterion_id}'")
    
    with open(definition_path) as f:
        return json.load(f)


def _load_deterministic_function(criterion_id: str, function_name: str) -> callable:
    """
    Load the Python function for a deterministic criterion.
    
    Args:
        criterion_id: Folder name of the criterion
        function_name: Name of the function to load
    
    Returns:
        Callable function
    
    Raises:
        FileNotFoundError: If logic.py doesn't exist
        AttributeError: If function not found in module
    """
    logic_path = _CRITERIA_DIR / criterion_id / "logic.py"
    
    if not logic_path.exists():
        raise FileNotFoundError(f"logic.py not found for deterministic criterion '{criterion_id}'")
    
    # Load the module dynamically
    spec = importlib.util.spec_from_file_location(f"criteria.{criterion_id}.logic", logic_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Get the function
    if not hasattr(module, function_name):
        raise AttributeError(f"Function '{function_name}' not found in {logic_path}")
    
    return getattr(module, function_name)


def _initialize_registry() -> None:
    """
    Initialize the registry by discovering and loading all criteria.
    
    Called lazily on first access.
    """
    global _registry, _initialized
    
    if _initialized:
        return
    
    _registry = {}
    
    for criterion_id in _discover_criteria():
        try:
            definition = _load_criterion_definition(criterion_id)
            
            # Ensure ID matches folder name
            definition["id"] = criterion_id
            
            # For deterministic criteria, load the function
            if definition.get("type") == "deterministic":
                function_name = definition.get("function")
                if function_name:
                    try:
                        func = _load_deterministic_function(criterion_id, function_name)
                        definition["_callable"] = func
                    except (FileNotFoundError, AttributeError) as e:
                        definition["_load_error"] = str(e)
            
            _registry[criterion_id] = definition
        
        except Exception as e:
            # Log error but continue loading other criteria
            print(f"Warning: Failed to load criterion '{criterion_id}': {e}")
    
    _initialized = True


def reload_registry() -> None:
    """
    Force reload of the criteria registry.
    
    Useful after adding new criteria or modifying definitions.
    """
    global _initialized
    _initialized = False
    _initialize_registry()


# ============================================================================
# Public API
# ============================================================================

def get_criterion(criterion_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a criterion definition by ID.
    
    Args:
        criterion_id: The criterion identifier (folder name)
    
    Returns:
        Criterion definition dict, or None if not found
    """
    _initialize_registry()
    return _registry.get(criterion_id)


def get_all_criteria() -> Dict[str, Dict[str, Any]]:
    """
    Get all registered criteria.
    
    Returns:
        Dict mapping criterion_id -> definition
    """
    _initialize_registry()
    return dict(_registry)


def get_criteria_by_type(criterion_type: str) -> List[Dict[str, Any]]:
    """
    Get all criteria of a specific type.
    
    Args:
        criterion_type: "llm" or "deterministic"
    
    Returns:
        List of criterion definitions
    """
    _initialize_registry()
    return [c for c in _registry.values() if c.get("type") == criterion_type]


def get_criteria_by_tag(tag: str) -> List[Dict[str, Any]]:
    """
    Get all criteria with a specific tag.
    
    Args:
        tag: Tag to filter by (e.g., "core", "quality")
    
    Returns:
        List of criterion definitions
    """
    _initialize_registry()
    return [c for c in _registry.values() if tag in c.get("tags", [])]


def get_criteria_for_test(test_case: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get criteria definitions for a test case.
    
    Looks up criteria referenced in the test case's "criteria" array
    and merges any test-specific overrides (threshold, params).
    
    Args:
        test_case: Test case dict with "criteria" array
    
    Returns:
        List of criterion definitions with test-specific overrides applied
    """
    _initialize_registry()
    
    criteria_refs = test_case.get("criteria", [])
    
    if not criteria_refs:
        # Fall back to default criteria based on llm_criteria config
        llm_config = test_case.get("llm_criteria", {})
        if llm_config.get("enabled"):
            focus_areas = llm_config.get("focus_areas", ["relevance", "quality", "diversity"])
            return [_registry[c] for c in focus_areas if c in _registry]
        return []
    
    result = []
    for ref in criteria_refs:
        if isinstance(ref, str):
            # Simple string reference
            criterion = get_criterion(ref)
            if criterion:
                result.append(criterion)
        elif isinstance(ref, dict):
            # Reference with overrides
            criterion_id = ref.get("id")
            criterion = get_criterion(criterion_id)
            if criterion:
                # Merge overrides
                merged = dict(criterion)
                if "threshold" in ref:
                    merged["_threshold_override"] = ref["threshold"]
                if "params" in ref:
                    merged["_params_override"] = ref["params"]
                result.append(merged)
    
    return result


def list_criteria() -> List[str]:
    """
    List all available criterion IDs.
    
    Returns:
        Sorted list of criterion IDs
    """
    _initialize_registry()
    return sorted(_registry.keys())


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Registry functions
    "get_criterion",
    "get_all_criteria",
    "get_criteria_by_type",
    "get_criteria_by_tag",
    "get_criteria_for_test",
    "list_criteria",
    "reload_registry",
    
    # Base classes (re-exported from base.py)
    "CriterionDefinition",
    "CriterionType",
    "LLMCriterion",
    "DeterministicCriterion",
    "parse_criterion",
]
