"""Contrato de la migración de hooks legacy fuera de los archivos de Kitty."""

from __future__ import annotations

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_HOOKS = REPOSITORY_ROOT / "hooks" / "active"
SUPPORT_HOOKS = REPOSITORY_ROOT / "hooks" / "support"
FORBIDDEN_IMPORTS = ("from generate_theme import", "import generate_theme")
KITTY_OWNED_PATHS = ("~/.config/kitty", "/.config/kitty")


def hook_files(directory: Path) -> tuple[Path, ...]:
    """Devuelve los hooks Python de un directorio en orden determinista."""
    return tuple(sorted(directory.glob("*.py")))


def test_active_hooks_do_not_import_kitty_generate_theme() -> None:
    assert hook_files(ACTIVE_HOOKS), "no hay hooks activos migrados"

    offenders = [
        hook.name
        for hook in hook_files(ACTIVE_HOOKS)
        if any(
            forbidden in hook.read_text(encoding="utf-8")
            for forbidden in FORBIDDEN_IMPORTS
        )
    ]

    assert offenders == []


def test_support_hooks_do_not_import_kitty_generate_theme() -> None:
    offenders = [
        hook.name
        for hook in hook_files(SUPPORT_HOOKS)
        if any(
            forbidden in hook.read_text(encoding="utf-8")
            for forbidden in FORBIDDEN_IMPORTS
        )
    ]

    assert offenders == []


def test_no_hook_references_kitty_owned_paths() -> None:
    offenders = [
        hook.name
        for hook in hook_files(ACTIVE_HOOKS) + hook_files(SUPPORT_HOOKS)
        if any(
            owned in hook.read_text(encoding="utf-8")
            for owned in KITTY_OWNED_PATHS
        )
    ]

    assert offenders == []


def test_color_helpers_come_from_the_shared_bridge() -> None:
    consumers: list[Path] = []
    for hook in hook_files(ACTIVE_HOOKS) + hook_files(SUPPORT_HOOKS):
        source = hook.read_text(encoding="utf-8")
        if "get_accent_rgb" not in source:
            continue
        if "def get_accent_rgb" in source:
            continue
        consumers.append(hook)

    assert consumers, "ningún hook consume los helpers de color"
    offenders = [
        hook.name
        for hook in consumers
        if "from bridge import" not in hook.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_self_contained_hooks_keep_their_own_accent_reader() -> None:
    equibop = ACTIVE_HOOKS / "generate_equibop_theme.py"
    source = equibop.read_text(encoding="utf-8")

    assert "def get_accent_rgb" in source
    assert "MATUGEN_ACCENT" in source
    assert "from bridge import" not in source


def test_noctalia_uses_the_bundled_pacman_support_script() -> None:
    noctalia = ACTIVE_HOOKS / "generate_noctalia_theme.py"
    contents = noctalia.read_text(encoding="utf-8")

    assert "generate_pacman_assets.py" in contents
    assert '"support"' in contents
    assert ".config/kitty" not in contents


def test_bridge_exposes_the_legacy_helper_surface() -> None:
    bridge = (REPOSITORY_ROOT / "hooks" / "bridge.py").read_text(encoding="utf-8")

    for helper in ("get_accent_rgb", "hsv_to_hex", "build_palette"):
        assert helper in bridge
