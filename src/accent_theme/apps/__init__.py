"""Integraciones de apps que el motor aplica tras generar la paleta.

Estas apps no encajan en una plantilla de Matugen: escriben su
configuración en sitios donde una plantilla no llega, como un JSON que hay
que fusionar con lo que ya había o un tema que se deriva de otro archivo.
El motor las aplica desde aquí, con el acento y la paleta ya calculados.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from accent_theme.accent import accent_to_hex, rgb_to_hsv
from accent_theme.apps.base import AppResult
from accent_theme.apps.brave import apply_brave
from accent_theme.apps.equibop import apply_equibop
from accent_theme.apps.materialgram import apply_materialgram
from accent_theme.apps.obs import apply_obs
from accent_theme.apps.paths import AppPaths

if TYPE_CHECKING:
    from collections.abc import Mapping

    from accent_theme.accent import Accent

__all__ = [
    "AppPaths",
    "AppResult",
    "apply_app_integrations",
]


def apply_app_integrations(
    paths: AppPaths,
    accent: Accent,
    palette: Mapping[str, str],
) -> tuple[AppResult, ...]:
    """Aplica el tema de las apps que no son plantillas de Matugen."""
    hsv = rgb_to_hsv(accent)
    return (
        apply_brave(paths.brave_roots, accent_to_hex(accent)),
        apply_equibop(paths.equibop_theme, accent_to_hex(accent)),
        apply_materialgram(
            paths.materialgram_template,
            paths.materialgram_themes,
            palette,
        ),
        apply_obs(
            paths.obs_base,
            paths.obs_themes,
            hsv,
            paths.obs_base_fallback,
        ),
    )
