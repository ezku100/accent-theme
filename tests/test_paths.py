from __future__ import annotations

from typing import TYPE_CHECKING

from accent_theme.paths import ThemePaths

if TYPE_CHECKING:
    from pathlib import Path


def test_paths_follow_xdg_environment(tmp_path: Path) -> None:
    paths = ThemePaths.from_environment(
        {
            "HOME": str(tmp_path),
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
            "XDG_DATA_HOME": str(tmp_path / "data"),
            "XDG_CACHE_HOME": str(tmp_path / "cache"),
        }
    )

    assert paths.config_home == tmp_path / "config" / "accent-theme"
    assert paths.data_home == tmp_path / "data" / "accent-theme"
    assert paths.cache_home == tmp_path / "cache" / "accent-theme"
    assert paths.templates_dir == tmp_path / "config" / "accent-theme" / "templates"
    assert paths.templates_d_dir == (
        tmp_path / "config" / "accent-theme" / "templates.d"
    )
    assert paths.matugen_config == (
        tmp_path / "config" / "accent-theme" / "matugen.toml"
    )
    assert paths.user_service == (
        tmp_path / "config" / "systemd" / "user" / "accent-theme.service"
    )


def test_paths_use_home_defaults_when_xdg_is_unset(tmp_path: Path) -> None:
    paths = ThemePaths.from_environment({"HOME": str(tmp_path)})

    assert paths.config_home == tmp_path / ".config" / "accent-theme"
    assert paths.data_home == tmp_path / ".local" / "share" / "accent-theme"
    assert paths.cache_home == tmp_path / ".cache" / "accent-theme"
