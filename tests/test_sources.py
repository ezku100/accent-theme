"""Pruebas de rutas, modelos y resolución de fuentes del tema."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from accent_theme.paths import ThemePaths
from accent_theme.sources import (
    SOURCE_REQUESTS,
    SourceError,
    ThemeSource,
    resolve_source,
    resolve_source_kind,
)
from accent_theme.sources import resolver as resolver_module
from accent_theme.sources.kde import read_kde_source
from accent_theme.sources.waywallen import (
    read_last_wallpaper,
    read_waywallen_source,
    resolve_preview_path,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_paths_expose_kde_waywallen_and_state_paths(tmp_path: Path) -> None:
    environ = {
        "HOME": str(tmp_path / "home"),
        "XDG_CONFIG_HOME": str(tmp_path / "xdg-config"),
        "XDG_DATA_HOME": str(tmp_path / "xdg-data"),
        "XDG_CACHE_HOME": str(tmp_path / "xdg-cache"),
    }

    paths = ThemePaths.from_environment(environ)

    assert paths.kde_globals == tmp_path / "xdg-config" / "kdeglobals"
    assert paths.waywallen_config == (
        tmp_path
        / "home"
        / ".var"
        / "app"
        / "org.waywallen.waywallen"
        / "config"
        / "waywallen"
        / "config.toml"
    )
    assert paths.waywallen_database == (
        tmp_path
        / "home"
        / ".var"
        / "app"
        / "org.waywallen.waywallen"
        / "data"
        / "waywallen"
        / "waywallen-v2.db"
    )
    assert paths.niri_state == (
        tmp_path / "xdg-cache" / "accent-theme" / "niri-state.json"
    )


def test_resolve_source_kind_auto_uses_waywallen_for_niri() -> None:
    assert resolve_source_kind("auto", {"XDG_CURRENT_DESKTOP": "niri"}) == "waywallen"


def test_resolve_source_kind_auto_uses_kde_for_non_niri_desktop_chain() -> None:
    environ = {"XDG_CURRENT_DESKTOP": "plasma:gnome:NIRI-OTHER"}

    assert resolve_source_kind("auto", environ) == "kde"


def test_resolve_source_kind_auto_uses_kde_without_desktop() -> None:
    assert resolve_source_kind("auto", {}) == "kde"


def test_resolve_source_kind_auto_uses_waywallen_when_its_config_exists(
    tmp_path: Path,
) -> None:
    config = tmp_path / "config.toml"
    _ = config.write_text('[global]\nlast_wallpaper = "27"\n', encoding="utf-8")

    assert resolve_source_kind("auto", {}, config) == "waywallen"


def test_resolve_source_kind_auto_uses_kde_when_waywallen_config_is_absent(
    tmp_path: Path,
) -> None:
    assert resolve_source_kind("auto", {}, tmp_path / "missing.toml") == "kde"


def test_resolve_source_auto_fails_when_the_wallpaper_config_is_broken(
    tmp_path: Path,
) -> None:
    environ = {"HOME": str(tmp_path / "home")}
    paths = ThemePaths.from_environment(environ)
    paths.waywallen_config.parent.mkdir(parents=True, exist_ok=True)
    _ = paths.waywallen_config.write_text("esto = [no es toml", encoding="utf-8")

    with pytest.raises(SourceError):
        _ = resolve_source("auto", paths, environ)


def test_resolve_source_kind_rejects_unknown_request() -> None:
    with pytest.raises(SourceError):
        _ = resolve_source_kind("otra", {})
    assert SOURCE_REQUESTS == ("auto", "kde", "waywallen")


def test_read_kde_source_uses_accent_color(tmp_path: Path) -> None:
    config = tmp_path / "kdeglobals"
    _ = config.write_text(
        "[General]\nAccentColor=1,2,3\n",
        encoding="utf-8",
    )
    paths = ThemePaths.from_environment(
        {"HOME": str(tmp_path), "XDG_CONFIG_HOME": str(tmp_path)}
    )

    source = read_kde_source(paths, {"PATH": ""})

    assert source == ThemeSource(
        kind="kde",
        reference="#010203",
        accent="#010203",
        preview=None,
    )


def test_read_kde_source_falls_back_to_decorative_precolor(tmp_path: Path) -> None:
    config = tmp_path / "kdeglobals"
    _ = config.write_text(
        "[Colors:Selection]\nBackgroundNormal=12,34,56\n",
        encoding="utf-8",
    )
    paths = ThemePaths.from_environment(
        {"HOME": str(tmp_path), "XDG_CONFIG_HOME": str(tmp_path)}
    )

    source = read_kde_source(paths, {"PATH": ""})

    assert source == ThemeSource(
        kind="kde",
        reference="#0c2238",
        accent="#0c2238",
        preview=None,
    )


def test_read_last_wallpaper_prefers_global_section(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    _ = config.write_text(
        '[global]\nlast_wallpaper = "27"\n\n[display.one]\nlast_wallpaper = "42"\n',
        encoding="utf-8",
    )

    assert read_last_wallpaper(config) == "27"


def test_read_last_wallpaper_falls_back_to_display_entries(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config_text = (
        '[display.one]\nlast_wallpaper = "42"\n\n'
        '[display.two]\nlast_wallpaper = "27"\n'
    )
    _ = config.write_text(config_text, encoding="utf-8")

    assert read_last_wallpaper(config) == "42"


def test_read_last_wallpaper_rejects_missing_value(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    _ = config.write_text('[global]\nlast_wallpaper = ""\n', encoding="utf-8")

    with pytest.raises(SourceError):
        _ = read_last_wallpaper(config)


def _create_waywallen_database(
    database: Path,
    library_root: Path,
    *,
    wallpaper_id: str = "27",
    preview_path: str = "wallpapers/preview.gif",
) -> None:
    connection = sqlite3.connect(database)
    try:
        _ = connection.execute(
            "CREATE TABLE library (id INTEGER PRIMARY KEY, path TEXT NOT NULL)"
        )
        item_schema = (
            "CREATE TABLE item (id INTEGER PRIMARY KEY, "
            "library_id INTEGER NOT NULL, preview_path TEXT)"
        )
        _ = connection.execute(item_schema)
        _ = connection.execute(
            "INSERT INTO library (id, path) VALUES (1, ?)",
            (str(library_root),),
        )
        _ = connection.execute(
            "INSERT INTO item (id, library_id, preview_path) VALUES (?, 1, ?)",
            (wallpaper_id, preview_path),
        )
        _ = connection.commit()
    finally:
        connection.close()


def test_resolve_preview_path_uses_read_only_uri(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "waywallen.db"
    library = tmp_path / "library"
    preview = library / "wallpapers" / "preview.gif"
    _ = preview.parent.mkdir(parents=True)
    _ = preview.write_bytes(b"GIF89a")
    _create_waywallen_database(database, library)
    seen: list[tuple[str, bool]] = []
    original_connect = sqlite3.connect

    def recording_connect(
        database_uri: str,
        *,
        uri: bool = False,
    ) -> sqlite3.Connection:
        seen.append((database_uri, uri))
        return original_connect(database_uri, uri=uri)

    monkeypatch.setattr(sqlite3, "connect", recording_connect)

    resolved = resolve_preview_path(database, "27")

    assert resolved == preview
    assert seen == [(f"file:{database}?mode=ro", True)]


def test_resolve_preview_path_returns_relative_preview_inside_library(
    tmp_path: Path,
) -> None:
    database = tmp_path / "waywallen.db"
    library = tmp_path / "library"
    preview = library / "wallpapers" / "preview.gif"
    _ = preview.parent.mkdir(parents=True)
    _ = preview.write_bytes(b"GIF89a")
    _create_waywallen_database(database, library)

    resolved = resolve_preview_path(database, "27")

    assert resolved.is_relative_to(library)


def test_resolve_preview_path_rejects_absolute_preview(tmp_path: Path) -> None:
    database = tmp_path / "waywallen.db"
    library = tmp_path / "library"
    _ = library.mkdir()
    _create_waywallen_database(database, library, preview_path="/etc/passwd")

    with pytest.raises(SourceError):
        _ = resolve_preview_path(database, "27")


def test_resolve_preview_path_rejects_parent_traversal(tmp_path: Path) -> None:
    database = tmp_path / "waywallen.db"
    library = tmp_path / "library"
    _ = library.mkdir()
    _create_waywallen_database(database, library, preview_path="../outside.gif")

    with pytest.raises(SourceError):
        _ = resolve_preview_path(database, "27")


def test_resolve_preview_path_rejects_missing_item(tmp_path: Path) -> None:
    database = tmp_path / "waywallen.db"
    library = tmp_path / "library"
    _ = library.mkdir()
    _create_waywallen_database(database, library)

    with pytest.raises(SourceError):
        _ = resolve_preview_path(database, "missing")


def test_read_waywallen_source_returns_preview_and_id(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    _ = config.write_text('[global]\nlast_wallpaper = "27"\n', encoding="utf-8")
    database = tmp_path / "waywallen.db"
    library = tmp_path / "library"
    preview = library / "wallpapers" / "preview.gif"
    _ = preview.parent.mkdir(parents=True)
    _ = preview.write_bytes(b"GIF89a")
    _create_waywallen_database(database, library)
    paths = replace(
        ThemePaths.from_environment({"HOME": str(tmp_path)}),
        waywallen_config=config,
        waywallen_database=database,
    )

    source = read_waywallen_source(paths)

    assert source == ThemeSource(
        kind="waywallen",
        reference="27",
        preview=preview,
        accent=None,
    )


def test_resolve_source_dispatches_to_waywallen_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = ThemePaths.from_environment({"HOME": str(tmp_path)})
    seen: list[ThemePaths] = []

    def fake_reader(reader_paths: ThemePaths) -> ThemeSource:
        seen.append(reader_paths)
        return ThemeSource(kind="waywallen", reference="27")

    monkeypatch.setattr(resolver_module, "read_waywallen_source", fake_reader)

    source = resolve_source("waywallen", paths, {})

    assert source == ThemeSource(kind="waywallen", reference="27")
    assert seen == [paths]
