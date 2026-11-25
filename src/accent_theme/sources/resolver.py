"""Resolución de la fuente de color solicitada para el tema."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from accent_theme.sources.kde import read_kde_source
from accent_theme.sources.models import (
    SourceError,
    SourceKind,
    SourceRequest,
    ThemeSource,
)
from accent_theme.sources.waywallen import read_waywallen_source

if TYPE_CHECKING:
    from collections.abc import Mapping

    from accent_theme.paths import ThemePaths

SOURCE_REQUESTS: Final[tuple[SourceRequest, ...]] = ("auto", "kde", "waywallen")
NIRI_DESKTOP: Final = "niri"


def resolve_source_kind(request: str, environ: Mapping[str, str]) -> SourceKind:
    """Resuelve el tipo concreto de fuente para una petición."""
    if request not in SOURCE_REQUESTS:
        raise SourceError.invalid_source(request)
    if request != "auto":
        return request
    desktops = environ.get("XDG_CURRENT_DESKTOP", "").split(":")
    if any(desktop.strip().lower() == NIRI_DESKTOP for desktop in desktops):
        return "waywallen"
    return "kde"


def resolve_source(
    request: str,
    paths: ThemePaths,
    environ: Mapping[str, str],
) -> ThemeSource:
    """Resuelve la fuente concreta y delega en su lector."""
    kind = resolve_source_kind(request, environ)
    if kind == "waywallen":
        return read_waywallen_source(paths)
    return read_kde_source(paths, environ)
