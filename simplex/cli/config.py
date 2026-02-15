"""Credential storage and API key resolution."""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

CREDENTIALS_DIR = Path.home() / ".simplex"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials"


def _ensure_credentials_dir() -> None:
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)


def save_api_key(api_key: str) -> None:
    """Save API key to ~/.simplex/credentials with restricted permissions."""
    _ensure_credentials_dir()
    CREDENTIALS_FILE.write_text(json.dumps({"api_key": api_key}))
    try:
        CREDENTIALS_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600
    except OSError:
        pass  # Windows doesn't support Unix permissions


def load_api_key() -> str | None:
    """Load API key from credentials file."""
    if not CREDENTIALS_FILE.exists():
        return None
    try:
        data = json.loads(CREDENTIALS_FILE.read_text())
        return data.get("api_key")
    except (json.JSONDecodeError, OSError):
        return None


def delete_credentials() -> bool:
    """Delete credentials file. Returns True if file existed."""
    if CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()
        return True
    return False


def resolve_api_key() -> str:
    """Resolve API key from env var or credentials file.

    Order: SIMPLEX_API_KEY env var → ~/.simplex/credentials file.
    Exits with error message if neither is found.
    """
    key = os.environ.get("SIMPLEX_API_KEY") or load_api_key()
    if not key:
        from rich.console import Console

        Console(stderr=True).print(
            "[red]Not authenticated. Run 'simplex login' or set SIMPLEX_API_KEY.[/red]"
        )
        raise SystemExit(1)
    return key


def resolve_base_url() -> str | None:
    """Resolve base URL from env var. Returns None to use SDK default."""
    return os.environ.get("SIMPLEX_BASE_URL") or None


def make_client_kwargs() -> dict:
    """Return kwargs dict for SimplexClient with api_key and optional base_url."""
    kwargs: dict = {"api_key": resolve_api_key()}
    base_url = resolve_base_url()
    if base_url:
        kwargs["base_url"] = base_url
    return kwargs


def get_api_key_source() -> tuple[str, str] | None:
    """Return (masked_key, source) or None if no key found."""
    env_key = os.environ.get("SIMPLEX_API_KEY")
    if env_key:
        return _mask_key(env_key), "SIMPLEX_API_KEY environment variable"
    file_key = load_api_key()
    if file_key:
        return _mask_key(file_key), "~/.simplex/credentials"
    return None


SESSIONS_DIR = CREDENTIALS_DIR / "sessions"


def save_session(workflow_id: str, session_id: str, name: str, url: str) -> None:
    """Save a session to ~/.simplex/sessions/<workflow_id>.json."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    (SESSIONS_DIR / f"{workflow_id}.json").write_text(json.dumps({
        "workflow_id": workflow_id,
        "session_id": session_id,
        "name": name,
        "url": url,
    }))


def resolve_session(target: str) -> dict | None:
    """Resolve a target to a saved session.

    Matches against (in order):
      1. Workflow name (case-insensitive substring)
      2. Workflow ID prefix
    """
    if not SESSIONS_DIR.exists():
        return None
    sessions = list_sessions()
    # 1. Match by name (case-insensitive substring)
    target_lower = target.lower()
    for s in sessions:
        if target_lower in s.get("name", "").lower():
            return s
    # 2. Match by workflow ID prefix
    for s in sessions:
        if s.get("workflow_id", "").startswith(target):
            return s
    return None


def list_sessions() -> list[dict]:
    """List all saved sessions, most recent first."""
    if not SESSIONS_DIR.exists():
        return []
    sessions = []
    for f in sorted(SESSIONS_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            sessions.append(json.loads(f.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    return sessions


def remove_session(workflow_id: str) -> bool:
    """Remove a saved session file."""
    f = SESSIONS_DIR / f"{workflow_id}.json"
    if f.exists():
        f.unlink()
        return True
    return False


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return key[:2] + "*" * (len(key) - 2)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]
