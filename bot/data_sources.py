"""Filesystem-backed data layer for ConfigBoost.

The bot reads ``data/servers.json`` and ``data/channel.json`` (which are
written by n8n) and persists per-user state in ``data/users.json``. Files
that are missing or malformed are replaced with safe empty defaults so
the bot never crashes because n8n has not run yet.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("configboost.data")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR = Path(os.environ.get("DATA_DIR", str(_DEFAULT_DATA_DIR)))

SERVERS_FILE = DATA_DIR / "servers.json"
CHANNEL_FILE = DATA_DIR / "channel.json"
USERS_FILE = DATA_DIR / "users.json"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_SERVERS: list[dict[str, Any]] = []
DEFAULT_CHANNEL: dict[str, str] = {"username": "", "link": ""}
DEFAULT_USERS: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_write_lock = threading.Lock()


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_write_json(path: Path, data: Any) -> None:
    _ensure_data_dir()
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", dir=str(DATA_DIR))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read %s: %s; using default", path, exc)
        return default


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ensure_files() -> None:
    """Create data files with safe defaults if they are missing."""
    _ensure_data_dir()
    if not SERVERS_FILE.exists():
        _atomic_write_json(SERVERS_FILE, DEFAULT_SERVERS)
    if not CHANNEL_FILE.exists():
        _atomic_write_json(CHANNEL_FILE, DEFAULT_CHANNEL)
    if not USERS_FILE.exists():
        _atomic_write_json(USERS_FILE, DEFAULT_USERS)


def load_servers() -> list[dict[str, Any]]:
    ensure_files()
    data = _read_json(SERVERS_FILE, DEFAULT_SERVERS)
    if isinstance(data, list):
        # Drop non-dict entries defensively.
        return [s for s in data if isinstance(s, dict)]
    return []


def load_channel() -> dict[str, str]:
    ensure_files()
    data = _read_json(CHANNEL_FILE, DEFAULT_CHANNEL)
    if isinstance(data, dict):
        return {
            "username": str(data.get("username", "")),
            "link": str(data.get("link", "")),
        }
    return DEFAULT_CHANNEL.copy()


def load_users() -> dict[str, dict[str, Any]]:
    ensure_files()
    data = _read_json(USERS_FILE, DEFAULT_USERS)
    if isinstance(data, dict):
        return data
    return {}


def save_users(users: dict[str, dict[str, Any]]) -> None:
    with _write_lock:
        _atomic_write_json(USERS_FILE, users)


def get_user(telegram_id: int) -> dict[str, Any]:
    """Return the user record, creating an empty one if it does not exist.

    The new record has ``lang=None`` until the user picks a language.
    """
    users = load_users()
    key = str(telegram_id)
    if key not in users:
        users[key] = {"lang": None, "first_seen": None, "assigned": []}
        save_users(users)
    return users[key]


def set_user_lang(telegram_id: int, lang: str) -> None:
    users = load_users()
    key = str(telegram_id)
    user = users.setdefault(
        key,
        {"lang": None, "first_seen": None, "assigned": []},
    )
    user["lang"] = lang
    if not user.get("first_seen"):
        user["first_seen"] = datetime.now(timezone.utc).isoformat()
    save_users(users)


def count_users() -> int:
    return len(load_users())