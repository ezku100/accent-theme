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
    hooks_dir: Path
    hooks_active_dir: Path
    hooks_support_dir: Path

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> ThemePaths:
        """Construye las rutas respetando XDG y el HOME efectivo."""
        home = Path(environ.get("HOME", str(Path.home()))).expanduser()
        xdg_config = Path(environ.get("XDG_CONFIG_HOME", home / ".config")).expanduser()
        xdg_data = Path(environ.get("XDG_DATA_HOME", home / ".local" / "share"))
        xdg_cache = Path(environ.get("XDG_CACHE_HOME", home / ".cache")).expanduser()

        config_home = xdg_config / "accent-theme"
        data_home = xdg_data / "accent-theme"
        hooks_dir = data_home / "source" / "hooks"
        return cls(
            home=home,
            config_home=config_home,
            data_home=data_home,
            cache_home=xdg_cache / "accent-theme",
            templates_dir=config_home / "templates",
            templates_d_dir=config_home / "templates.d",
            matugen_config=config_home / "matugen.toml",
            user_service=xdg_config / "systemd" / "user" / "accent-theme.service",
            hooks_dir=hooks_dir,
            hooks_active_dir=hooks_dir / "active",
            hooks_support_dir=hooks_dir / "support",
        )

    @classmethod
    def current(cls) -> ThemePaths:
        """Construye las rutas desde el entorno del proceso."""
        return cls.from_environment(os.environ)
