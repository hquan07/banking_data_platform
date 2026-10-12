"""Resolve runtime secrets from Docker secret files before legacy environment values."""

from __future__ import annotations

import os
from pathlib import Path


def get_secret(name: str, default: str = "", *, required: bool = False) -> str:
    file_name = os.environ.get(f"{name}_FILE", "").strip()
    if file_name:
        path = Path(file_name)
        try:
            value = path.read_text(encoding="utf-8").rstrip("\r\n")
        except OSError as exc:
            raise RuntimeError(f"Cannot read secret file for {name}: {path}") from exc
    else:
        value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required secret: {name}")
    return value


def has_secret(name: str) -> bool:
    try:
        return bool(get_secret(name))
    except RuntimeError:
        return False

