"""Tema CSS de EquiBop (Vencord/Equicord) teñido con el acento de KDE.

Se apoya en el tema "midnight" (por refact0r) como base: solo pisa las
variables de --accent-* / --blue-*, que colorean enlaces, botones y
resaltados, y el tinte de fondo. Los colores de estado (online, dnd, idle,
streaming) se dejan intactos porque son semánticos.
"""

from __future__ import annotations

import colorsys
import math
from typing import TYPE_CHECKING

from accent_theme.apps.base import AppResult, accent_channels, atomic_write_text

if TYPE_CHECKING:
    from pathlib import Path

MIDNIGHT_BASE_URL = "https://refact0r.github.io/midnight-discord/build/midnight.css"
LIGHTNESS_STOPS = (76, 70, 64, 58, 52)
SRGB_THRESHOLD = 0.04045


def _srgb_to_linear(channel: float) -> float:
    return (
        channel / 12.92
        if channel <= SRGB_THRESHOLD
        else ((channel + 0.055) / 1.055) ** 2.4
    )


def rgb_to_oklch(red: float, green: float, blue: float) -> tuple[float, float, float]:
    """Devuelve (L 0-1, C, H en grados) desde RGB en 0-1 (sRGB)."""
    red = _srgb_to_linear(red)
    green = _srgb_to_linear(green)
    blue = _srgb_to_linear(blue)

    lightness = 0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue
    medium = 0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue
    short = 0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue

    long_ = lightness ** (1 / 3)
    medium_ = medium ** (1 / 3)
    short_ = short ** (1 / 3)

    l_value = 0.2104542553 * long_ + 0.7936177850 * medium_ - 0.0040720468 * short_
    a_value = 1.9779984951 * long_ - 2.4285922050 * medium_ + 0.4505937099 * short_
    b_value = 0.0259040371 * long_ + 0.7827717662 * medium_ - 0.8086757660 * short_

    chroma = math.sqrt(a_value * a_value + b_value * b_value)
    hue = math.degrees(math.atan2(b_value, a_value)) % 360
    return l_value, chroma, hue


def build_blue_shades(
    accent_lightness: float,
    accent_chroma: float,
    accent_hue: float,
) -> list[tuple[int, float, int]]:
    """Genera los cinco tonos --blue-1..5 que alimentan --accent-1..5.

    Usan el hue y la chroma reales del acento, no la chroma fija (0.1) del
    tema original, que quedaba desaturada. El tono de lightness más
    cercano al del acento se reemplaza por el acento exacto, para que la
    fidelidad sea total.
    """
    chroma = max(0.08, min(accent_chroma, 0.16))
    shades = [
        (lightness, round(chroma, 3), round(accent_hue))
        for lightness in LIGHTNESS_STOPS
    ]

    accent_percent = accent_lightness * 100
    closest = min(
        range(len(LIGHTNESS_STOPS)),
        key=lambda index: abs(LIGHTNESS_STOPS[index] - accent_percent),
    )
    shades[closest] = (
        round(accent_percent),
        round(accent_chroma, 3),
        round(accent_hue),
    )
    return shades


def render_equibop_css(accent: str) -> str:
    """Devuelve el CSS del tema con los tonos del acento."""
    red, green, blue = accent_channels(accent)
    lightness, chroma, hue = rgb_to_oklch(red, green, blue)
    hue_degrees = colorsys.rgb_to_hls(red, green, blue)[0] * 360
    shades = build_blue_shades(lightness, chroma, hue)

    lines = [
        "/**",
        " * Generado automáticamente a partir del accent color de KDE.",
        " * Base: tema midnight (https://github.com/refact0r/midnight-discord)",
        " */",
        f"@import url('{MIDNIGHT_BASE_URL}');",
        "",
        ":root {",
    ]
    for index, (lightness, chroma, hue) in enumerate(shades, start=1):
        lines.append(f"    --blue-{index}: oklch({lightness}% {chroma} {hue});")

    lines += [
        "",
        f"    --bg-1: hsla({hue_degrees:.0f}, 15%, 20%, 1);",
        f"    --bg-2: hsla({hue_degrees:.0f}, 15%, 16%, 1);",
        f"    --bg-3: hsla({hue_degrees:.0f}, 15%, 13%, 1);",
        f"    --bg-4: hsla({hue_degrees:.0f}, 15%, 10%, 1);",
        "",
        "    /* Texto blanco/gris puro (sin el tinte azul del tema original) */",
        "    --text-1: hsl(0, 0%, 95%);",
        "    --text-2: hsl(0, 0%, 78%);",
        "    --text-3: hsl(0, 0%, 65%);",
        "    --text-4: hsl(0, 0%, 45%);",
        "    --text-5: hsl(0, 0%, 30%);",
        "}",
        "",
    ]
    return "\n".join(lines)


def apply_equibop(theme_path: Path, accent: str) -> AppResult:
    """Escribe el tema CSS de EquiBop con los tonos del acento."""
    try:
        atomic_write_text(theme_path, render_equibop_css(accent))
    except (OSError, ValueError) as error:
        return AppResult(app="equibop", status="failed", detail=str(error))
    return AppResult(app="equibop", status="applied", detail=str(theme_path))
