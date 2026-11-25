"""Pruebas del contrato JSON de estado del tema."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from accent_theme.state import ThemeState, read_state, state_document, write_state

if TYPE_CHECKING:
    from pathlib import Path


def _state() -> ThemeState:
    return ThemeState(
        source="waywallen",
        reference="27",
        wallpaper_id="27",
        source_color="#ec1413",
        generated_at="2026-11-23T20:00:00Z",
    )


def test_state_document_uses_external_keys() -> None:
    document = state_document(_state())

    assert document == {
        "source": "waywallen",
        "reference": "27",
        "wallpaperId": "27",
        "sourceColor": "#ec1413",
        "generatedAt": "2026-11-23T20:00:00Z",
        "status": "ok",
    }


def test_write_state_creates_parent_and_json(tmp_path: Path) -> None:
    path = tmp_path / "cache" / "accent-theme" / "niri-state.json"

    write_state(path, _state())

    assert json.loads(path.read_text(encoding="utf-8")) == state_document(_state())


def test_read_state_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "niri-state.json"

    write_state(path, _state())

    assert read_state(path) == _state()


def test_read_state_returns_none_for_missing_file(tmp_path: Path) -> None:
    assert read_state(tmp_path / "missing.json") is None


def test_read_state_returns_none_for_invalid_payload(tmp_path: Path) -> None:
    path = tmp_path / "niri-state.json"
    _ = path.write_text(
        json.dumps({"source": "unknown", "status": "ok"}),
        encoding="utf-8",
    )

    assert read_state(path) is None
