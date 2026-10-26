"""Rutas de los archivos que las integraciones en vivo tocan."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True, slots=True)
class LivePaths:
    """Rutas de configuración de las apps que aceptan recarga inmediata."""

    kitty_theme: Path
    kitty_socket_dir: Path
    ghostty_config: Path
    zen_css: Path
    zen_profile_roots: tuple[Path, ...]
    cava_snippet: Path
    cava_config: Path
    millennium_config: Path
    millennium_accent_file: Path

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> LivePaths:
        """Construye las rutas respetando XDG y el HOME efectivo."""
        home = Path(environ.get("HOME", str(Path.home()))).expanduser()
        config_home = Path(
            environ.get("XDG_CONFIG_HOME", home / ".config")
        ).expanduser()
        cache_home = Path(environ.get("XDG_CACHE_HOME", home / ".cache")).expanduser()
        runtime_dir = environ.get("XDG_RUNTIME_DIR", "")
        socket_dir = Path(runtime_dir) if runtime_dir else Path("/tmp")  # noqa: S108

        return cls(
            kitty_theme=config_home / "kitty" / "theme.conf",
            kitty_socket_dir=socket_dir,
            ghostty_config=config_home / "ghostty" / "config",
            zen_css=cache_home / "matugen-zen-kde-accent.css",
            zen_profile_roots=(
                home / ".var" / "app" / "app.zen_browser.zen" / ".zen",
                home / ".zen",
            ),
            cava_snippet=cache_home / "matugen-cava-snippet",
            cava_config=config_home / "cava" / "config",
            millennium_config=config_home / "millennium" / "config.json",
            millennium_accent_file=config_home / "millennium" / "dinamico-accent.txt",
        )
