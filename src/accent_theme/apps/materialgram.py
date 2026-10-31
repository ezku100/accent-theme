"""Tema ``Dinamico.tdesktop-theme`` para Materialgram (Telegram Desktop).

Base: tema "SolidDark" de MasterGroosha (MIT), cuya cabecera y atribución
se conservan. Solo se sustituyen los colores de acento y fondo por los
del acento de KDE; los colores semánticos (estados de los contactos,
errores) se dejan intactos.

Importación (una vez): enviar ``~/Documents/Dinamico.tdesktop-theme`` a
"Mensajes guardados", tocar la burbuja -> Aplicar. Telegram no recarga el
fichero en vivo: tras cada cambio de acento hay que re-tocar "Dinamico" en
la lista de temas.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from accent_theme.apps.base import AppResult, atomic_write_text

if TYPE_CHECKING:
    from collections.abc import Mapping

TEMPLATE_NAME = "materialgram.tdesktop-theme"


def _template_path(installed: Path) -> Path:
    """Devuelve la plantilla, desde la instalación o desde el repo."""
    candidate = installed
    if candidate.is_file():
        return candidate
    repository = Path(__file__).resolve().parents[3]
    return repository / "templates" / "materialgram" / TEMPLATE_NAME


def render_materialgram(template: str, palette: Mapping[str, str]) -> str:
    """Sustituye los marcadores de la plantilla por los colores de la paleta."""
    replacements = {
        "{{matugen_grey}}": palette["MATUGEN_GREY"],
        "{{matugen_bg}}": palette["MATUGEN_BG"],
        "{{matugen_bg_over}}": palette["MATUGEN_BG_OVER"],
        "{{matugen_bg_over2}}": palette["MATUGEN_BG_OVER2"],
        "{{matugen_fg}}": palette["MATUGEN_FG"],
        "{{matugen_accent}}": palette["MATUGEN_ACCENT"],
        "{{matugen_accent_light}}": palette["MATUGEN_ACCENT_LIGHT"],
        "{{matugen_accent_pressed}}": palette["MATUGEN_ACCENT_PRESSED"],
    }
    content = template
    for marker, value in replacements.items():
        content = content.replace(marker, value)
    return content


def apply_materialgram(
    template_path: Path,
    destinations: tuple[Path, ...],
    palette: Mapping[str, str],
) -> AppResult:
    """Escribe el tema de Materialgram en todos sus destinos."""
    source = _template_path(template_path)
    if not source.is_file():
        return AppResult(app="materialgram", status="skipped", detail="sin plantilla")

    content = render_materialgram(source.read_text(encoding="utf-8"), palette)
    written = 0
    for destination in destinations:
        try:
            atomic_write_text(destination, content)
        except OSError:
            continue
        written += 1

    if written == 0:
        return AppResult(app="materialgram", status="failed", detail="sin destinos")
    return AppResult(
        app="materialgram",
        status="applied",
        detail=f"{written} destinos",
    )
