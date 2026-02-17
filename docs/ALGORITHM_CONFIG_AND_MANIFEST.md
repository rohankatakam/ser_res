# Algorithm: config.json, manifest.json, and computed_params.py

What each file is, where it’s used, whether you need it, and how you might refactor.

---

## Confirmed: Is computed_params.py used in the UI?

**Yes.** It is used by the frontend only (not by evaluation).

- **Frontend** (`frontend/src/components/ParameterSidebar.jsx`): Calls `computeParameters(baseParams, null)` (see `frontend/src/api.js` → `POST /api/algorithm/compute`). The response `result.computed` is stored in `computedParams` state. The sidebar renders schema groups with `section === 'computed'` and displays values from `computedParams[param.key]` (e.g. normalized weights, recency half-life, diversity strategy). So the algorithm tuning panel uses computed_params to show derived values in real time as the user adjusts sliders.
- **Server** (`server/routes/algorithm.py`): Implements `POST /api/algorithm/compute` by calling `state.current_algorithm.compute_module.compute_parameters(request.base_params, request.profile)` when `compute_module` exists.
- **Evaluation**: Does not call `/api/algorithm/compute` or use computed_params.py; the word "computed" in evaluation reports refers to quality scores in narrative text, not this module.

---

## 1. manifest.json

**What it is**  
Metadata for this algorithm *version*: name, version string, description, embedding model/dimensions, required episode fields, and **default_parameters** (default values for tuning).

**Who loads it**  
- **Server** (`algorithm_loader.py`): reads `manifest.json` and builds `AlgorithmManifest` (version, name, embedding_model, embedding_dimensions, default_parameters, etc.). Stored on `LoadedAlgorithm.manifest`.
- **Evaluation** (`evaluation/runner.py`): can read it for algorithm display name.

**Where it’s used**  
- **Sessions**: `state.current_algorithm.manifest.version` (and `.name`) for response metadata.
- **Config/algorithm routes**: algorithm name/version, and **config diff** uses `manifest.default_parameters` as the “default” baseline when comparing to current config.
- **Evaluation reports**: algorithm name, embedding_strategy_version, embedding_model, etc.
- **Loader**: embedding model/dimensions fallback from manifest when not in embedding_strategy.

**Do you need it?**  
**Yes.** The loader requires it; the API and evaluation use it for identity, defaults, and reporting.

**Refactor / reorganize**  
- Keep as the single “algorithm identity + defaults” file.
- Optional: move it under something like `algorithm/meta/manifest.json` and have the loader look there; only do this if you introduce a broader `meta/` or `config/` layout and want all algorithm metadata in one place.

---

## 2. config.json

**What it is**  
**Runtime parameter values** for this algorithm: the actual numbers the engine uses (stage_a gates, stage_b weights, engagement_weights, cold_start, etc.). Same logical content as manifest’s `default_parameters`, but this is the *loaded* config that can be edited at runtime (and then compared to manifest defaults for “config diff”).

**Who loads it**  
- **Server** (`algorithm_loader.py`): if `config.json` exists, loads it into `LoadedAlgorithm.config` (raw dict). If missing, uses `config = {}` (engine will use `RecommendationConfig` defaults when you call `from_dict`).

**Where it’s used**  
- **Sessions**: `state.current_algorithm.config` is passed to `RecommendationConfig.from_dict(...)` and used for `create_recommendation_queue(..., config)`.
- **Algorithm routes**:  
  - **GET /api/algorithm/config** returns `config` and `schema`.  
  - **POST /api/algorithm/config/update** merges request body into `state.current_algorithm.config` and validates with `config_schema`.  
  - **GET /api/algorithm/config/diff** compares current `config` to “defaults” (from disk `config.json` or manifest.default_parameters).
- **Evaluation**: engine context gets `state.current_algorithm.config` as `algo_config`.

**Do you need it?**  
**Yes.** It’s the source of runtime parameters for the recommendation engine and for the tuning UI. Without it you’re either hardcoding or using only manifest defaults.

**Refactor / reorganize**  
- **Option A (minimal):** Keep `config.json` at algorithm root; ensure its shape matches what `RecommendationConfig.from_dict()` expects (nested `stage_a`, `stage_b`, `engagement_weights`, `cold_start`). No structural change.
- **Option B:** Move to `algorithm/config/params.json` (or `algorithm/config/runtime.json`) and point the loader at that path. Only worth it if you want a dedicated `config/` dir (e.g. params + schema + manifest together).
- **Single source of truth:** Right now you have both `manifest.default_parameters` and `config.json`. You could:
  - Treat **config.json** as the only source: loader loads it, and “defaults” for diff come from a copy or from manifest generated from it.
  - Or treat **manifest.default_parameters** as canonical and have config.json optional “overrides”; then loader does `config = load config.json if exists else manifest.default_parameters`. Either way, document which is canonical to avoid drift.

---

## 3. computed_params.py

**What it is**  
A **read-only “derived parameters”** module. It takes the same base params (e.g. from config.json) and optionally a user profile, and returns a dict of *computed* values: normalized weights, recency half-life, quality score range, engagement weight ratios, category diversity stats, and (with a profile) user-vector stats and cold-start flag. Used so the UI can show “what does this config imply?” without running the full engine.

**Who loads it**  
- **Server** (`algorithm_loader.py`): if `computed_params.py` exists, loads it as `LoadedAlgorithm.compute_module`.

**Where it’s used**  
- **Algorithm route** `POST /api/algorithm/compute`: request body has `base_params` (and optional `profile`); server calls `state.current_algorithm.compute_module.compute_parameters(base_params, profile)` and returns the result. The frontend uses this to show derived values (e.g. normalized weights, half-life, diversity strategy) while the user tweaks sliders.

**Do you need it?**  
**Only if you want the “computed parameters” UI.** The recommendation engine does **not** call it; it only uses `RecommendationConfig` (from config.json + updates). So:
- If the tuning UI shows “normalized weights”, “recency half-life”, “diversity strategy”, etc., you need this (or an equivalent).
- If you remove that UI or move it to a different backend, you can drop it.

**Refactor / reorganize**  
- **Keep as-is:** Single module, one function `compute_parameters(base_params, profile=None)`. Fits the loader and the single `/api/algorithm/compute` endpoint.
- **Move into algorithm package:** e.g. `algorithm/computed_params.py` → `algorithm/params/computed.py` and have the loader load `algorithm.params.computed` when the algorithm is loaded as a package; or keep the file at algorithm root so the loader-by-path still finds it.
- **Align with models/config.py:** `computed_params` consumes the same nested dict shape as config.json. You could:
  - Add a small layer in the server that builds that dict from `state.current_algorithm.config` and passes it into `compute_parameters`, so the Python module doesn’t care where the dict came from.
  - Or have `compute_parameters` accept also a `RecommendationConfig` and derive the dict internally (avoids duplicate flattening logic).
- **Schema-driven:** If you later define “computed” fields in config_schema.json (e.g. which keys are computed and how), you could generate or validate the outputs of `compute_parameters` from that schema; that’s a larger refactor.

---

## 4. config_schema.json (for completeness)

**What it is**  
Schema for the **tuning UI**: groups, param keys, types, min/max, labels, and constraints (e.g. “stage_b weights must sum to 1”). Used for validation and for rendering controls.

**Used by**  
- **GET /api/algorithm/config** (returned as `schema`).
- **POST /api/algorithm/config/update** (validation via `validate_config_against_schema(merged_config, config_schema)`).
- **GET /api/algorithm/config/diff** (indirectly; diff is key-based).

You need this if you keep the parameter-tuning UI. It should stay in sync with the shape of config.json and with `RecommendationConfig.from_dict()`.

---

## 5. Summary table

| File               | Purpose                         | Required? | Used by                                      |
|--------------------|----------------------------------|-----------|----------------------------------------------|
| **manifest.json** | Identity, defaults, embedding   | Yes       | Loader, API (version/name), config diff, eval |
| **config.json**   | Runtime parameter values        | Yes       | Loader → engine config, tuning UI, diff      |
| **config_schema.json** | UI schema + validation   | Yes (for UI) | Algorithm routes (config + update + validation) |
| **computed_params.py** | Derived/read-only params for UI | Only if you use “computed” UI | POST /api/algorithm/compute |

---

## 6. Overlap: config.json, manifest.json, and algorithm/models/config.py

The **same parameter set** (stage_a, stage_b, engagement_weights, cold_start) is represented in three places:

| Source | Role | Default values (examples) |
|--------|------|---------------------------|
| **algorithm/models/config.py** | Python dataclass: field names, types, and **code defaults**. `RecommendationConfig.from_dict()` consumes a nested dict and fills missing keys from these defaults. | e.g. weight_similarity=0.55, weight_quality=0.30, weight_recency=0.15 |
| **config.json** | **Runtime** values loaded by the server. Nested shape: `stage_a`, `stage_b`, `engagement_weights`, `cold_start`. Passed to `from_dict()` so the engine uses these values. | e.g. 0.85, 0.1, 0.05 (v1.5 tuned); same structure as manifest.default_parameters |
| **manifest.json** | **Metadata** (version, name, embedding_*, required_fields) plus **default_parameters** (flattened/nested). Used as algorithm identity and as the "baseline" for config diff (current vs default). | default_parameters: same logical content as config.json (v1.5 values) |

So aside from metadata (version, name, description, embedding_*, etc.):

- **Parameter names and structure** are defined in `models/config.py` (the dataclass and `from_dict()`).
- **Default / tuned values** appear in both **config.json** and **manifest.default_parameters** (and can differ from the Python defaults in `RecommendationConfig`). Right now config.json and manifest.default_parameters align (v1.5); the dataclass defaults (0.55/0.30/0.15) are different and only apply when a key is missing from the dict.

So yes: the "data" (which params exist and their shape) is described in `models/config.py`; the **values** for this algorithm version live in config.json and manifest.default_parameters. To avoid drift, pick one source of truth for default values (e.g. manifest.default_parameters or config.json) and have the loader use it; optionally generate or validate config.json from manifest, or vice versa.

---

## 7. Refactor / reorganization ideas

1. **Single source for “default” config**  
   Decide whether manifest.default_parameters or config.json is canonical. Option: loader does `config = load(config.json) if exists else manifest.default_parameters`, and “config diff” always compares current in-memory config to manifest.default_parameters (or to a read-only copy of config.json). That way you don’t have two places that can drift.

2. **Optional `algorithm/config/` directory**  
   Put all config-related files in one place, e.g.  
   `algorithm/config/params.json` (current config.json),  
   `algorithm/config/schema.json` (current config_schema.json),  
   and optionally a single `algorithm/config/defaults.json` if you split defaults out of manifest.  
   Then point the loader at `config/params.json` and `config/schema.json`. manifest.json can stay at root as “algorithm identity”.

3. **Keep computed_params.py, but align with RecommendationConfig**  
   Have `compute_parameters(base_params, profile)` accept the same nested structure as config.json. Optionally add a helper that takes `RecommendationConfig` and builds the dict for `compute_parameters` so the server only deals with one type (e.g. current_algorithm.config dict) and the engine’s config model stays the single source of field names.

4. **Document the contract**  
   In the algorithm repo or docs, document: “config.json shape = what RecommendationConfig.from_dict() accepts; config_schema.json describes that shape for the UI; computed_params.py input = same shape as config.json.”

This keeps manifest, config, schema, and computed params clearly defined and gives you a path to reorganize without breaking the loader or the API.
