"""
User store: resolve or create users by display name (no password).
Persistence to JSON file or Firestore depending on DATA_SOURCE.
When using Firestore, document ID = normalized username (lowercase, no spaces).
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Union


def _normalize_name(name: str) -> str:
    """Normalize for use as user_id / doc id: strip and lowercase."""
    return name.strip().lower()


class UserStore(Protocol):
    """Protocol for user persistence. Implement for JSON file or Firestore."""

    def get_by_id(self, user_id: str) -> Optional[Dict]:
        """Return user dict if exists, else None."""
        ...

    def get_by_display_name(self, display_name: str) -> Optional[Dict]:
        """Return user dict if a user with this display_name exists, else None."""
        ...

    def create(self, display_name: str) -> Dict:
        """Create a new user with the given display_name. Returns the new user dict."""
        ...

    def resolve_or_create(self, display_name: str) -> Dict:
        """Return existing user with this display_name, or create and return a new one."""
        ...


class JsonUserStore:
    """User store backed by a JSON file (e.g. data/users.json)."""

    def __init__(self, path: Union[Path, str]):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._users: Dict[str, Dict] = {}
        self._by_display_name: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path) as f:
                    data = json.load(f)
                users = data.get("users", data) if isinstance(data, dict) else data
                if isinstance(users, list):
                    for u in users:
                        uid = u.get("user_id") or u.get("id")
                        if uid:
                            self._users[uid] = u
                            name = (u.get("display_name") or u.get("name") or "").strip()
                            if name:
                                self._by_display_name[name.lower()] = uid
                elif isinstance(users, dict):
                    for uid, u in users.items():
                        u["user_id"] = uid
                        self._users[uid] = u
                        name = (u.get("display_name") or u.get("name") or "").strip()
                        if name:
                            self._by_display_name[name.lower()] = uid
            except (json.JSONDecodeError, IOError):
                self._users = {}
                self._by_display_name = {}

    def _save(self) -> None:
        out = {"users": list(self._users.values())}
        with open(self._path, "w") as f:
            json.dump(out, f, indent=2)

    def get_by_id(self, user_id: str) -> Optional[Dict]:
        if user_id in self._users:
            return self._users[user_id]
        key = user_id.strip().lower()
        uid = self._by_display_name.get(key)
        return self._users.get(uid) if uid else None

    def get_by_display_name(self, display_name: str) -> Optional[Dict]:
        key = display_name.strip().lower()
        if not key:
            return None
        uid = self._by_display_name.get(key)
        return self._users.get(uid) if uid else None

    def create(self, display_name: str) -> Dict:
        name = display_name.strip()
        if not name:
            raise ValueError("display_name cannot be empty")
        user_id = str(uuid.uuid4())[:12]
        user = {"user_id": user_id, "display_name": name}
        self._users[user_id] = user
        self._by_display_name[name.lower()] = user_id
        self._save()
        return user

    def resolve_or_create(self, display_name: str) -> Dict:
        existing = self.get_by_display_name(display_name)
        if existing:
            return existing
        return self.create(display_name)


class FirestoreUserStore:
    """User store backed by Firestore 'users' collection."""

    def __init__(
        self,
        project_id: Optional[str] = None,
        credentials_path: Optional[Union[Path, str]] = None,
    ):
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore
        except ImportError:
            raise ImportError(
                "firebase-admin is required for FirestoreUserStore. pip install firebase-admin"
            )
        if not firebase_admin._apps:
            if credentials_path:
                cred = credentials.Certificate(str(Path(credentials_path).resolve()))
                opts = {"projectId": project_id} if project_id else None
                firebase_admin.initialize_app(cred, opts)
            else:
                firebase_admin.initialize_app(options={"projectId": project_id} if project_id else None)
        self._db = firestore.client()
        self._coll = self._db.collection("users")

    def _doc_to_user(self, doc) -> Dict:
        d = doc.to_dict()
        d["user_id"] = doc.id
        return d

    def get_by_id(self, user_id: str) -> Optional[Dict]:
        doc = self._coll.document(user_id).get()
        if doc.exists:
            return self._doc_to_user(doc)
        return None

    def get_by_display_name(self, display_name: str) -> Optional[Dict]:
        name = display_name.strip()
        if not name:
            return None
        user_id = _normalize_name(name)
        return self.get_by_id(user_id)

    def create(self, display_name: str) -> Dict:
        name = display_name.strip()
        if not name:
            raise ValueError("display_name cannot be empty")
        user_id = _normalize_name(name)
        user = {"user_id": user_id, "display_name": name}
        self._coll.document(user_id).set(user)
        return user

    def resolve_or_create(self, display_name: str) -> Dict:
        existing = self.get_by_display_name(display_name)
        if existing:
            return existing
        return self.create(display_name)
