"""Publicación del acento de niri en la config del compositor.

El motor escribe un snippet de KDL que niri incluye desde su ``config.d``.
Así el borde de la ventana activa y el fondo del overview siguen al acento
que publica la shell, sin que nadie tenga que editar el KDL a mano.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from accent_theme.accent import (
    HEX_COLOR_PATTERN,
    RGB_CHANNEL_MAX,
    Accent,
    accent_to_hex,
)
from accent_theme.apps.base import atomic_write_text

if TYPE_CHECKING:
    from pathlib import Path


BORDER_WIDTH: Final = 2
INACTIVE_BORDER_FACTOR: Final = 0.4
URGENT_BORDER: Final = "#cc4444"
OVERVIEW_MIX: Final = 0.40
FALLBACK_OVERVIEW_COLOR: Final = "#3a3a3a"
FALLBACK_ACCENT: Final = Accent(58, 58, 58)
OVERVIEW_COLOR_PATTERN: Final = re.compile(r'backdrop-color\s+"([^"]+)"')


@dataclass(frozen=True, slots=True)
class NiriBorderColors:
    """Colores con los que niri dibuja el borde de las ventanas."""

    active: str
    inactive: str
    urgent: str


def _is_usable(accent: Accent) -> bool:
    """Indica si los canales del acento caben en un color de 8 bits."""
    return all(
        0 <= channel <= RGB_CHANNEL_MAX
        for channel in (accent.red, accent.green, accent.blue)
    )


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


def overview_backdrop_color(accent: Accent) -> str | None:
    """Devuelve el acento apagado hacia negro para el fondo del overview.

    Devuelve ``None`` si el acento no trae canales válidos, para que la
    publicación conserve el último color conocido en vez de escribir uno roto.
    """
    if not _is_usable(accent):
        return None
    return accent_to_hex(
        Accent(
            int(accent.red * OVERVIEW_MIX),
            int(accent.green * OVERVIEW_MIX),
            int(accent.blue * OVERVIEW_MIX),
        )
    )


def _published_overview_color(path: Path) -> str | None:
    """Lee el fondo del overview ya publicado para conservarlo si hace falta."""
    try:
        contents = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    match = OVERVIEW_COLOR_PATTERN.search(contents)
    if match is None:
        return None
    color = match.group(1)
    return color if HEX_COLOR_PATTERN.fullmatch(color) is not None else None


def render_border(colors: NiriBorderColors) -> str:
    """Devuelve el KDL del bloque ``border`` de niri."""
    return (
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


def render_overview_backdrop(color: str) -> str:
    """Devuelve el KDL del bloque ``overview`` de niri."""
    return (
        "overview {\n"
        f'    backdrop-color "{color}"\n'
        "}\n"
    )


def render_niri_accent(colors: NiriBorderColors, overview_color: str) -> str:
    """Devuelve el KDL completo: el borde de niri y el fondo del overview."""
    return (
        "// Generado por accent-theme: el borde y el fondo del overview de niri\n"
        "// siguen el acento de la shell.\n"
        "// No editar a mano; el motor lo reescribe en cada cambio de tema.\n"
        f"{render_border(colors)}\n"
        f"{render_overview_backdrop(overview_color)}"
    )


def write_niri_border(path: Path, accent: Accent) -> None:
    """Escribe el snippet de niri de forma atómica.

    El snippet lleva el borde de las ventanas y el fondo del overview. Si el
    acento no se puede leer, se conserva el último fondo publicado y, si no
    hay ninguno, se usa el gris de respaldo.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    overview = overview_backdrop_color(accent)
    if overview is None:
        overview = _published_overview_color(path) or FALLBACK_OVERVIEW_COLOR
    usable = accent if _is_usable(accent) else FALLBACK_ACCENT
    atomic_write_text(path, render_niri_accent(border_colors(usable), overview))
