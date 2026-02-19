"""Evaluation endpoints: profiles, test cases, reports, run, judge-config."""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Header

try:
    from ..state import get_state
    from ..models import RunAllTestsRequest, RunTestRequest
except ImportError:
    from state import get_state
    from models import RunAllTestsRequest, RunTestRequest

# Runner is imported after EVALUATION_DIR is on path (set in server.py / app.py)
from runner import (
    run_test_async,
    run_all_tests_async,
    EngineContext,
    load_all_profiles,
)

router = APIRouter()


def _build_engine_context(state) -> EngineContext:
    """
    Build EngineContext for evaluation, using Firestore + Pinecone when configured
    (same data sources as session creation).
    """
    engine = state.current_algorithm.engine_module
    algo_config = getattr(state.current_algorithm, "parsed_config", None) or state.current_algorithm.config

    # Episodes: Firestore when provider exists, else dataset (build map from episodes to avoid second scan)
    if state.current_episode_provider:
        episodes = state.current_episode_provider.get_episodes(limit=None)
        episode_by_content_id = {ep["content_id"]: ep for ep in episodes if isinstance(ep, dict) and ep.get("content_id")}
    else:
        episodes = state.current_dataset.episodes
        episode_by_content_id = state.current_dataset.episode_by_content_id

    # Embeddings: use in-memory when available, else fetch from Pinecone in batches
    # (fetching all 900+ ids at once can hit 414 Request-URI Too Large)
    embeddings = state.current_embeddings
    if not embeddings and state.vector_store:
        all_ids = [eid for ep in episodes for eid in (ep.get("id"), ep.get("content_id")) if eid]
        all_ids = list(dict.fromkeys(all_ids))
        if all_ids:
            batch_size = 100
            merged: dict = {}
            for i in range(0, len(all_ids), batch_size):
                chunk = all_ids[i : i + batch_size]
                batch = state.vector_store.get_embeddings(
                    chunk,
                    state.current_algorithm.folder_name,
                    state.current_algorithm.strategy_version,
                    state.current_dataset.folder_name,
                )
                if batch:
                    merged.update(batch)
            embeddings = merged
    if not embeddings:
        embeddings = {}

    return EngineContext(
        engine_module=engine,
        episodes=episodes,
        embeddings=embeddings,
        episode_by_content_id=episode_by_content_id,
        algo_config=algo_config,
    )


@router.get("/profiles")
def list_profiles():
    """List available evaluation profiles."""
    state = get_state()
    profiles_dir = state.config.evaluation_dir / "profiles"
    if not profiles_dir.exists():
        return {"profiles": []}
    profiles = []
    for path in profiles_dir.glob("*.json"):
        try:
            with open(path) as f:
                profile = json.load(f)
            profiles.append({
                "id": profile.get("profile_id", path.stem),
                "name": profile.get("name", path.stem),
                "description": profile.get("description", ""),
                "engagements_count": len(profile.get("engagements", [])),
            })
        except (json.JSONDecodeError, IOError):
            continue
    return {"profiles": profiles}


@router.get("/profiles/{profile_id}")
def get_profile(profile_id: str):
    """Get a specific profile."""
    state = get_state()
    profile_path = state.config.evaluation_dir / "profiles" / f"{profile_id}.json"
    if not profile_path.exists():
        raise HTTPException(status_code=404, detail="Profile not found")
    with open(profile_path) as f:
        return json.load(f)


@router.get("/test-cases")
def list_test_cases():
    """List available test cases."""
    state = get_state()
    tests_dir = state.config.evaluation_dir / "test_cases"
    if not tests_dir.exists():
        return {"test_cases": []}
    test_cases = []
    for path in tests_dir.glob("*.json"):
        try:
            with open(path) as f:
                test = json.load(f)
            test_cases.append({
                "id": test.get("test_id", path.stem),
                "name": test.get("name", path.stem),
                "type": test.get("type", ""),
                "evaluation_method": test.get("evaluation_method", "deterministic"),
                "description": test.get("description", ""),
            })
        except (json.JSONDecodeError, IOError):
            continue
    return {"test_cases": sorted(test_cases, key=lambda x: x["id"])}


@router.get("/test-cases/{test_id}")
def get_test_case(test_id: str):
    """Get a specific test case."""
    state = get_state()
    test_path = state.config.evaluation_dir / "test_cases" / f"{test_id}.json"
    if not test_path.exists():
        raise HTTPException(status_code=404, detail="Test case not found")
    with open(test_path) as f:
        return json.load(f)


@router.get("/reports")
def list_reports():
    """List saved test reports."""
    state = get_state()
    reports_dir = state.config.evaluation_dir / "reports"
    if not reports_dir.exists():
        return {"reports": []}
    reports = []
    for path in reports_dir.glob("*.json"):
        try:
            with open(path) as f:
                report = json.load(f)
            reports.append({
                "id": path.stem,
                "timestamp": report.get("timestamp", ""),
                "total_tests": report.get("total_tests", 0),
                "passed": report.get("passed", 0),
                "failed": report.get("failed", 0),
                "context": report.get("context", {}),
            })
        except (json.JSONDecodeError, IOError):
            continue
    return {"reports": sorted(reports, key=lambda x: x["timestamp"], reverse=True)}


@router.get("/reports/{report_id}")
def get_report(report_id: str):
    """Get a specific test report."""
    state = get_state()
    report_path = state.config.evaluation_dir / "reports" / f"{report_id}.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    with open(report_path) as f:
        return json.load(f)


@router.post("/run")
async def run_single_test(
    request: RunTestRequest,
    x_openai_key: Optional[str] = Header(None, alias="X-OpenAI-Key"),
    x_gemini_key: Optional[str] = Header(None, alias="X-Gemini-Key"),
    x_anthropic_key: Optional[str] = Header(None, alias="X-Anthropic-Key"),
):
    """Run a single test case with multi-LLM evaluation."""
    state = get_state()
    if not state.is_loaded:
        raise HTTPException(
            status_code=400,
            detail="No algorithm/dataset loaded. Call /api/config/load first.",
        )
    if x_openai_key:
        os.environ["OPENAI_API_KEY"] = x_openai_key
    if x_gemini_key:
        os.environ["GEMINI_API_KEY"] = x_gemini_key
    if x_anthropic_key:
        os.environ["ANTHROPIC_API_KEY"] = x_anthropic_key
    profiles = load_all_profiles()
    engine_context = _build_engine_context(state)
    result = await run_test_async(
        test_id=request.test_id,
        profiles=profiles,
        verbose=False,
        skip_llm=False,
        legacy_mode=False,
        engine_context=engine_context,
    )
    return result.to_dict()


@router.post("/run-all")
async def run_all_tests_endpoint(
    request: RunAllTestsRequest,
    x_openai_key: Optional[str] = Header(None, alias="X-OpenAI-Key"),
    x_gemini_key: Optional[str] = Header(None, alias="X-Gemini-Key"),
    x_anthropic_key: Optional[str] = Header(None, alias="X-Anthropic-Key"),
):
    """Run all test cases with multi-LLM evaluation."""
    state = get_state()
    if not state.is_loaded:
        raise HTTPException(
            status_code=400,
            detail="No algorithm/dataset loaded. Call /api/config/load first.",
        )
    if x_openai_key:
        os.environ["OPENAI_API_KEY"] = x_openai_key
    if x_gemini_key:
        os.environ["GEMINI_API_KEY"] = x_gemini_key
    if x_anthropic_key:
        os.environ["ANTHROPIC_API_KEY"] = x_anthropic_key
    profiles = load_all_profiles()
    engine_context = _build_engine_context(state)
    results = await run_all_tests_async(
        verbose=False,
        skip_llm=False,
        method_filter=None,
        legacy_mode=False,
        engine_context=engine_context,
    )
    results_dicts = [r.to_dict() for r in results]
    passed = sum(1 for r in results_dicts if r.get("passed", False))
    failed = len(results_dicts) - passed
    mft_tests = ["03_quality_gates_credibility", "04_excluded_episodes"]
    total_weight = 0.0
    weighted_score = 0.0
    total_confidence = 0.0
    for r in results_dicts:
        test_scores = r.get("scores", {})
        if test_scores and test_scores.get("aggregate_score") is not None:
            weight = 2.0 if r.get("test_id") in mft_tests else 1.0
            weighted_score += test_scores.get("aggregate_score", 0) * weight
            total_confidence += test_scores.get("aggregate_confidence", 1.0) * weight
            total_weight += weight
    overall_score = round(weighted_score / total_weight, 2) if total_weight > 0 else 0.0
    overall_confidence = round(total_confidence / total_weight, 2) if total_weight > 0 else 0.0
    try:
        from judges import get_available_providers
        llm_providers = get_available_providers()
    except Exception:
        llm_providers = []
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context": {
            "algorithm_version": state.current_algorithm.folder_name if state.current_algorithm else None,
            "algorithm_name": state.current_algorithm.manifest.name if state.current_algorithm else None,
            "dataset_version": state.current_dataset.folder_name if state.current_dataset else None,
            "dataset_episode_count": len(state.current_dataset.episodes) if state.current_dataset else 0,
            "llm_providers": llm_providers,
            "evaluation_mode": "multi_llm",
        },
        "algorithm_config": {
            "config_snapshot": state.current_algorithm.config if state.current_algorithm else {},
            "manifest_defaults": state.current_algorithm.manifest.default_parameters if state.current_algorithm else {},
            "embedding_strategy_version": state.current_algorithm.manifest.embedding_strategy_version if state.current_algorithm else None,
            "embedding_model": state.current_algorithm.manifest.embedding_model if state.current_algorithm else None,
        },
        "summary": {
            "total_tests": len(results_dicts),
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / len(results_dicts), 3) if results_dicts else 0,
            "overall_score": overall_score,
            "overall_confidence": overall_confidence,
            "score_breakdown": {
                r.get("test_id"): r.get("scores", {}).get("aggregate_score", 0)
                for r in results_dicts
            },
        },
        "results": results_dicts,
    }
    if request.save_report:
        reports_dir = state.config.evaluation_dir / "reports"
        reports_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        algo = state.current_algorithm.folder_name if state.current_algorithm else "unknown"
        dataset = state.current_dataset.folder_name if state.current_dataset else "unknown"
        report_filename = f"{timestamp}_{algo}__{dataset}.json"
        report_path = reports_dir / report_filename
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        report["report_id"] = report_filename.replace(".json", "")
        report["report_path"] = str(report_path)
    return report


@router.get("/judge-config")
def get_judge_config():
    """Get current judge configuration from judges/config.json."""
    state = get_state()
    config_path = state.config.evaluation_dir / "judges" / "config.json"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Judge configuration file not found")
    try:
        with open(config_path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse judge configuration: {str(e)}",
        )


@router.post("/judge-config")
def update_judge_config(config: Dict[str, Any]):
    """Update judge configuration in judges/config.json."""
    state = get_state()
    config_path = state.config.evaluation_dir / "judges" / "config.json"
    if "judges" not in config:
        raise HTTPException(status_code=400, detail="Configuration must include 'judges' array")
    if not isinstance(config["judges"], list):
        raise HTTPException(status_code=400, detail="'judges' must be an array")
    for judge in config["judges"]:
        if not isinstance(judge, dict):
            raise HTTPException(status_code=400, detail="Each judge must be an object")
        if "provider" not in judge or "model" not in judge or "enabled" not in judge:
            raise HTTPException(
                status_code=400,
                detail="Each judge must have 'provider', 'model', and 'enabled' fields",
            )
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        return {"status": "success", "message": "Judge configuration updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write configuration: {str(e)}")
