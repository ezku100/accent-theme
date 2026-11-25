"""Estado JSON publicado por el motor de tema."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast

from accent_theme.apps.base import atomic_write_json

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from accent_theme.sources.models import SourceKind

HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
ThemeStatus = Literal["ok", "error"]


@dataclass(frozen=True, slots=True)
class ThemeState:
    """Estado mínimo de la última generación de tema correcta."""

    source: SourceKind
    reference: str
    wallpaper_id: str | None
    source_color: str
    generated_at: str
    status: ThemeStatus = "ok"


def state_document(state: ThemeState) -> dict[str, object]:
    """Convierte el estado interno al contrato JSON externo."""
    return {
        "source": state.source,
        "reference": state.reference,
        "wallpaperId": state.wallpaper_id,
        "sourceColor": state.source_color,
        "generatedAt": state.generated_at,
        "status": state.status,
    }


def write_state(path: Path, state: ThemeState) -> None:
    """Publica el estado de forma atómica."""
    atomic_write_json(path, state_document(state))


def _is_source_kind(value: object) -> bool:
    return value in {"kde", "waywallen"}


def _is_status(value: object) -> bool:
    return value in {"ok", "error"}


def _string_field(document: Mapping[str, object], key: str) -> str | None:
    value = document.get(key)
    if not isinstance(value, str):
        return None
    return value


def read_state(path: Path) -> ThemeState | None:
    """Lee y valida el estado; devuelve ``None`` si el documento no es válido."""
    try:
        raw = cast("object", json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None

    if not isinstance(raw, dict):
        return None
    document = cast("dict[str, object]", raw)

    source = document.get("source")
    reference = _string_field(document, "reference")
    wallpaper_id = document.get("wallpaperId")
    source_color = _string_field(document, "sourceColor")
    generated_at = _string_field(document, "generatedAt")
    status = document.get("status")

    if (
        not _is_source_kind(source)
        or reference is None
        or (wallpaper_id is not None and not isinstance(wallpaper_id, str))
        or source_color is None
        or HEX_COLOR_PATTERN.fullmatch(source_color) is None
        or generated_at is None
        or not _is_status(status)
    ):
        return None

    return ThemeState(
        source=cast("SourceKind", source),
        reference=reference,
        wallpaper_id=wallpaper_id,
        source_color=source_color,
        generated_at=generated_at,
        status=cast("ThemeStatus", status),
    )
