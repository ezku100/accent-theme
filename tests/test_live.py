from __future__ import annotations

import json
import stat
from typing import TYPE_CHECKING, cast

from accent_theme.live import LivePaths, apply_live_integrations
from accent_theme.live.cava import inject_cava
from accent_theme.live.ghostty import touch_ghostty
from accent_theme.live.kitty import reload_kitty
from accent_theme.live.millennium import sync_millennium
from accent_theme.live.zen import deploy_zen

if TYPE_CHECKING:
    from pathlib import Path


def make_script(path: Path, body: str) -> None:
    _ = path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def make_fake_kitty(directory: Path, log: Path, *, exit_code: int = 0) -> Path:
    """Crea un binario ``kitty`` falso que registra los argumentos recibidos."""
    binary = directory / "kitty"
    make_script(
        binary,
        f'echo "$@" >> {log}\nexit {exit_code}',
    )
    return binary


def test_reload_kitty_applies_theme_to_every_socket(tmp_path: Path) -> None:
    log = tmp_path / "kitty.log"
    binaries = tmp_path / "bin"
    binaries.mkdir()
    _ = make_fake_kitty(binaries, log)
    socket_root = tmp_path / "sockets"
    socket_root.mkdir()
    first = socket_root / "kitty-socket-1"
    second = socket_root / "kitty-socket-2"
    _ = first.touch()
    _ = second.touch()
    theme = tmp_path / "theme.conf"
    _ = theme.write_text("background #101010\n", encoding="utf-8")

    result = reload_kitty(
        theme,
        socket_root,
        {"PATH": str(binaries)},
    )

    recorded = log.read_text(encoding="utf-8")
    assert result.status == "applied"
    assert f"unix:{first}" in recorded
    assert f"unix:{second}" in recorded
    assert f"set-colors -a {theme}" in recorded


def test_reload_kitty_skips_when_theme_is_missing(tmp_path: Path) -> None:
    socket_root = tmp_path / "sockets"
    socket_root.mkdir()
    (socket_root / "kitty-socket-1").touch()

    result = reload_kitty(tmp_path / "ausente.conf", socket_root, {"PATH": ""})

    assert result.status == "skipped"


def test_reload_kitty_skips_without_active_sockets(tmp_path: Path) -> None:
    socket_root = tmp_path / "sockets"
    socket_root.mkdir()
    theme = tmp_path / "theme.conf"
    _ = theme.write_text("background #101010\n", encoding="utf-8")

    result = reload_kitty(theme, socket_root, {"PATH": ""})

    assert result.status == "skipped"


def test_reload_kitty_reports_failure_when_kitty_fails(tmp_path: Path) -> None:
    log = tmp_path / "kitty.log"
    binaries = tmp_path / "bin"
    binaries.mkdir()
    _ = make_fake_kitty(binaries, log, exit_code=1)
    socket_root = tmp_path / "sockets"
    socket_root.mkdir()
    _ = (socket_root / "kitty-socket-1").touch()
    theme = tmp_path / "theme.conf"
    _ = theme.write_text("background #101010\n", encoding="utf-8")

    result = reload_kitty(theme, socket_root, {"PATH": str(binaries)})

    assert result.status == "failed"


def test_touch_ghostty_marks_config_as_reloaded(tmp_path: Path) -> None:
    config = tmp_path / "config"
    _ = config.write_text("theme = dark\n", encoding="utf-8")

    result = touch_ghostty(config)

    assert result.status == "applied"
    assert config.read_text(encoding="utf-8") == "theme = dark\n"


def test_touch_ghostty_skips_when_config_is_missing(tmp_path: Path) -> None:
    result = touch_ghostty(tmp_path / "config")

    assert result.status == "skipped"


def test_deploy_zen_copies_css_and_ensures_imports(tmp_path: Path) -> None:
    css = tmp_path / "kde-accent.css"
    _ = css.write_text(":root { --accent: #123456; }\n", encoding="utf-8")
    profile = tmp_path / ".zen" / "abc.Default"
    profile.mkdir(parents=True)

    result = deploy_zen(css, (tmp_path / ".zen",))

    deployed = profile / "chrome" / "kde-accent.css"
    assert result.status == "applied"
    assert deployed.read_text(encoding="utf-8") == ":root { --accent: #123456; }\n"
    assert '@import url("kde-accent.css");' in (
        profile / "chrome" / "userChrome.css"
    ).read_text(encoding="utf-8")
    assert "legacyUserProfileCustomizations" in (profile / "user.js").read_text(
        encoding="utf-8"
    )


def test_deploy_zen_skips_without_css(tmp_path: Path) -> None:
    profile = tmp_path / ".zen" / "abc.Default"
    profile.mkdir(parents=True)

    result = deploy_zen(tmp_path / "ausente.css", (tmp_path / ".zen",))

    assert result.status == "skipped"


def test_deploy_zen_skips_without_profiles(tmp_path: Path) -> None:
    css = tmp_path / "kde-accent.css"
    _ = css.write_text(":root { --accent: #123456; }\n", encoding="utf-8")

    result = deploy_zen(css, (tmp_path / ".zen",))

    assert result.status == "skipped"


def test_inject_cava_writes_keys_inside_color_section(tmp_path: Path) -> None:
    snippet = tmp_path / "snippet"
    _ = snippet.write_text(
        "foreground = #ffffff\nbackground = #000000\n",
        encoding="utf-8",
    )
    config = tmp_path / "config"
    _ = config.write_text(
        "[general]\nlive-config = 0\n\n[color]\nforeground = #aaaaaa\n",
        encoding="utf-8",
    )

    result = inject_cava(snippet, config)

    contents = config.read_text(encoding="utf-8")
    assert result.status == "applied"
    assert "live-config = 1" in contents
    assert "foreground = #ffffff" in contents
    assert "background = #000000" in contents
    assert "#aaaaaa" not in contents


def test_inject_cava_skips_without_snippet(tmp_path: Path) -> None:
    config = tmp_path / "config"
    _ = config.write_text("[general]\n", encoding="utf-8")

    result = inject_cava(tmp_path / "ausente", config)

    assert result.status == "skipped"


def test_sync_millennium_updates_accent_colors(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    _ = config.write_text(
        json.dumps(
            {
                "general": {"accentColor": "#111111"},
                "themes": {
                    "themeColors": {
                        "Material-Theme": {"--custom-accent-color": "#111111"}
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    accent_file = tmp_path / "dinamico-accent.txt"

    result = sync_millennium(config, "#123456", accent_file)

    parsed = cast("object", json.loads(config.read_text(encoding="utf-8")))
    assert result.status == "applied"
    assert parsed == {
        "general": {"accentColor": "#123456"},
        "themes": {
            "themeColors": {"Material-Theme": {"--custom-accent-color": "#123456"}}
        },
    }
    assert accent_file.read_text(encoding="utf-8").strip() == "#123456"


def test_sync_millennium_skips_without_config(tmp_path: Path) -> None:
    result = sync_millennium(
        tmp_path / "config.json",
        "#123456",
        tmp_path / "dinamico-accent.txt",
    )

    assert result.status == "skipped"


def test_apply_live_integrations_reports_every_app(tmp_path: Path) -> None:
    environ = {"HOME": str(tmp_path), "PATH": ""}
    paths = LivePaths.from_environment(environ)

    results = apply_live_integrations(paths, "#123456", environ)

    assert [result.app for result in results] == [
        "kitty",
        "ghostty",
        "zen",
        "cava",
        "millennium",
    ]
    assert all(result.status == "skipped" for result in results)


def test_live_paths_follow_xdg_environment(tmp_path: Path) -> None:
    paths = LivePaths.from_environment(
        {
            "HOME": str(tmp_path),
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
            "XDG_CACHE_HOME": str(tmp_path / "cache"),
        }
    )

    assert paths.kitty_theme == tmp_path / "config" / "kitty" / "theme.conf"
    assert paths.ghostty_config == tmp_path / "config" / "ghostty" / "config"
    assert paths.cava_config == tmp_path / "config" / "cava" / "config"
    assert paths.zen_css == tmp_path / "cache" / "matugen-zen-kde-accent.css"
    assert paths.millennium_config == (
        tmp_path / "config" / "millennium" / "config.json"
    )
