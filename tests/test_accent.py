from __future__ import annotations

from typing import TYPE_CHECKING

from accent_theme.accent import Accent, accent_to_hex, read_accent

if TYPE_CHECKING:
    from pathlib import Path


def test_read_accent_uses_general_accent_color(tmp_path: Path) -> None:
    config = tmp_path / "kdeglobals"
    _ = config.write_text(
        "[General]\nAccentColor=61,174,233\n\n[Colors:Selection]\nBackgroundNormal=255,0,0\n",
        encoding="utf-8",
    )

    assert read_accent(config) == Accent(61, 174, 233)


def test_read_accent_falls_back_to_selection_background(tmp_path: Path) -> None:
    config = tmp_path / "kdeglobals"
    _ = config.write_text(
        "[Colors:Selection]\nBackgroundNormal=12,34,56\n",
        encoding="utf-8",
    )

    assert read_accent(config) == Accent(12, 34, 56)


def test_read_accent_uses_kde_blue_when_values_are_invalid(tmp_path: Path) -> None:
    config = tmp_path / "kdeglobals"
    _ = config.write_text(
        "[General]\nAccentColor=not-a-color\n",
        encoding="utf-8",
    )

    assert read_accent(config) == Accent(61, 174, 233)


def test_accent_to_hex_returns_lowercase_srgb() -> None:
    assert accent_to_hex(Accent(61, 174, 233)) == "#3daee9"
