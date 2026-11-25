"""Publicación del borde de niri con el color de acento de la shell.

El motor escribe un snippet de KDL que niri incluye desde su ``config.d``.
Así el borde de la ventana activa sigue al acento que publica la shell, sin
que nadie tenga que editar el KDL a mano.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from accent_theme.accent import Accent, accent_to_hex
from accent_theme.apps.base import atomic_write_text

if TYPE_CHECKING:
    from pathlib import Path


BORDER_WIDTH: Final = 4
INACTIVE_BORDER_FACTOR: Final = 0.4
URGENT_BORDER: Final = "#cc4444"


@dataclass(frozen=True, slots=True)
class NiriBorderColors:
    """Colores con los que niri dibuja el borde de las ventanas."""

    active: str
    inactive: str
    urgent: str


def _dimmed(accent: Accent, factor: float) -> str:
    """Apaga un color mezclándolo con negro, sin salirse de su familia."""
    return accent_to_hex(
        Accent(
            round(accent.red * factor),
            round(accent.green * factor),
            round(accent.blue * factor),
        )
    )


def border_colors(accent: Accent) -> NiriBorderColors:
    """Deriva los colores del borde a partir del acento de la shell."""
    return NiriBorderColors(
        active=accent_to_hex(accent),
        inactive=_dimmed(accent, INACTIVE_BORDER_FACTOR),
        urgent=URGENT_BORDER,
    )


def render_border(colors: NiriBorderColors) -> str:
    """Devuelve el KDL del bloque ``border`` de niri."""
    return (
        "// Generado por accent-theme: el borde de niri sigue el acento de la shell.\n"
        "// No editar a mano; el motor lo reescribe en cada cambio de tema.\n"
        "layout {\n"
        "    border {\n"
        "        on\n"
        f"        width {BORDER_WIDTH}\n"
        f'        active-color "{colors.active}"\n'
        f'        inactive-color "{colors.inactive}"\n'
        f'        urgent-color "{colors.urgent}"\n'
        "    }\n"
        "}\n"
    )


def write_niri_border(path: Path, accent: Accent) -> None:
    """Escribe el snippet del borde de niri de forma atómica."""
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, render_border(border_colors(accent)))
