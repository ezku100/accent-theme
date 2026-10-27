"""Puente de color compartido por los hooks legacy migrados.

Reexporta los helpers de ``accent_theme.accent`` con la misma firma que usaba
``~/.config/kitty/generate_theme.py``, de modo que los hooks conserven su
comportamiento sin depender de archivos propiedad de Kitty.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from accent_theme.accent import (
        accent_to_rgb,
        build_palette,
        hsv_to_hex,
        read_accent,
    )
except ModuleNotFoundError:
    _SOURCE = Path(__file__).resolve().parents[1] / "src"
    sys.path.insert(0, str(_SOURCE))
    from accent_theme.accent import (
        accent_to_rgb,
        build_palette,
        hsv_to_hex,
        read_accent,
    )

KDEGLOBALS = Path.home() / ".config" / "kdeglobals"


def get_accent_rgb() -> tuple[float, float, float]:
    """Lee el AccentColor de KDE y lo devuelve en canales normalizados."""
    return accent_to_rgb(read_accent(KDEGLOBALS))


__all__ = [
    "accent_to_rgb",
    "build_palette",
    "get_accent_rgb",
    "hsv_to_hex",
    "read_accent",
]
