# Refactor Plan: Algorithm + Server

**Note:** Qdrant references in this document are outdated. Pinecone is the primary embedding store for production; Qdrant is deprecated.

This document plans refactoring of `algorithm/` and `server/` to remove redundancy, dead code, and ambiguous or poorly written code. It extends the cleanup work from `CLEANUP_PLAN.md`.

---

## 1. Current Structure (Brief)

| Layer | Role |
|-------|------|
| **algorithm/** | Single version (flat): `manifest.json`, `config.json`, `config_schema.json`, `embedding_strategy.py`, `recommendation_engine.py`, `computed_params.py`. Defines embedding text, config schema, and ranking (candidate pool + blended scoring). |
| **server/** | Loads algorithm + dataset; manages embeddings (JSON cache + Qdrant); exposes config, embeddings, sessions, evaluation. Uses algorithm’s engine and embedding strategy at runtime. |

**Data flow:** `AlgorithmLoader` + `DatasetLoader` → load algorithm + dataset; embeddings from `EmbeddingCache` (JSON) or `QdrantEmbeddingStore`; session creation calls `engine.create_recommendation_queue(...)` with `RecommendationConfig.from_dict(algorithm.config)`.

---

## 2. Redundant Code

### 2.1 `get_badges` duplicated

- **algorithm/recommendation_engine.py**: `get_badges(ep)` (lines ~428–446) — score-based badges, max 2.
- **server/server.py**: `get_badges(ep)` (lines ~1270–1284) — same logic, copy-pasted.

**Action:** Use a single source. Have server call the engine’s `get_badges` when building `EpisodeCard` (e.g. `engine_module.get_badges(ep)` if engine is loaded), or move badge logic into a small shared helper used by both. Prefer using the algorithm’s implementation so badge rules stay with the algorithm.

### 2.2 Cache key / collection name logic duplicated

- **server/embedding_cache.py**: `get_cache_key(algorithm_version, strategy_version, dataset_version)` — sanitizes and formats string.
- **server/qdrant_store.py**: `get_collection_name(...)` — same idea, slightly different sanitization (more chars replaced for Qdrant).

**Action:** Extract a single `cache_key_for(algorithm_version, strategy_version, dataset_version)` (e.g. in a small `server/cache_keys.py` or inside `embedding_cache.py`) that returns the canonical key string. Have `EmbeddingCache` use it for the filename and `QdrantEmbeddingStore` use it (or a Qdrant-safe variant from it) for the collection name so key rules live in one place.

### 2.3 Config path bug (flat algorithm dir)

- **server/server.py** (e.g. ~765):  
  `config_path = state.config.algorithms_dir / state.current_algorithm.folder_name / "config.json"`  
  With a flat layout, `algorithms_dir` is `.../algorithm` and `folder_name` is `"algorithm"`, so this becomes `.../algorithm/algorithm/config.json`, which does not exist.

**Action:** Use the loaded algorithm’s path:  
`config_path = state.current_algorithm.path / "config.json"`.  
Same for any other place that builds paths under the “current algorithm” (e.g. diff, compute) so they work for both flat and (future) versioned layouts.

### 2.4 Algorithm “list” vs flat layout

- **server/algorithm_loader.py**: `list_algorithms()` only considers **subdirectories** of `algorithms_dir`. With a flat layout (all files in `algorithm/`), there are no subdirs, so the list is empty while `load_algorithm()` still loads the single algorithm from `algorithms_dir` itself.

**Action:** Support “single algorithm in algorithms_dir” explicitly:  
e.g. if `algorithms_dir / "manifest.json"` exists, treat the directory itself as one algorithm and return one entry (folder_name can be `algorithms_dir.name` or a fixed id like `"current"`). This keeps UI and APIs consistent (e.g. “current” algorithm appears in the list).

---

## 3. Unused / Dead Code

### 3.1 `validate_episode_for_embedding`

- **algorithm/embedding_strategy.py**: `validate_episode_for_embedding(episode)` exists but is **never used** in algorithm or server (embedding generation doesn’t call it).

**Action:** Either wire it into embedding generation (e.g. in `EmbeddingGenerator.generate_for_episodes` or the server’s generate flow) to skip invalid episodes and report errors, or remove it to avoid dead code.

### 3.2 Algorithm `__init__.py` docstring / version drift

- **algorithm/__init__.py**: Docstring says “V1.2 Blended Scoring”; `manifest.json` and code are v1.5 (diversified, cold start diversity, etc.).

**Action:** Update the top-level docstring (and any “V1.2” references in algorithm docstrings) to reflect the current version (e.g. “V1.5 Diversified”) so new readers aren’t misled.

### 3.3 `RecommendationConfig` default weights vs `config.json`

- **algorithm/recommendation_engine.py**: `DEFAULT_CONFIG` uses `weight_similarity=0.55`, `weight_quality=0.30`, `weight_recency=0.15`.
- **algorithm/config.json**: Uses 0.85, 0.10, 0.05.  
  Runtime config comes from `RecommendationConfig.from_dict(state.current_algorithm.config)`, so the class defaults only apply when no config is passed. No functional bug, but two sources of “defaults” (class vs manifest/config) can confuse.

**Action:** Document that `config.json` (and manifest `default_parameters`) are the source of truth for the shipped algorithm; keep `DEFAULT_CONFIG` as a fallback for tests or missing config and add a one-line comment that production config comes from JSON/manifest.

### 3.4 Hardcoded debug weights in server

- **server/server.py** (~1387–1391): `SessionDebugInfo` uses hardcoded `scoring_weights = {"similarity": 0.55, "quality": 0.30, "recency": 0.15}`. Actual weights come from the algorithm config (e.g. 0.85, 0.10, 0.05).

**Action:** Populate debug scoring weights from the same config used for the session (e.g. from `algo_config` built via `RecommendationConfig.from_dict`) so the debug panel reflects the real weights.

---

## 4. Ambiguous or Poorly Written Code

### 4.1 Single “current” algorithm vs folder_name

- `LoadedAlgorithm.folder_name` is set to `folder_path.name` (e.g. `"algorithm"`). It’s used in many places as the “algorithm id” for cache keys, API responses, and paths. With a flat layout this is the dir name, not a version id; with future versioned subdirs it would be the subdir name.

**Action:** Keep one consistent meaning: “algorithm identifier used in cache keys and API.” For flat layout, either (a) use a stable id like `"current"` in API/cache and keep `path` for file paths, or (b) derive a version from `manifest.version` (e.g. `v1_5_diversified`) for display and cache keys. Prefer (b) so cache keys and UI match the manifest. Then use `current_algorithm.path` for all filesystem paths under the algorithm.

### 4.2 Unload / reload and cache key

- **algorithm_loader**: `unload_algorithm(folder_name)` and `reload_algorithm(folder_name)` use `folder_name`, but `load_algorithm` ignores it and caches under `"current"`. So `unload_algorithm("v1_5")` never clears the cached algorithm.

**Action:** Make cache key consistent: e.g. always use `"current"` for the single-algorithm flat layout. Then `unload_algorithm("current")` (or any string) can clear that cache; or expose `unload_current()` and use that from server if needed.

### 4.3 Validator “algorithm_folder” / “dataset_folder”

- **validator**: Takes `algorithm_folder` and `dataset_folder` and calls `algorithm_loader.load_algorithm(algorithm_folder)` and `dataset_loader.load_dataset(dataset_folder)`. For algorithm, `folder_name` is ignored by `load_algorithm`, so the validator still works but the parameter name is misleading.

**Action:** Keep the validator API for compatibility, but document that for the current flat algorithm layout, `algorithm_folder` is ignored. No code change required if list/diff paths are fixed as above.

### 4.4 Two embedding backends (JSON + Qdrant)

- Server supports both `EmbeddingCache` (JSON files) and `QdrantEmbeddingStore`; logic in server chooses which to use for read/write and status. This is fine for flexibility but adds branching and duplicate “has_cache / load_embeddings / save_embeddings” concepts.

**Action:** Keep both backends but isolate the “which backend to use” and “delegate to backend” logic in one place (e.g. a thin `EmbeddingStore` facade that holds cache + qdrant and implements `has_cache`, `load`, `save` once). Reduces duplication in server.py and makes it obvious where to add a new backend later.

---

## 5. Proposed Refactor Order

Do these in order so each step stays testable.

1. **Algorithm: docstrings and single source for badges**
   - Update algorithm `__init__.py` and any “V1.2” references to current version.
   - Remove `get_badges` from server and use `engine.get_badges(ep)` (or equivalent) when building episode cards.
   - **Test:** Sessions still return correct badges; one place defines badge rules.

2. **Server: config path and algorithm list**
   - Use `state.current_algorithm.path / "config.json"` (and same for other algorithm file paths) instead of `algorithms_dir / folder_name / ...`.
   - In `algorithm_loader.list_algorithms()`, if `algorithms_dir` has `manifest.json`, return one entry for the “current” algorithm (folder_name from dir name or manifest version).
   - **Test:** Config load/diff/compute work; `/api/config/algorithms` returns one algorithm when using flat layout.

3. **Server: shared cache key**
   - Add a small module or function that computes the canonical cache key string. Use it in `EmbeddingCache` and in `QdrantEmbeddingStore` (with Qdrant-safe sanitization if needed).
   - **Test:** Embedding status, generate, and Qdrant/JSON behavior unchanged; keys match between backends.

4. **Server: debug weights from config**
   - Build session debug `scoring_weights` from the same `RecommendationConfig` (or algo config dict) used for the session.
   - **Test:** Debug panel shows actual weights (e.g. 0.85, 0.10, 0.05).

5. **Algorithm: optional use or remove `validate_episode_for_embedding`**
   - Either call it during embedding generation and skip invalid episodes (and document), or remove it from `embedding_strategy.py`.
   - **Test:** Embedding generation still works; if kept, invalid episodes are skipped and counts/errors are correct.

6. **Algorithm: document config source of truth**
   - Add a short comment in `recommendation_engine.py` that production defaults come from `config.json` / manifest; `DEFAULT_CONFIG` is for fallback/tests only.

7. **Optional later: embedding store facade**
   - Introduce a single facade that delegates to JSON cache and/or Qdrant so server.py has one “store” and fewer branches. Low priority if current branching is acceptable.

---

## 6. Testing After Each Step

- **Health:** `GET /api/health`, `GET /`
- **Config:** `GET /api/config/algorithms`, `GET /api/config/datasets`, `POST /api/config/load` with current algorithm/dataset, `GET /api/algorithm/config`, `GET /api/algorithm/config/diff`
- **Embeddings:** `GET /api/embeddings/status`, optionally `POST /api/embeddings/generate` (with key) if not already cached
- **Sessions:** `POST /api/sessions/create` with minimal body, `GET /api/sessions/{id}`, `POST /api/sessions/{id}/next`; check episode cards and debug weights
- **Evaluation:** Run `evaluation/runner.py --test 01` (or one test) against the server

Run these after steps 1–2 and again after 4–5; full regression before/after the optional step 7.

---

## 7. Summary Table

| Issue | Location | Action |
|-------|----------|--------|
| Duplicate `get_badges` | server vs algorithm | Use engine’s `get_badges` in server |
| Duplicate cache key logic | embedding_cache, qdrant_store | Shared cache-key helper |
| Wrong config path (flat) | server.py | Use `current_algorithm.path / "config.json"` |
| Empty algorithm list (flat) | algorithm_loader | Treat algorithms_dir with manifest as one algorithm |
| Unused `validate_episode_for_embedding` | embedding_strategy | Use in generation or remove |
| Version docstring drift | algorithm __init__ | Update to V1.5 / current |
| Debug weights hardcoded | server SessionDebugInfo | Use algo config |
| Default config vs JSON | recommendation_engine | Comment only |
| Unload/reload cache key | algorithm_loader | Align with "current" / doc |

This plan removes redundancy, fixes the config path and list behavior for the flat layout, and clarifies where configuration and behavior are defined, without changing the external API contract.
