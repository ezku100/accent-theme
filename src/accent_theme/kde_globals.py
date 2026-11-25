"""Escritura de los colores Material en kdeglobals y KColorScheme.

Qt bajo Plasma lee los colores de ``kdeglobals`` y los esquemas de color de
``KColorScheme``. Este módulo traduce la paleta Material a tripletas
``r,g,b`` y fusiona sólo las secciones ``[Colors:*]``: el resto del archivo
—``AccentColor``, iconos, estilo de widgets— se conserva intacto.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from accent_theme.apps.base import atomic_write_text

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

COLOR_SECTION_PREFIX: Final = "[Colors:"
SCHEME_NAME: Final = "Matugen"
HEX_PATTERN: Final = re.compile(r"^#[0-9a-fA-F]{6}$")


class KdeGlobalsError(RuntimeError):
    """Paleta o color que no se puede publicar en KDE."""

    @classmethod
    def missing_role(cls, role: str) -> KdeGlobalsError:
        """Construye el error de un rol ausente en la paleta."""
        return cls(f"falta el rol {role} en la paleta Material")

    @classmethod
    def invalid_color(cls, value: str) -> KdeGlobalsError:
        """Construye el error de un color que no es hexadecimal."""
        return cls(f"color no válido: {value}")


def _spec(
    background: str,
    alternate: str,
    *,
    foreground: str = "on_surface",
    accent: str = "primary",
    inverse: bool = False,
) -> dict[str, str]:
    """Construye la especificación de una sección ``[Colors:*]``."""
    inactive = "on_primary" if inverse else "on_surface_variant"
    return {
        "BackgroundNormal": background,
        "BackgroundAlternate": alternate,
        "ForegroundNormal": foreground,
        "ForegroundInactive": inactive,
        "ForegroundActive": accent,
        "ForegroundLink": accent,
        "ForegroundVisited": accent if inverse else "tertiary",
        "ForegroundNegative": accent if inverse else "error",
        "ForegroundNeutral": accent if inverse else "secondary",
        "ForegroundPositive": accent if inverse else "tertiary",
        "DecorationFocus": accent,
        "DecorationHover": accent,
    }


SECTION_SPECS: Final[dict[str, dict[str, str]]] = {
    "Colors:Window": _spec("surface", "surface_container_low"),
    "Colors:View": _spec("surface_container_lowest", "surface_container_low"),
    "Colors:Button": _spec("surface_container", "surface_container_high"),
    "Colors:Selection": _spec(
        "primary",
        "primary",
        foreground="on_primary",
        accent="on_primary",
        inverse=True,
    ),
    "Colors:Tooltip": _spec("surface_container_highest", "surface_container_high"),
    "Colors:Complementary": _spec(
        "surface_container_high",
        "surface_container_highest",
    ),
    "Colors:Header": _spec("surface_container_low", "surface_container"),
}


def _color(tokens: Mapping[str, str], role: str) -> str:
    """Extrae un rol obligatorio de la paleta."""
    value = tokens.get(role)
    if value is None:
        raise KdeGlobalsError.missing_role(role)
    return value


def _rgb(hex_color: str) -> str:
    """Convierte ``#rrggbb`` en la tripleta ``r,g,b`` que usa KDE."""
    if HEX_PATTERN.fullmatch(hex_color) is None:
        raise KdeGlobalsError.invalid_color(hex_color)
    red = int(hex_color[1:3], 16)
    green = int(hex_color[3:5], 16)
    blue = int(hex_color[5:7], 16)
    return f"{red},{green},{blue}"


def render_color_block(tokens: Mapping[str, str]) -> str:
    """Renderiza todas las secciones ``[Colors:*]`` con la paleta dada."""
    blocks: list[str] = []
    for section, spec in SECTION_SPECS.items():
        body = "\n".join(
            f"{key}={_rgb(_color(tokens, role))}" for key, role in spec.items()
        )
        blocks.append(f"[{section}]\n{body}")
    return "\n\n".join(blocks) + "\n"


def render_kcolor_scheme(tokens: Mapping[str, str]) -> str:
    """Renderiza un archivo ``.colors`` completo para KColorScheme."""
    header = f"[General]\nColorScheme={SCHEME_NAME}\nName={SCHEME_NAME}\n"
    return f"{header}\n{render_color_block(tokens)}"


@dataclass(slots=True)
class _Section:
    """Sección de un archivo INI: encabezado y líneas crudas."""

    header: str | None = None
    lines: list[str] = field(default_factory=list)


def _parse(text: str) -> list[_Section]:
    """Divide un INI conservando cada línea tal cual."""
    sections = [_Section()]
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            sections.append(_Section(header=stripped))
        else:
            sections[-1].lines.append(raw_line)
    return sections


def _serialize(sections: list[_Section]) -> str:
    """Reconstruye el texto de un INI."""
    output: list[str] = []
    for section in sections:
        if section.header is not None:
            output.append(section.header)
        output.extend(section.lines)
    return "\n".join(output) + ("\n" if output else "")


def _is_color_section(section: _Section) -> bool:
    """Indica si la sección pertenece al bloque de colores."""
    return section.header is not None and section.header.startswith(
        COLOR_SECTION_PREFIX,
    )


def extract_color_block(text: str) -> str:
    """Devuelve sólo las secciones ``[Colors:*]`` de un INI."""
    color_sections = [
        section for section in _parse(text) if _is_color_section(section)
    ]
    return _serialize(color_sections)


def merge_color_block(existing: str, block: str) -> str:
    """Sustituye las secciones de color del INI por las del bloque."""
    rendered = [section for section in _parse(block) if _is_color_section(section)]
    merged: list[_Section] = []
    inserted = False
    for section in _parse(existing):
        if not _is_color_section(section):
            merged.append(section)
        elif not inserted:
            merged.extend(rendered)
            inserted = True
    if not inserted:
        merged.extend(rendered)
    return _serialize(merged)


@dataclass(frozen=True, slots=True)
class KdeGlobalsPaths:
    """Archivo de KDE junto a la copia de seguridad y la última escritura."""

    kdeglobals: Path
    backup: Path
    applied: Path


def _read_text(path: Path) -> str:
    """Lee un archivo de texto y trata su ausencia como vacío."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def apply_colors(paths: KdeGlobalsPaths, tokens: Mapping[str, str]) -> None:
    """Escribe la paleta en ``kdeglobals`` guardando el bloque original.

    El bloque original sólo se refresca cuando el bloque actual no es el
    que escribimos: si Plasma o el usuario cambian el esquema, la copia de
    seguridad pasa a ser el nuevo original y la restauración no lo pisa.
    """
    block = render_color_block(tokens)
    current = _read_text(paths.kdeglobals)
    previous_applied = _read_text(paths.applied).strip()
    if extract_color_block(current).strip() != previous_applied:
        atomic_write_text(paths.backup, extract_color_block(current))
    atomic_write_text(paths.kdeglobals, merge_color_block(current, block))
    atomic_write_text(paths.applied, block)


def restore_colors(paths: KdeGlobalsPaths) -> bool:
    """Devuelve ``kdeglobals`` a su esquema original.

    Si el bloque de colores ya no es el que escribimos —porque el usuario
    cambió de esquema— no se toca nada y se devuelve ``False``.
    """
    if not paths.backup.is_file():
        return False
    original = _read_text(paths.backup)
    current = _read_text(paths.kdeglobals)
    applied = _read_text(paths.applied).strip()
    if applied and extract_color_block(current).strip() != applied:
        return False
    atomic_write_text(paths.kdeglobals, merge_color_block(current, original))
    paths.applied.unlink(missing_ok=True)
    return True


def write_kcolor_scheme(path: Path, tokens: Mapping[str, str]) -> None:
    """Publica un ``.colors`` con la paleta Material."""
    atomic_write_text(path, render_kcolor_scheme(tokens))
