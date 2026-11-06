"""Transformaciones de color sobre las paletas que publica el motor."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from accent_theme.accent import Accent, hsv_to_hex, rgb_to_hsv

if TYPE_CHECKING:
    from collections.abc import Mapping

HEX_COLOR_PATTERN: Final = re.compile(r"^#[0-9a-fA-F]{6}$")


def boost_saturation(document: Mapping[str, str], factor: float) -> dict[str, str]:
    """Multiplica la saturación HSV de cada color hexadecimal del documento."""
    return {key: _boost_color(value, factor) for key, value in document.items()}


def _boost_color(value: str, factor: float) -> str:
    if HEX_COLOR_PATTERN.fullmatch(value) is None:
        return value
    accent = Accent(
        int(value[1:3], 16),
        int(value[3:5], 16),
        int(value[5:7], 16),
    )
    hsv = rgb_to_hsv(accent)
    return hsv_to_hex(hsv.hue, hsv.saturation * factor, hsv.value)
