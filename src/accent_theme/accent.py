"""Lectura y conversiones del color de acento de KDE."""

from __future__ import annotations

import colorsys
import shutil
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class Accent:
    """Color RGB de 8 bits leído desde KDE."""

    red: int
    green: int
    blue: int


KDE_DEFAULT_ACCENT: Final = Accent(61, 174, 233)
RGB_CHANNEL_COUNT: Final = 3
RGB_CHANNEL_MAX: Final = 255


@dataclass(frozen=True, slots=True)
class HSV:
    """Componentes HSV normalizados."""

    hue: float
    saturation: float
    value: float


def _parse_rgb(raw: str) -> Accent | None:
    parts = [part.strip() for part in raw.split(",")]
    if len(parts) != RGB_CHANNEL_COUNT:
        return None
    try:
        channels = tuple(int(part) for part in parts)
    except ValueError:
        return None
    if any(channel < 0 or channel > RGB_CHANNEL_MAX for channel in channels):
        return None
    red, green, blue = channels
    return Accent(red, green, blue)


def _read_kde_values(path: Path) -> dict[tuple[str, str], str]:
    """Lee pares sección/clave de ``kdeglobals`` sin depender de configparser."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return {}

    values: dict[tuple[str, str], str] = {}
    section = ""
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip()
            continue
        if "=" not in stripped:
            continue
        key, raw = stripped.split("=", 1)
        values[(section, key.strip())] = raw.strip()
    return values


def read_accent(path: Path) -> Accent:
    """Lee ``AccentColor`` y usa la selección KDE como fallback."""
    values = _read_kde_values(path)
    for section, key in (
        ("General", "AccentColor"),
        ("Colors:Selection", "BackgroundNormal"),
    ):
        raw = values.get((section, key))
        if raw is None:
            continue
        parsed = _parse_rgb(raw)
        if parsed is not None:
            return parsed
    return KDE_DEFAULT_ACCENT


def read_kde_accent(path: Path, environ: Mapping[str, str]) -> Accent:
    """Lee el acento con ``kreadconfig6`` y cae al parser si no responde."""
    binary = shutil.which("kreadconfig6", path=environ.get("PATH", ""))
    if binary is not None:
        try:
            process = subprocess.run(  # noqa: S603
                [
                    binary,
                    "--file",
                    str(path),
                    "--group",
                    "General",
                    "--key",
                    "AccentColor",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                env=dict(environ),
            )
        except (OSError, subprocess.TimeoutExpired):
            process = None
        if process is not None:
            parsed = _parse_rgb(process.stdout.strip())
            if parsed is not None:
                return parsed
    return read_accent(path)


def read_explicit_accent(path: Path) -> Accent | None:
    """Lee ``AccentColor`` y devuelve ``None`` si no está definido."""
    values = _read_kde_values(path)
    raw = values.get(("General", "AccentColor"))
    if raw is None:
        return None
    return _parse_rgb(raw)


def accent_to_hex(accent: Accent) -> str:
    """Convierte un color RGB al formato hexadecimal sRGB."""
    return f"#{accent.red:02x}{accent.green:02x}{accent.blue:02x}"


def accent_to_rgb(accent: Accent) -> tuple[float, float, float]:
    """Convierte un color RGB de 8 bits a canales normalizados."""
    return (
        accent.red / 255,
        accent.green / 255,
        accent.blue / 255,
    )


def rgb_to_hsv(accent: Accent) -> HSV:
    """Convierte un color RGB a HSV normalizado."""
    hue, saturation, value = colorsys.rgb_to_hsv(*accent_to_rgb(accent))
    return HSV(hue=hue, saturation=saturation, value=value)


def hsv_to_hex(hue: float, saturation: float, value: float) -> str:
    """Convierte HSV normalizado a hexadecimal sRGB."""
    red, green, blue = colorsys.hsv_to_rgb(
        hue,
        max(0.0, min(1.0, saturation)),
        max(0.0, min(1.0, value)),
    )
    return f"#{int(red * 255):02x}{int(green * 255):02x}{int(blue * 255):02x}"


def build_palette(hue: float, saturation: float, value: float) -> dict[int, str]:
    """Construye la familia ANSI de 16 colores alrededor del acento."""
    colors: dict[int, str] = {}
    offsets = (-0.06, -0.03, 0.03, 0.06, 0.0, -0.045, 0.045, 0.0)

    for index in range(8):
        progress = index / 7
        slot_hue = (hue + offsets[index]) % 1.0
        slot_value = 0.30 + 0.55 * progress
        slot_saturation = max(saturation * 0.55, saturation - 0.05 * progress)
        colors[index] = hsv_to_hex(slot_hue, slot_saturation, slot_value)

    for index in range(8, 16):
        progress = (index - 8) / 7
        slot_hue = (hue + offsets[index - 8]) % 1.0
        slot_value = 0.55 + 0.45 * progress
        slot_saturation = max(saturation * 0.5, saturation - 0.25 * progress)
        colors[index] = hsv_to_hex(slot_hue, slot_saturation, slot_value)

    colors[4] = hsv_to_hex(hue, saturation, value)
    colors[12] = hsv_to_hex(
        hue,
        min(1.0, saturation + 0.05),
        min(1.0, value + 0.05),
    )
    return colors
