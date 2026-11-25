"""Pruebas de la escritura de colores Material en KDE."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from accent_theme.kde_globals import (
    KdeGlobalsError,
    KdeGlobalsPaths,
    apply_colors,
    extract_color_block,
    merge_color_block,
    render_color_block,
    render_kcolor_scheme,
    restore_colors,
    write_kcolor_scheme,
)
from accent_theme.matugen import REQUIRED_ROLES

if TYPE_CHECKING:
    from pathlib import Path

EXISTING = """[General]
AccentColor=169,108,65
ColorScheme=OxygenDarkMono
widgetStyle=breeze

[Icons]
Theme=Tela-dark

[Colors:Window]
BackgroundNormal=44,34,29
ForegroundNormal=252,233,79

[WM]
activeBackground=1,2,3
"""


def tokens(**overrides: str) -> dict[str, str]:
    """Construye tokens con todos los roles requeridos y distintos."""
    colors: dict[str, str] = dict.fromkeys(REQUIRED_ROLES, "#123456")
    colors.update(
        surface="#101010",
        surface_container_lowest="#000000",
        surface_container_low="#111111",
        surface_container="#121212",
        surface_container_high="#131313",
        surface_container_highest="#141414",
        on_surface="#e0e0e0",
        on_surface_variant="#a0a0a0",
        primary="#3daee9",
        on_primary="#002b3d",
        secondary="#8aeeff",
        tertiary="#7fd1ff",
        error="#ff5252",
    )
    colors.update(overrides)
    return colors


def test_render_color_block_uses_rgb_triplets() -> None:
    block = render_color_block(tokens())

    assert "[Colors:Window]" in block
    assert "BackgroundNormal=16,16,16" in block
    assert "DecorationFocus=61,174,233" in block
    assert "[Colors:Selection]" in block
    assert "BackgroundNormal=61,174,233" in block
    assert "ForegroundNormal=0,43,61" in block


def test_render_color_block_rejects_a_missing_role() -> None:
    incomplete = tokens()
    del incomplete["tertiary"]

    with pytest.raises(KdeGlobalsError):
        _ = render_color_block(incomplete)


def test_extract_color_block_keeps_only_color_sections() -> None:
    block = extract_color_block(EXISTING)

    assert "[Colors:Window]" in block
    assert "BackgroundNormal=44,34,29" in block
    assert "[General]" not in block
    assert "[Icons]" not in block
    assert "[WM]" not in block


def test_merge_replaces_only_color_sections() -> None:
    merged = merge_color_block(EXISTING, render_color_block(tokens()))

    assert "AccentColor=169,108,65" in merged
    assert "Theme=Tela-dark" in merged
    assert "activeBackground=1,2,3" in merged
    assert "BackgroundNormal=44,34,29" not in merged
    assert "BackgroundNormal=16,16,16" in merged
    assert merged.count("[Colors:Window]") == 1


def test_merge_appends_the_block_when_missing() -> None:
    base = "[General]\nAccentColor=1,2,3\n"
    merged = merge_color_block(base, render_color_block(tokens()))

    assert "AccentColor=1,2,3" in merged
    assert "[Colors:Window]" in merged


def test_apply_colors_backs_up_the_original_block_once(tmp_path: Path) -> None:
    kdeglobals = tmp_path / "kdeglobals"
    _ = kdeglobals.write_text(EXISTING, encoding="utf-8")
    paths = KdeGlobalsPaths(
        kdeglobals=kdeglobals,
        backup=tmp_path / "colors.backup",
        applied=tmp_path / "colors.applied",
    )

    apply_colors(paths, tokens())
    first_backup = paths.backup.read_text(encoding="utf-8")
    apply_colors(paths, tokens(primary="#ff0000"))

    assert "BackgroundNormal=44,34,29" in first_backup
    assert paths.backup.read_text(encoding="utf-8") == first_backup
    assert "AccentColor=169,108,65" in kdeglobals.read_text(encoding="utf-8")
    assert "BackgroundNormal=255,0,0" in kdeglobals.read_text(encoding="utf-8")


def test_restore_colors_brings_back_the_original_block(tmp_path: Path) -> None:
    kdeglobals = tmp_path / "kdeglobals"
    _ = kdeglobals.write_text(EXISTING, encoding="utf-8")
    paths = KdeGlobalsPaths(
        kdeglobals=kdeglobals,
        backup=tmp_path / "colors.backup",
        applied=tmp_path / "colors.applied",
    )
    apply_colors(paths, tokens())

    restored = restore_colors(paths)

    contents = kdeglobals.read_text(encoding="utf-8")
    assert restored is True
    assert "BackgroundNormal=44,34,29" in contents
    assert "AccentColor=169,108,65" in contents
    assert not paths.applied.exists()


def test_restore_colors_respects_a_user_change(tmp_path: Path) -> None:
    kdeglobals = tmp_path / "kdeglobals"
    _ = kdeglobals.write_text(EXISTING, encoding="utf-8")
    paths = KdeGlobalsPaths(
        kdeglobals=kdeglobals,
        backup=tmp_path / "colors.backup",
        applied=tmp_path / "colors.applied",
    )
    apply_colors(paths, tokens())
    current = kdeglobals.read_text(encoding="utf-8")
    _ = kdeglobals.write_text(
        current.replace("BackgroundNormal=16,16,16", "BackgroundNormal=9,9,9"),
        encoding="utf-8",
    )

    restored = restore_colors(paths)

    assert restored is False
    assert "BackgroundNormal=9,9,9" in kdeglobals.read_text(encoding="utf-8")


def test_restore_colors_without_backup_is_a_noop(tmp_path: Path) -> None:
    paths = KdeGlobalsPaths(
        kdeglobals=tmp_path / "kdeglobals",
        backup=tmp_path / "colors.backup",
        applied=tmp_path / "colors.applied",
    )

    assert restore_colors(paths) is False


def test_render_kcolor_scheme_has_general_and_colors() -> None:
    scheme = render_kcolor_scheme(tokens())

    assert "ColorScheme=Matugen" in scheme
    assert "[Colors:Window]" in scheme
    assert "BackgroundNormal=16,16,16" in scheme


def test_write_kcolor_scheme_creates_the_file(tmp_path: Path) -> None:
    target = tmp_path / "Matugen.colors"

    write_kcolor_scheme(target, tokens())

    scheme = target.read_text(encoding="utf-8")
    assert "ColorScheme=Matugen" in scheme
    assert "[Colors:Selection]" in scheme


def test_apply_colors_keeps_the_rest_of_kdeglobals(
    tmp_path: Path,
) -> None:
    kdeglobals = tmp_path / "kdeglobals"
    _ = kdeglobals.write_text(EXISTING, encoding="utf-8")
    paths = KdeGlobalsPaths(
        kdeglobals=kdeglobals,
        backup=tmp_path / "colors.backup",
        applied=tmp_path / "colors.applied",
    )

    apply_colors(paths, tokens())

    contents = kdeglobals.read_text(encoding="utf-8")
    for line in ("AccentColor=169,108,65", "widgetStyle=breeze", "Theme=Tela-dark"):
        assert line in contents
