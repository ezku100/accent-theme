"""Modelos compartidos por las fuentes de color del tema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

SourceKind = Literal["kde", "waywallen"]
SourceRequest = Literal["auto", "kde", "waywallen"]


@dataclass(frozen=True, slots=True)
class ThemeSource:
    """Fuente de color ya resuelta para una generación."""

    kind: SourceKind
    reference: str
    preview: Path | None = None
    accent: str | None = None


class SourceError(RuntimeError):
    """Error al resolver la fuente de color del tema."""

    @classmethod
    def invalid_source(cls, value: str) -> SourceError:
        """Construye el error de una fuente solicitada desconocida."""
        return cls(f"fuente desconocida: {value}")

    @classmethod
    def invalid_config(cls, path: Path, detail: str) -> SourceError:
        """Construye el error de una configuración de fuente inválida."""
        return cls(f"configuración inválida en {path}: {detail}")

    @classmethod
    def missing_last_wallpaper(cls, path: Path) -> SourceError:
        """Construye el error de un wallpaper ausente en la configuración."""
        return cls(f"no hay wallpaper registrado en {path}")

    @classmethod
    def missing_item(cls, database: Path, wallpaper_id: str) -> SourceError:
        """Construye el error de un item de galería ausente."""
        return cls(f"wallpaper {wallpaper_id} ausente en {database}")

    @classmethod
    def invalid_preview(cls, preview: Path, library_root: Path) -> SourceError:
        """Construye el error de un preview fuera de su librería."""
        return cls(f"preview fuera de la librería {library_root}: {preview}")

    @classmethod
    def missing_preview(cls, path: Path) -> SourceError:
        """Construye el error de un preview que no existe."""
        return cls(f"preview no encontrado: {path}")

    @classmethod
    def unreadable_database(cls, path: Path, detail: str) -> SourceError:
        """Construye el error de una base de datos que no se puede leer."""
        return cls(f"no se pudo leer {path}: {detail}")
