"""Integraciones en vivo que recarga las apps tras generar la paleta."""

from __future__ import annotations

from typing import TYPE_CHECKING

from accent_theme.live.base import LiveResult
from accent_theme.live.cava import inject_cava
from accent_theme.live.ghostty import touch_ghostty
from accent_theme.live.kitty import reload_kitty
from accent_theme.live.millennium import sync_millennium
from accent_theme.live.paths import LivePaths
from accent_theme.live.zen import deploy_zen

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "LivePaths",
    "LiveResult",
    "apply_live_integrations",
]


def apply_live_integrations(
    paths: LivePaths,
    accent: str,
    environ: Mapping[str, str],
) -> tuple[LiveResult, ...]:
    """Ejecuta las recargas en vivo de todas las apps soportadas."""
    return (
        reload_kitty(paths.kitty_theme, paths.kitty_socket_dir, environ),
        touch_ghostty(paths.ghostty_config),
        deploy_zen(paths.zen_css, paths.zen_profile_roots),
        inject_cava(paths.cava_snippet, paths.cava_config),
        sync_millennium(
            paths.millennium_config,
            accent,
            paths.millennium_accent_file,
        ),
    )
