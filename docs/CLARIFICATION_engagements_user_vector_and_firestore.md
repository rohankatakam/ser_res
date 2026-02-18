# Clarification: User Vector, Engagements for Session vs User, and Firestore Shape

This doc answers:

1. How the user vector is computed and when it is "recalculated" in the cloud.
2. The difference between "engagements for a session" and "engagements for the user" — and what we should use for ranking.
3. Whether to store engagements per-session or per-user in Firestore, and how that fits the plan.

---

## 1. How the user vector is computed (and when it’s “recalculated”)

**Where it happens:** [algorithm/stages/ranking/user_vector.py](algorithm/stages/ranking/user_vector.py) — `get_user_vector_mean(engagements, embeddings, episode_by_content_id, config)`.

**What it does:**

- Takes a **list of engagements** (each has `episode_id`, `type`, `timestamp`).
- Uses [engagement_embeddings.py](algorithm/stages/ranking/engagement_embeddings.py) to get **recent** engagement–embedding pairs: sorts by `timestamp` (newest first), takes up to `user_vector_limit` (default 10), and resolves each `episode_id` to an embedding.
- Computes a single vector by **mean-pooling** (or weighted mean if `use_weighted_engagements` is true) over those embeddings.
- Returns that vector or `None` if there are no valid pairs.

**Important:** The algorithm does **not** store the user vector anywhere. It is computed **on demand** every time we call `create_recommendation_queue` → `rank_candidates` → `get_user_vector_mean`. There is no “recalculation” step inside the algorithm; the only input is the engagements list passed in.

**So “recalculation when a new engagement is made” means:**

- When the user makes a new engagement, we **persist** it (e.g. Firestore).
- The **next** time we **create a session** (or refresh), we pass an **updated engagements list** (from Firestore) into `create_recommendation_queue`.
- The algorithm then computes the user vector from that updated list. No separate “recompute user vector” API is needed; “create session” with the latest engagements is the recalculation.

**Cloud adherence:** As long as the backend passes the **current, full (or recent) engagements for that user** from Firestore when creating a session, the user vector will automatically reflect new engagements. No change is required inside `user_vector.py` for the new cloud infra.

---

## 2. “Engagements for a session” vs “engagements for the user”

**Current API name:** `get_engagements_for_session(user_id, request_engagements)`.

**What it’s really for:** Deciding **which engagements to use when building the user vector and running ranking** for this request. So it’s “engagements to use for **this** session create,” not “engagements that belong to a specific session.”

**Two possible semantics:**

| Option | Meaning | Use case |
|--------|--------|----------|
| **A) Engagements for the *current* session** | Only engagements that happened in the “current” browsing/recommendation session (e.g. since last “Refresh” or since page load). | Would limit the user vector to a short window. |
| **B) All engagements for the *user*** | All (or recent) engagements for that user, across all time and all sessions. | Matches algorithm design: user vector = mean of **recent** engagements (up to `user_vector_limit`). |

**Recommendation: B — use all (or recent) engagements for the user.**

- The algorithm already limits to the most recent `user_vector_limit` (10) engagements by timestamp ([engagement_embeddings.py](algorithm/stages/ranking/engagement_embeddings.py)).
- So we should pass **all engagements for the user** (or a capped recent list, e.g. last 500) from Firestore into `get_engagements_for_session` when `user_id` is set. The algorithm will then take the 10 most recent and build the user vector.
- “Session” in the method name is historical: it means “engagements to use when creating **this** recommendation session,” not “engagements that belong to session X.”

**Optional rename:** To avoid confusion, we could rename to something like `get_engagements_for_ranking(user_id, request_engagements)` and document: “Returns engagements to use for ranking (when user_id is set: all/recent engagements for that user from Firestore).”

---

## 3. Firestore: store engagements per user, not per session

**Your assumption:** “We will be storing in our Firestore engagements table each session and in each session the engagements in the session.”

**Recommendation:** Do **not** store “sessions” in Firestore for engagements. Store **one list of engagements per user**.

**Why:**

- For ranking we need **all (or recent) engagements for the user** to build the user vector. If we stored engagements per-session, we’d have to query **all** sessions for that user and merge engagements every time we create a new session. That’s more complex and doesn’t match the algorithm (which expects a single list sorted by time).
- A “session” in our app is a **recommendation session**: a precomputed queue + pagination state. It’s already stored in **server memory** (e.g. `state.sessions[session_id]`). We don’t need to persist that queue to Firestore for the recommendation or engagement logic.
- So:
  - **Firestore:** Persist **engagements per user** only: e.g. `users/{user_id}/engagements` (subcollection). Each doc = one engagement: `{ episode_id, type, timestamp }`.
  - **Server:** Keep **sessions** in memory (or Redis) as today: session_id → queue, shown_indices, engaged_ids, etc. No “sessions” collection in Firestore for this.

**Concrete Firestore shape:**

- **Collection (or subcollection):** `users/{user_id}/engagements`
- **Document:** e.g. auto-id or `episode_id + "_" + timestamp`
- **Fields:** `episode_id`, `type`, `timestamp`
- **No** `sessions` collection for engagement storage. When we create a session we read from `users/{user_id}/engagements` (e.g. order by timestamp desc, limit 500) and pass that list to the algorithm.

**When a new user is created:** We don’t need to create an “engagements” document. The subcollection is created when the first engagement is written. So no extra “create engagements table” step on user create.

---

## 4. Summary for the plan

- **User vector:** Computed on the fly from the engagements list passed to `create_recommendation_queue`. Recalculation = “next session create uses updated engagements from Firestore.” No algorithm change.
- **get_engagements_for_session:** Should return **all (or recent) engagements for the user** when `user_id` is set, so the user vector reflects full/recent history. Optional rename to `get_engagements_for_ranking` and document clearly.
- **Firestore:** Store engagements **per user** in `users/{user_id}/engagements`. Do **not** store sessions or per-session engagement lists in Firestore for this flow. Sessions remain server-side (in-memory/Redis).

Once this is agreed, the implementation plan (Pinecone + Firestore engagements + Reset, etc.) can use this semantics and storage model consistently.
