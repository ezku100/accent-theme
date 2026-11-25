"""Lector de la fuente de color compatible con KDE."""

from __future__ import annotations

from typing import TYPE_CHECKING

from accent_theme.accent import accent_to_hex, read_accent
from accent_theme.sources.models import ThemeSource

if TYPE_CHECKING:
    from collections.abc import Mapping

    from accent_theme.paths import ThemePaths


def read_kde_source(paths: ThemePaths, environ: Mapping[str, str]) -> ThemeSource:
    """Lee el acento configurado en ``kdeglobals`` sin modificarlo."""
    _ = environ
    accent = read_accent(paths.kde_globals)
    value = accent_to_hex(accent)
    return ThemeSource(kind="kde", reference=value, accent=value, preview=None)
