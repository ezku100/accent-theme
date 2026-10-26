"""Sincronización en vivo del color de acento de Millennium."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Final, cast

from accent_theme.live.base import LiveResult

GENERAL_SECTION: Final = "general"
THEMES_SECTION: Final = "themes"
THEME_COLORS_SECTION: Final = "themeColors"
MATERIAL_THEME: Final = "Material-Theme"
ACCENT_KEY: Final = "accentColor"
CUSTOM_ACCENT_KEY: Final = "--custom-accent-color"

JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


def _load_json(path: Path) -> dict[str, JsonValue]:
    """Lee el config de Millennium como diccionario JSON tipado."""
    parsed = cast("JsonValue", json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _ensure_mapping(
    container: dict[str, JsonValue],
    key: str,
) -> dict[str, JsonValue]:
    """Devuelve el sub-diccionario de ``key`` y lo crea si falta."""
    existing = container.get(key)
    if isinstance(existing, dict):
        return existing
    created: dict[str, JsonValue] = {}
    container[key] = created
    return created


def _atomic_write(path: Path, contents: str) -> None:
    """Escribe el archivo de forma atómica."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            _ = handle.write(contents)
        _ = temporary_path.replace(path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise


def sync_millennium(config: Path, accent: str, accent_file: Path) -> LiveResult:
    """Escribe el acento en el config de Millennium y en su archivo espejo."""
    if not config.is_file():
        return LiveResult(app="millennium", status="skipped", detail="sin config")

    data = _load_json(config)
    general = _ensure_mapping(data, GENERAL_SECTION)
    general[ACCENT_KEY] = accent
    themes = _ensure_mapping(data, THEMES_SECTION)
    theme_colors = _ensure_mapping(themes, THEME_COLORS_SECTION)
    material = _ensure_mapping(theme_colors, MATERIAL_THEME)
    material[CUSTOM_ACCENT_KEY] = accent

    _atomic_write(config, json.dumps(data, indent=2) + "\n")
    _atomic_write(accent_file, f"{accent}\n")
    return LiveResult(app="millennium", status="applied", detail=accent)
