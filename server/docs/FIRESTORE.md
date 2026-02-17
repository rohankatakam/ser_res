# Using Cloud Firestore with Serafis

This describes how to upload episode/series data to Cloud Firestore and use it as the episode source for the recommendation server.

## 1. Firebase project and service account

1. In the [Firebase Console](https://console.firebase.google.com), select your project (or create one).
2. Go to **Project settings** (gear) → **Service accounts**.
3. Click **Generate new private key** and save the JSON file (e.g. `serviceAccountKey.json`).
4. Set the environment variable before running the upload script or the server:

   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/serviceAccountKey.json
   ```

**Security:** Do not commit the key file. It is in `.gitignore` (`**/serviceAccountKey.json`, `**/*-firebase-adminsdk-*.json`, `secrets/`). In `.env` set `FIREBASE_CREDENTIALS_PATH` to the key path; Docker Compose mounts it into the backend automatically.

## 2. Upload episodes and series

From the repo root, with credentials set:

```bash
pip install -r server/requirements.txt
python -m server.scripts.upload_to_firestore
```

Optional arguments:

- `--dataset-path PATH` — Path to the dataset directory (default: `datasets/eval_909_feb2026`).
- `--skip-users` — Do not create the `users` collection placeholder.

This creates three collections:

- **episodes** — One document per episode; document ID = episode `id`. Fields match your JSON (title, published_at, scores, key_insight, etc.).
- **series** — One document per series; document ID = series `id`.
- **users** — Empty except for an optional placeholder doc; use for user/engagement persistence later.

## 3. Firestore indexes

For filtered episode queries (e.g. by `published_at`), create an index in the Firebase Console:

1. **Firestore** → **Indexes** → **Composite**.
2. Collection: `episodes`.
3. Fields: `published_at` (Descending).
4. Query scope: Collection.

If you use both `since` and `until` in queries, the same index supports range queries on `published_at`.

## 4. Using Firestore as the episode source in the server

After upload, point the server at Firestore instead of the file-based dataset when loading config:

- **Option A (code):** When building the app state or loading config, if the request or env indicates Firestore (e.g. `EPISODE_SOURCE=firestore`), instantiate `FirestoreEpisodeProvider()` and set `state.current_episode_provider` to it instead of `DatasetEpisodeProvider(dataset)`. You still need an algorithm and embeddings (e.g. from a fixed dataset or precomputed store).
- **Option B (API):** Add a load endpoint or env that uses Firestore: e.g. `POST /api/config/load` with `"episode_source": "firestore"` and optional `"firestore_project_id": "your-project-id"`, and wire it to `FirestoreEpisodeProvider(project_id=...)`.

Example (in code):

```python
from server.services import FirestoreEpisodeProvider

provider = FirestoreEpisodeProvider()  # uses GOOGLE_APPLICATION_CREDENTIALS
state.current_episode_provider = provider
# Sessions will then use provider.get_episodes(...) and provider.get_episode_by_content_id_map()
```

## 5. Cost and limits

- **Reads:** Each session create that uses Firestore may call `get_episodes(...)` (and optionally `get_episode_by_content_id_map()`). Use `limit` and `since`/`until` so you don’t read the whole collection (e.g. last 90 days, limit 500–2000).
- **Writes:** Upload is one-time (or occasional re-sync). User engagement writes can go to the `users` collection or a subcollection later.
- Firestore [quotas and pricing](https://firebase.google.com/docs/firestore/quotas) apply.
