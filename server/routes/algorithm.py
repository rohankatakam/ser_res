"""Algorithm config and compute endpoints."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

try:
    from ..state import get_state
    from ..utils import deep_merge, validate_config_against_schema
    from ..models.config import ConfigUpdateRequest, ComputeParamsRequest
except ImportError:
    from state import get_state
    from utils import deep_merge, validate_config_against_schema
    from models.config import ConfigUpdateRequest, ComputeParamsRequest

router = APIRouter()


@router.get("/config")
def get_algorithm_config():
    """Get current algorithm config and schema for UI parameter tuning."""
    state = get_state()
    if not state.current_algorithm:
        raise HTTPException(
            status_code=400,
            detail="No algorithm loaded. Call /api/config/load first.",
        )
    return {
        "algorithm": state.current_algorithm.folder_name,
        "algorithm_name": state.current_algorithm.manifest.name,
        "algorithm_version": state.current_algorithm.manifest.version,
        "config": state.current_algorithm.config,
        "schema": state.current_algorithm.config_schema,
    }


@router.post("/config/update")
def update_algorithm_config(request: ConfigUpdateRequest):
    """Update algorithm config at runtime (not persisted to file)."""
    state = get_state()
    if not state.current_algorithm:
        raise HTTPException(
            status_code=400,
            detail="No algorithm loaded. Call /api/config/load first.",
        )
    current_config = state.current_algorithm.config
    merged_config = deep_merge(current_config, request.config)
    errors = validate_config_against_schema(
        merged_config, state.current_algorithm.config_schema
    )
    if errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "Config validation failed", "validation_errors": errors},
        )
    state.current_algorithm.config = merged_config
    state.sessions.clear()
    return {
        "success": True,
        "message": "Config updated. Existing sessions cleared.",
        "config": merged_config,
    }


@router.get("/config/diff")
def get_algorithm_config_diff():
    """Compare current algorithm config with defaults."""
    state = get_state()
    if not state.current_algorithm:
        raise HTTPException(
            status_code=400,
            detail="No algorithm loaded. Call /api/config/load first.",
        )
    current_config = state.current_algorithm.config
    config_path = (
        state.config.algorithms_dir
        / state.current_algorithm.folder_name
        / "config.json"
    )
    try:
        with open(config_path) as f:
            original_config = json.load(f)
    except Exception:
        original_config = state.current_algorithm.manifest.default_parameters
    changed_params = []

    def compare_nested(current, original, prefix=""):
        all_keys = set(current.keys()) | set(original.keys())
        for key in all_keys:
            current_value = current.get(key)
            original_value = original.get(key)
            full_key = f"{prefix}.{key}" if prefix else key
            if key.startswith("_"):
                continue
            if isinstance(original_value, dict) and isinstance(current_value, dict):
                compare_nested(current_value, original_value, full_key)
            elif isinstance(original_value, dict) and current_value is None:
                compare_nested({}, original_value, full_key)
            elif current_value is None and original_value is None:
                pass
            elif current_value is None or original_value is None:
                if current_value is not None or original_value is not None:
                    changed_params.append({
                        "key": full_key,
                        "default": original_value,
                        "current": current_value,
                        "diff_percent": None,
                        "type": type(original_value).__name__ if original_value is not None else type(current_value).__name__,
                    })
            elif current_value != original_value:
                diff_pct = None
                if isinstance(original_value, (int, float)) and isinstance(current_value, (int, float)):
                    if original_value != 0:
                        diff_pct = ((current_value - original_value) / original_value) * 100
                changed_params.append({
                    "key": full_key,
                    "default": original_value,
                    "current": current_value,
                    "diff_percent": diff_pct,
                    "type": type(original_value).__name__,
                })

    compare_nested(current_config, original_config)
    return {
        "has_changes": len(changed_params) > 0,
        "changed_params": changed_params,
        "change_count": len(changed_params),
        "algorithm": state.current_algorithm.folder_name,
        "algorithm_version": state.current_algorithm.manifest.version,
    }


@router.post("/compute")
def compute_derived_parameters(request: ComputeParamsRequest):
    """Compute derived parameters from base parameters in real-time."""
    state = get_state()
    if not state.current_algorithm:
        raise HTTPException(
            status_code=400,
            detail="No algorithm loaded. Call /api/config/load first.",
        )
    if not state.current_algorithm.compute_module:
        return {
            "computed": {},
            "success": True,
            "message": "This algorithm version does not have computed parameters",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    try:
        computed = state.current_algorithm.compute_module.compute_parameters(
            base_params=request.base_params,
            profile=request.profile,
        )
        return {
            "computed": computed,
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Computation failed: {str(e)}")
