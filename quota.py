import json
import os
from pathlib import Path
from datetime import datetime

QUOTA_DIR = Path.home() / ".dorkmax"
QUOTA_FILE = QUOTA_DIR / "quota.json"
SERPER_LIMIT = 2500


def _load() -> dict:
    if not QUOTA_FILE.exists():
        return {"used": 0, "limit": SERPER_LIMIT, "reset_month": datetime.now().strftime("%Y-%m")}
    with open(QUOTA_FILE) as f:
        return json.load(f)


def _save(data: dict):
    QUOTA_DIR.mkdir(parents=True, exist_ok=True)
    with open(QUOTA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _maybe_reset(data: dict) -> dict:
    current_month = datetime.now().strftime("%Y-%m")
    if data.get("reset_month") != current_month:
        data["used"] = 0
        data["reset_month"] = current_month
    return data


def get_quota() -> tuple[int, int]:
    data = _maybe_reset(_load())
    _save(data)
    used = data.get("used", 0)
    limit = data.get("limit", SERPER_LIMIT)
    return limit - used, limit


def increment_quota(n: int = 1):
    data = _maybe_reset(_load())
    data["used"] = data.get("used", 0) + n
    _save(data)


def quota_display() -> str:
    remaining, limit = get_quota()
    return f"{remaining}/{limit}"
