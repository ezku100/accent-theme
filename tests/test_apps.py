"""Contrato de las apps que el motor aplica tras generar la paleta.

Estas apps no son plantillas de Matugen: escriben su configuración a
mano, así que cada una tiene su propio contrato.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from accent_theme.apps.brave import apply_brave, rgb_to_skcolor
from accent_theme.apps.equibop import build_blue_shades, render_equibop_css
from accent_theme.apps.materialgram import render_materialgram
from accent_theme.apps.obs import accent_scale, render_obs_theme
from accent_theme.apps.paths import AppPaths

if TYPE_CHECKING:
    from pathlib import Path

ACCENT = "#3daee9"
PALETTE = {
    "MATUGEN_GREY": "#778899",
    "MATUGEN_BG": "#101010",
    "MATUGEN_BG_OVER": "#202020",
    "MATUGEN_BG_OVER2": "#303030",
    "MATUGEN_FG": "#f0f0f0",
    "MATUGEN_ACCENT": "#3daee9",
    "MATUGEN_ACCENT_LIGHT": "#84cfff",
    "MATUGEN_ACCENT_PRESSED": "#00658e",
}


def test_the_equibop_theme_has_five_accent_shades() -> None:
    css = render_equibop_css(ACCENT)

    for index in range(1, 6):
        assert f"--blue-{index}: oklch(" in css
    assert "--bg-1: hsla(" in css
    assert "@import url(" in css


def test_the_equibop_shades_keep_the_accent_exactly_once() -> None:
    """El tono más cercano en lightness recibe el acento sin tocar."""
    shades = build_blue_shades(0.64, 0.12, 210.0)

    assert len(shades) == 5
    assert shades[2] == (64, 0.12, 210)


def test_brave_writes_the_accent_into_the_preferences(tmp_path: Path) -> None:
    root = tmp_path / "BraveSoftware" / "Brave-Browser"
    profile = root / "Default"
    profile.mkdir(parents=True)
    (profile / "Preferences").write_text(
        json.dumps({"browser": {"theme": {}}}),
        encoding="utf-8",
    )
    (root / "Local State").write_text(
        json.dumps({"profile": {"info_cache": {"Default": {}}}}),
        encoding="utf-8",
    )

    result = apply_brave((root,), ACCENT, kdeglobals=tmp_path / "kdeglobals")

    assert result.status == "applied"
    preferences = json.loads((profile / "Preferences").read_text(encoding="utf-8"))
    expected = rgb_to_skcolor(61 / 255, 174 / 255, 233 / 255)
    assert preferences["browser"]["theme"]["user_color"] == expected
    assert preferences["browser"]["theme"]["color_scheme"] == 2
    local_state = json.loads((root / "Local State").read_text(encoding="utf-8"))
    seed = local_state["profile"]["info_cache"]["Default"]["profile_color_seed"]
    assert seed == expected


def test_brave_is_skipped_when_there_is_no_installation(tmp_path: Path) -> None:
    result = apply_brave((tmp_path / "nada",), ACCENT)

    assert result.status == "skipped"


def test_the_materialgram_template_keeps_the_variable_names() -> None:
    content = render_materialgram(
        "COLOR_PURPLE_DARK: {{matugen_accent}};\n"
        "COLOR_WHITE: {{matugen_fg}};\n"
        "windowBgOver: {{matugen_bg_over}};",
        PALETTE,
    )

    assert "COLOR_PURPLE_DARK: #3daee9;" in content
    assert "COLOR_WHITE: #f0f0f0;" in content
    assert "windowBgOver: #202020;" in content


def test_the_obs_theme_is_renamed_and_recolored() -> None:
    base = (
        "name: 'Venom';\n"
        "id: 'com.obsproject.Venom';\n"
        "author: 'FM.VENOM';\n"
        "--orange1: #ff7f50;\n"
        "--orange5: #ffb74d;\n"
        "color: #ff955b;\n"
    )

    content = render_obs_theme(base, accent_scale(0.55, 0.8, 0.9))

    assert "name: 'Dinamico';" in content
    assert "id: 'com.ezku.Dinamico';" in content
    assert "FM.VENOM" in content
    assert "#ff7f50" not in content
    assert "var(--primary)" in content


def test_the_app_paths_follow_xdg(tmp_path: Path) -> None:
    paths = AppPaths.from_environment(
        {
            "HOME": str(tmp_path),
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
        }
    )

    assert paths.equibop_theme.is_relative_to(tmp_path / "config")
    assert paths.brave_roots[0].is_relative_to(tmp_path / "config")
