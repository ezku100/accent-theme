"""Recarga en vivo de Ghostty."""

from __future__ import annotations

from typing import TYPE_CHECKING

from accent_theme.live.base import LiveResult

if TYPE_CHECKING:
    from pathlib import Path


def touch_ghostty(config: Path) -> LiveResult:
    """Toca el config de Ghostty para que recargue el theme."""
    if not config.is_file():
        return LiveResult(app="ghostty", status="skipped", detail="sin config")
    try:
        config.touch()
    except OSError as error:
        return LiveResult(app="ghostty", status="failed", detail=str(error))
    return LiveResult(app="ghostty", status="applied", detail=str(config))
