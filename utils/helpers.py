"""Вспомогательные функции."""

from __future__ import annotations

import json
import os
from typing import Any


def load_json(path: str, default: Any = None) -> Any:
    """Загрузить JSON-файл, вернуть default при отсутствии/ошибке."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path: str, data: Any) -> None:
    """Сохранить данные в JSON-файл."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
