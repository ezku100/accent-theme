"""Lector de la fuente de color proporcionada por Waywallen."""

from __future__ import annotations

import sqlite3
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

from accent_theme.sources.models import SourceError, ThemeSource

if TYPE_CHECKING:
    from accent_theme.paths import ThemePaths

PREVIEW_QUERY: Final = """
SELECT i.preview_path, l.path
FROM item AS i
JOIN library AS l ON l.id = i.library_id
WHERE i.id = ?
"""


def read_last_wallpaper(config_path: Path) -> str:
    """Lee el último wallpaper global o, en su defecto, por display."""
    try:
        with config_path.open("rb") as config_file:
            document = tomllib.load(config_file)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise SourceError.invalid_config(config_path, str(error)) from error

    global_section = document.get("global")
    if isinstance(global_section, dict):
        global_entries = cast("dict[str, str]", global_section)
        global_value = global_entries.get("last_wallpaper")
        if global_value:
            return global_value

    display_section = document.get("display")
    if isinstance(display_section, dict):
        display_entries = cast("dict[str, dict[str, str]]", display_section)
        for name in sorted(display_entries):
            value = display_entries[name].get("last_wallpaper")
            if isinstance(value, str) and value:
                return value

    raise SourceError.missing_last_wallpaper(config_path)


def resolve_preview_path(database_path: Path, wallpaper_id: str) -> Path:
    """Resuelve un preview relativo dentro de la librería Waywallen."""
    try:
        connection = sqlite3.connect(
            f"file:{database_path}?mode=ro",
            uri=True,
        )
        try:
            row = cast(
                "tuple[str, str] | None",
                connection.execute(PREVIEW_QUERY, (wallpaper_id,)).fetchone(),
            )
        finally:
            connection.close()
    except sqlite3.Error as error:
        raise SourceError.unreadable_database(database_path, str(error)) from error

    if row is None:
        raise SourceError.missing_item(database_path, wallpaper_id)

    preview_value = row[0]
    library_value = row[1]
    preview_relative = Path(preview_value)
    library_root = Path(library_value)
    if preview_relative.is_absolute() or ".." in preview_relative.parts:
        raise SourceError.invalid_preview(preview_relative, library_root)

    candidate = (library_root / preview_relative).resolve(strict=False)
    root = library_root.resolve(strict=False)
    if not candidate.is_relative_to(root):
        raise SourceError.invalid_preview(preview_relative, library_root)
    if not candidate.is_file():
        raise SourceError.missing_preview(candidate)
    return candidate


def read_waywallen_source(paths: ThemePaths) -> ThemeSource:
    """Combina el wallpaper activo con su preview de la galería."""
    wallpaper_id = read_last_wallpaper(paths.waywallen_config)
    preview = resolve_preview_path(paths.waywallen_database, wallpaper_id)
    return ThemeSource(
        kind="waywallen",
        reference=wallpaper_id,
        preview=preview,
        accent=None,
    )
