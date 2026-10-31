"""Rutas de las apps que el motor aplica tras generar la paleta."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True, slots=True)
class AppPaths:
    """Rutas que necesita cada integración de apps."""

    brave_roots: tuple[Path, ...]
    equibop_theme: Path
    obs_base: Path
    obs_themes: tuple[Path, ...]
    materialgram_template: Path
    materialgram_themes: tuple[Path, ...]

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> AppPaths:
        """Construye las rutas respetando XDG y el HOME efectivo."""
        home = Path(environ.get("HOME", str(Path.home()))).expanduser()
        config_home = Path(
            environ.get("XDG_CONFIG_HOME", home / ".config")
        ).expanduser()

        return cls(
            brave_roots=(
                config_home / "BraveSoftware" / "Brave-Browser",
                home
                / ".var"
                / "app"
                / "com.brave.Browser"
                / "config"
                / "BraveSoftware"
                / "Brave-Browser",
            ),
            equibop_theme=config_home
            / "equibop"
            / "themes"
            / "midnight-accent-kde.theme.css",
            obs_base=home
            / ".var"
            / "app"
            / "com.obsproject.Studio"
            / "config"
            / "obs-studio"
            / "themes"
            / "Venom.obt",
            obs_themes=(
                home
                / ".var"
                / "app"
                / "com.obsproject.Studio"
                / "config"
                / "obs-studio"
                / "themes"
                / "Dinamico.obt",
                config_home / "obs-studio" / "themes" / "Dinamico.obt",
            ),
            materialgram_template=config_home
            / "accent-theme"
            / "templates"
            / "materialgram"
            / "materialgram.tdesktop-theme",
            materialgram_themes=(
                home
                / ".var"
                / "app"
                / "io.github.kukuruzka165.materialgram"
                / "data"
                / "materialgram"
                / "tdata"
                / "Dinamico.tdesktop-theme",
                config_home / "materialgram" / "themes" / "Dinamico.tdesktop-theme",
                home / "Documents" / "Dinamico.tdesktop-theme",
            ),
        )
