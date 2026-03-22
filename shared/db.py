"""
db.py — Simple JSON-based storage. No external database needed.
Each bot has its own data file. Everything saves automatically.
"""

import json, os
from datetime import datetime


def now() -> str:
    return datetime.now().strftime("%d %b %Y %I:%M %p")


def load(filepath: str, default: dict) -> dict:
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                d = json.load(f)
            for k, v in default.items():
                if k not in d:
                    d[k] = v
            return d
        except Exception:
            pass
    return {k: (list(v) if isinstance(v, list) else dict(v) if isinstance(v, dict) else v)
            for k, v in default.items()}


def save(filepath: str, data: dict) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
