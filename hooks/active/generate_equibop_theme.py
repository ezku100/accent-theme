#!/usr/bin/env python3
"""
Genera un theme.css para EquiBop (Vencord/Equicord) a partir del Accent
Color de KDE, en el mismo espíritu que el generador de kitty: fiel al
accent real, con buen contraste entre los tonos derivados.

Se apoya en el tema "midnight" (por refact0r) como base -- solo pisa las
variables de --accent-* / --blue-* (lo que colorea links, botones y
resaltados) y el tinte de fondo (--bg-1..4). Los colores de ESTADO
(online/dnd/idle/streaming) se dejan intactos porque son semánticos.
"""
import colorsys
import configparser
import math
import os

KDEGLOBALS = os.path.expanduser("~/.config/kdeglobals")
EQUIBOP_THEMES_DIR = os.path.expanduser("~/.config/equibop/themes")
THEME_OUT = os.path.join(EQUIBOP_THEMES_DIR, "midnight-accent-kde.theme.css")

MIDNIGHT_BASE_URL = "https://refact0r.github.io/midnight-discord/build/midnight.css"


def get_accent_rgb():
    """Lee el AccentColor de kdeglobals. Si no existe, usa un fallback."""
    _mh = os.environ.get("MATUGEN_ACCENT", "").lstrip("#")
    if len(_mh) == 6:
        try:
            return tuple(int(_mh[i:i + 2], 16) / 255 for i in (0, 2, 4))
        except ValueError:
            pass
    cfg = configparser.ConfigParser(strict=False)
    cfg.read(KDEGLOBALS)
    try:
        r, g, b = map(int, cfg["General"]["AccentColor"].split(","))
        return r / 255, g / 255, b / 255
    except (KeyError, ValueError):
        try:
            r, g, b = map(int, cfg["Colors:Selection"]["BackgroundNormal"].split(","))
            return r / 255, g / 255, b / 255
        except (KeyError, ValueError):
            return 61 / 255, 174 / 255, 233 / 255  # azul KDE por defecto


# --- Conversión sRGB -> Oklch ------------------------------------------------

def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb_to_oklch(r, g, b):
    """r,g,b en 0-1 (sRGB). Devuelve (L 0-1, C, H en grados)."""
    r, g, b = _srgb_to_linear(r), _srgb_to_linear(g), _srgb_to_linear(b)

    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    l_, m_, s_ = l ** (1 / 3), m ** (1 / 3), s ** (1 / 3)

    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b2 = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_

    C = math.sqrt(a * a + b2 * b2)
    H = math.degrees(math.atan2(b2, a)) % 360
    return L, C, H


def build_blue_shades(accent_L, accent_C, accent_H):
    """
    Genera los 5 stops --blue-1..5 (que alimentan --accent-1..5) con el
    hue y la chroma REALES del accent -- no la chroma fija (0.1) del tema
    original, que quedaba desaturada. El stop de lightness más cercano al
    del accent se reemplaza por el accent EXACTO, para que sea 100% fiel.
    """
    lightness_stops = [76, 70, 64, 58, 52]
    chroma = max(0.08, min(accent_C, 0.16))  # vívido pero dentro de gamut razonable

    shades = [(L, round(chroma, 3), round(accent_H)) for L in lightness_stops]

    accent_L_pct = accent_L * 100
    closest_idx = min(range(5), key=lambda i: abs(lightness_stops[i] - accent_L_pct))
    shades[closest_idx] = (round(accent_L_pct), round(accent_C, 3), round(accent_H))

    return shades


def main():
    r, g, b = get_accent_rgb()
    L, C, H = rgb_to_oklch(r, g, b)

    # Hue en HSL clásico, para tintar el fondo (igual que hace el tema original con 220°)
    hue_deg = colorsys.rgb_to_hls(r, g, b)[0] * 360

    blue_shades = build_blue_shades(L, C, H)

    css_lines = [
        "/**",
        " * Generado automáticamente a partir del accent color de KDE.",
        " * Base: tema midnight (https://github.com/refact0r/midnight-discord)",
        " */",
        f"@import url('{MIDNIGHT_BASE_URL}');",
        "",
        ":root {",
    ]

    for i, (L_pct, chroma, hue) in enumerate(blue_shades, start=1):
        css_lines.append(f"    --blue-{i}: oklch({L_pct}% {chroma} {hue});")

    css_lines += [
        "",
        f"    --bg-1: hsla({hue_deg:.0f}, 15%, 20%, 1);",
        f"    --bg-2: hsla({hue_deg:.0f}, 15%, 16%, 1);",
        f"    --bg-3: hsla({hue_deg:.0f}, 15%, 13%, 1);",
        f"    --bg-4: hsla({hue_deg:.0f}, 15%, 10%, 1);",
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

    os.makedirs(EQUIBOP_THEMES_DIR, exist_ok=True)
    with open(THEME_OUT, "w") as f:
        f.write("\n".join(css_lines))

    print(f"Tema de EquiBop generado en {THEME_OUT}")


if __name__ == "__main__":
    main()
