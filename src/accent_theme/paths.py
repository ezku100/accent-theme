"""Rutas XDG y de usuario del motor de tema."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True, slots=True)
class ThemePaths:
    """Rutas XDG y de usuario del motor de tema."""

    home: Path
    config_home: Path
    data_home: Path
    cache_home: Path
    templates_dir: Path
    templates_d_dir: Path
    matugen_config: Path
    user_service: Path
    kde_globals: Path
    waywallen_config: Path
    waywallen_database: Path
    niri_state: Path
    kcolor_scheme: Path
    kde_globals_backup: Path
    kde_globals_applied: Path

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> ThemePaths:
        """Construye las rutas respetando XDG y el HOME efectivo."""
        home = Path(environ.get("HOME", str(Path.home()))).expanduser()
        xdg_config = Path(environ.get("XDG_CONFIG_HOME", home / ".config")).expanduser()
        xdg_data = Path(environ.get("XDG_DATA_HOME", home / ".local" / "share"))
        xdg_cache = Path(environ.get("XDG_CACHE_HOME", home / ".cache")).expanduser()

        config_home = xdg_config / "accent-theme"
        data_home = xdg_data / "accent-theme"
        cache_home = xdg_cache / "accent-theme"
        return cls(
            home=home,
            config_home=config_home,
            data_home=data_home,
            cache_home=cache_home,
            templates_dir=config_home / "templates",
            templates_d_dir=config_home / "templates.d",
            matugen_config=config_home / "matugen.toml",
            user_service=xdg_config / "systemd" / "user" / "accent-theme.service",
            kde_globals=xdg_config / "kdeglobals",
            waywallen_config=(
                home
                / ".var"
                / "app"
                / "org.waywallen.waywallen"
                / "config"
                / "waywallen"
                / "config.toml"
            ),
            waywallen_database=(
                home
                / ".var"
                / "app"
                / "org.waywallen.waywallen"
                / "data"
                / "waywallen"
                / "waywallen-v2.db"
            ),
            niri_state=cache_home / "niri-state.json",
            kcolor_scheme=xdg_data / "color-schemes" / "Matugen.colors",
            kde_globals_backup=cache_home / "kdeglobals-colors.backup",
            kde_globals_applied=cache_home / "kdeglobals-colors.applied",
        )

    @classmethod
    def current(cls) -> ThemePaths:
        """Construye las rutas desde el entorno del proceso."""
        return cls.from_environment(os.environ)
