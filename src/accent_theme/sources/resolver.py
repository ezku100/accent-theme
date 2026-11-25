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
    from pathlib import Path

    from accent_theme.paths import ThemePaths

SOURCE_REQUESTS: Final[tuple[SourceRequest, ...]] = ("auto", "kde", "waywallen")
NIRI_DESKTOP: Final = "niri"


def resolve_source_kind(
    request: str,
    environ: Mapping[str, str],
    waywallen_config: Path | None = None,
) -> SourceKind:
    """Resuelve el tipo concreto de fuente para una petición.

    En ``auto`` manda el compositor del entorno. Cuando el entorno no declara
    ninguno (servicios, cron, terminal sin sesión) se consulta el disco: si la
    configuración de Waywallen existe se sigue el wallpaper, que es la fuente
    activa de PikaOS; sin ella se recurre al acento de KDE.
    """
    if request not in SOURCE_REQUESTS:
        raise SourceError.invalid_source(request)
    if request != "auto":
        return request
    desktops = [
        desktop.strip().lower()
        for desktop in environ.get("XDG_CURRENT_DESKTOP", "").split(":")
        if desktop.strip()
    ]
    if desktops:
        return "waywallen" if NIRI_DESKTOP in desktops else "kde"
    if waywallen_config is not None and waywallen_config.exists():
        return "waywallen"
    return "kde"


def resolve_source(
    request: str,
    paths: ThemePaths,
    environ: Mapping[str, str],
) -> ThemeSource:
    """Resuelve la fuente concreta y delega en su lector."""
    kind = resolve_source_kind(request, environ, paths.waywallen_config)
    if kind == "waywallen":
        return read_waywallen_source(paths)
    return read_kde_source(paths, environ)
