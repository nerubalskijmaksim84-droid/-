"""profile.py

Player profile persistence based on JSON.
Stores coins, owned items, and selected cosmetics/options.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

PROFILE_FILE = Path("player_profile.json")


def default_profile() -> Dict[str, Any]:
    return {
        "name": "Player",
        "coins": 300,
        "bot_coins": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "owned_boards": ["classic"],
        "owned_piece_skins": ["classic"],
        "owned_themes": ["light"],
        "unlocked_difficulties": [1, 2],
        "selected_board": "classic",
        "selected_piece_skin": "classic",
        "selected_theme": "light",
        "selected_difficulty": 2,
    }


def load_profile(path: Path = PROFILE_FILE) -> Dict[str, Any]:
    """Load profile from JSON (create default when missing/corrupt)."""
    if not path.exists():
        data = default_profile()
        save_profile(data, path)
        return data

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        data = default_profile()
        save_profile(data, path)
        return data

    # Fill missing keys for backward compatibility
    base = default_profile()
    for k, v in base.items():
        data.setdefault(k, v)

    return data


def save_profile(data: Dict[str, Any], path: Path = PROFILE_FILE) -> None:
    """Persist profile JSON with UTF-8 and readable indentation."""
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
