"""Inyección en vivo del fragmento de color de Cava."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from accent_theme.live.base import LiveResult

if TYPE_CHECKING:
    from pathlib import Path

SECTION_PATTERN: Final = re.compile(r"^\s*\[([^\]]+)\]")
GENERAL_SECTION: Final = "general"
COLOR_SECTION: Final = "color"
LIVE_CONFIG_KEY: Final = "live-config"


def _parse_snippet(snippet: Path) -> dict[str, str]:
    """Lee el fragmento ``key = value`` generado por Matugen."""
    wanted: dict[str, str] = {}
    for raw_line in snippet.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        wanted[key] = value.strip("'\"")
    return wanted


def _set_key(
    lines: list[str],
    section: str,
    key: str,
    value: str,
) -> list[str]:
    """Escribe ``key = value`` dentro de ``section`` de un archivo INI."""
    key_pattern = re.compile(rf"^[;\s#]*{re.escape(key)}\s*=")
    output: list[str] = []
    in_section = False
    found_section = False
    written = False

    for line in lines:
        section_match = SECTION_PATTERN.match(line)
        if section_match is not None:
            if in_section and not written:
                output.append(f"{key} = {value}\n")
                written = True
            in_section = section_match.group(1).strip() == section
            found_section = found_section or in_section
            output.append(line)
            continue
        if in_section and key_pattern.match(line):
            if not written:
                output.append(f"{key} = {value}\n")
                written = True
            continue
        output.append(line)

    if not found_section:
        output.append(f"\n[{section}]\n{key} = {value}\n")
    elif not written:
        output.append(f"{key} = {value}\n")
    return output


def inject_cava(snippet: Path, config: Path) -> LiveResult:
    """Inyecta el fragmento de Matugen en la sección ``color`` de Cava."""
    if not snippet.is_file():
        return LiveResult(app="cava", status="skipped", detail="sin fragmento")
    if not config.is_file():
        return LiveResult(app="cava", status="skipped", detail="sin config")

    wanted = _parse_snippet(snippet)
    if not wanted:
        return LiveResult(app="cava", status="skipped", detail="fragmento vacío")

    lines = config.read_text(encoding="utf-8").splitlines(keepends=True)
    lines = _set_key(lines, GENERAL_SECTION, LIVE_CONFIG_KEY, "1")
    for key, value in wanted.items():
        lines = _set_key(lines, COLOR_SECTION, key, value)
    _ = config.write_text("".join(lines), encoding="utf-8")
    return LiveResult(
        app="cava",
        status="applied",
        detail=f"{len(wanted)} claves inyectadas",
    )
