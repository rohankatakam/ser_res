# Pinecone + Firestore data flow

## How the app gets episode data and embeddings

1. **Episodes** come from **Firestore** when `DATA_SOURCE=firebase`:
   - `FirestoreEpisodeProvider.get_episodes()` and `get_episode_by_content_id_map()`.
   - Episode document id in Firestore = episode id used everywhere.

2. **Embeddings** come from **Pinecone** by **episode id** (no full load):
   - Session create computes needed ids: engagement episode ids + candidate pool episode ids.
   - `vector_store.get_embeddings(needed_ids, algorithm_version, strategy_version, dataset_version)` → Pinecone `index.fetch(ids=needed_ids, namespace=ns)`.
   - Vector id in Pinecone **must equal** Firestore episode document id so we can fetch by id.

3. **Index and namespace**
   - **Index**: Set by `PINECONE_INDEX_NAME` (default: `serafis-episodes`). If you created an index with another name (e.g. `quickstart`), set `PINECONE_INDEX_NAME=quickstart` in `.env`.
   - **Namespace**: `{algorithm_version}_s{strategy_version}__{dataset_version}` (e.g. `algorithm_s1_0__eval_909_feb2026` or `algorithm_s1_0__firestore`). The server uses the **loaded** algorithm’s `folder_name` and dataset’s `folder_name`, so vectors must be in that namespace.

## Populating Pinecone so the app finds vectors

Use the same index and namespace the server uses:

- **Index**: Backend uses `PINECONE_INDEX_NAME` or `serafis-episodes`. Run `populate_pinecone` with the same API key (same project); the script uses the same env and default index.
- **Namespace**: The script now uses the algorithm’s `folder_name` (same as the server). Run:

  ```bash
  # From repo root, with .env loaded (OPENAI_API_KEY, PINECONE_API_KEY, etc.)

  # Episodes from a dataset (writes to namespace algorithm_s1_0__eval_909_feb2026)
  python -m server.scripts.populate_pinecone --source dataset --dataset eval_909_feb2026

  # Episodes from Firestore (writes to namespace algorithm_s1_0__firestore)
  python -m server.scripts.populate_pinecone --source firestore
  ```

- **Episode ids**: The script uses each episode’s `id` (or `content_id`) as the Pinecone vector id so it matches Firestore.

## Docker and env changes

After changing `.env` (e.g. `PINECONE_INDEX_NAME`), restart the backend so it picks up the new values:

```bash
docker-compose down
docker-compose up --build -d
```

Or restart only the backend:

```bash
docker-compose restart backend
```
