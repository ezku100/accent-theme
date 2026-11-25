"""Pruebas de la orquestación y publicación atómica de una generación."""

from __future__ import annotations

import json
import stat
from typing import TYPE_CHECKING, cast

import pytest

from accent_theme import generation as generation_module
from accent_theme.accent import Accent
from accent_theme.generation import GenerationError, generate_once
from accent_theme.kde_globals import KdeGlobalsPaths, apply_colors
from accent_theme.matugen import REQUIRED_ROLES, MatugenTokens
from accent_theme.paths import ThemePaths
from accent_theme.registry import TemplateRegistration
from accent_theme.sources.models import ThemeSource

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from accent_theme.apps import AppPaths
    from accent_theme.apps.base import AppResult
    from accent_theme.live import LivePaths
    from accent_theme.live.base import LiveResult


def _tokens(**overrides: str) -> MatugenTokens:
    """Construye tokens con todos los roles que Matugen garantiza."""
    colors: dict[str, str] = dict.fromkeys(REQUIRED_ROLES, "#123456")
    colors.update(overrides)
    return MatugenTokens(colors)


def _paths(tmp_path: Path) -> ThemePaths:
    return ThemePaths.from_environment(
        {
            "HOME": str(tmp_path),
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
            "XDG_DATA_HOME": str(tmp_path / "data"),
            "XDG_CACHE_HOME": str(tmp_path / "cache"),
        }
    )


def _registration(
    tmp_path: Path,
    name: str,
    saturation: float | None = None,
) -> TemplateRegistration:
    output = tmp_path / "cache" / f"{name}.json"
    return TemplateRegistration(
        name=name,
        input_path=tmp_path / "templates" / f"{name}.json",
        output_path=output,
        saturation=saturation,
    )


def _binary(tmp_path: Path) -> Path:
    binary = tmp_path / "matugen"
    _ = binary.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    return binary


def _stub_source(
    monkeypatch: pytest.MonkeyPatch,
    source: ThemeSource,
) -> None:
    def fake_resolve(
        _request: str,
        _paths: ThemePaths,
        _environ: Mapping[str, str],
    ) -> ThemeSource:
        return source

    monkeypatch.setattr(generation_module, "resolve_source", fake_resolve)


def _stub_empty_integrations(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_apps(
        _paths: AppPaths,
        _accent: Accent,
        _palette: Mapping[str, str],
    ) -> tuple[AppResult, ...]:
        return ()

    def fake_live(
        _paths: LivePaths,
        _accent: str,
        _environ: Mapping[str, str],
    ) -> tuple[LiveResult, ...]:
        return ()

    monkeypatch.setattr(generation_module, "apply_app_integrations", fake_apps)
    monkeypatch.setattr(generation_module, "apply_live_integrations", fake_live)


def test_generate_once_kde_uses_color_and_existing_roles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _paths(tmp_path)
    registration = _registration(tmp_path, "colors")
    binary = _binary(tmp_path)
    captured: dict[str, str] = {}
    tokens = _tokens(primary="#123456", surface="#101010")

    def fake_invoke(
        invoked_binary: Path,
        accent: str,
        config: Path,
    ) -> MatugenTokens:
        captured["binary"] = str(invoked_binary)
        captured["accent"] = accent
        captured["config"] = str(config)
        _ = registration.staging_path.write_text(
            json.dumps({"primary": "#123456"}),
            encoding="utf-8",
        )
        return tokens

    _stub_source(
        monkeypatch,
        ThemeSource(kind="kde", reference="#3daee9", accent="#3daee9"),
    )

    def fake_find(_environ: Mapping[str, str]) -> Path | None:
        return binary

    def fake_rebuild(
        _config_paths: ThemePaths,
    ) -> tuple[TemplateRegistration, ...]:
        return (registration,)

    monkeypatch.setattr(generation_module, "find_matugen", fake_find)
    monkeypatch.setattr(generation_module, "rebuild_config", fake_rebuild)
    monkeypatch.setattr(generation_module, "invoke_matugen", fake_invoke)
    _stub_empty_integrations(monkeypatch)

    result = generate_once(paths, {"HOME": str(tmp_path)}, "kde")

    assert captured == {
        "binary": str(binary),
        "accent": "#3daee9",
        "config": str(paths.matugen_config),
    }
    assert result.tokens["primary"] == "#123456"
    assert result.source_color == "#3daee9"
    published = registration.output_path.read_text(encoding="utf-8")
    assert published == '{"primary": "#123456"}'


def test_generate_once_waywallen_uses_image_and_source_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _paths(tmp_path)
    registration = _registration(tmp_path, "colors")
    binary = _binary(tmp_path)
    preview = tmp_path / "preview.gif"
    captured: dict[str, str] = {}
    tokens = _tokens(primary="#123456", source_color="#ec1413")

    def fake_invoke_image(
        invoked_binary: Path,
        image: Path,
        config: Path,
    ) -> MatugenTokens:
        captured["binary"] = str(invoked_binary)
        captured["image"] = str(image)
        captured["config"] = str(config)
        _ = registration.staging_path.write_text(
            json.dumps({"primary": "#123456", "source_color": "#ec1413"}),
            encoding="utf-8",
        )
        return tokens

    _stub_source(
        monkeypatch,
        ThemeSource(kind="waywallen", reference="27", preview=preview),
    )

    def fake_find(_environ: Mapping[str, str]) -> Path | None:
        return binary

    def fake_rebuild(
        _config_paths: ThemePaths,
    ) -> tuple[TemplateRegistration, ...]:
        return (registration,)

    monkeypatch.setattr(generation_module, "find_matugen", fake_find)
    monkeypatch.setattr(generation_module, "rebuild_config", fake_rebuild)
    monkeypatch.setattr(
        generation_module,
        "invoke_matugen_image",
        fake_invoke_image,
    )
    _stub_empty_integrations(monkeypatch)

    result = generate_once(paths, {"HOME": str(tmp_path)}, "waywallen")

    assert captured == {
        "binary": str(binary),
        "image": str(preview),
        "config": str(paths.matugen_config),
    }
    assert result.source_color == "#ec1413"
    assert result.state.wallpaper_id == "27"
    assert result.state.reference == "27"


def test_generate_once_waywallen_propagates_accent_to_integrations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _paths(tmp_path)
    tokens = _tokens(primary="#123456", source_color="#ec1413")
    captured: dict[str, Accent | str] = {}

    _stub_source(
        monkeypatch,
        ThemeSource(kind="waywallen", reference="27", preview=tmp_path / "preview.gif"),
    )

    def fake_find(_environ: Mapping[str, str]) -> Path | None:
        return _binary(tmp_path)

    def fake_rebuild(
        _config_paths: ThemePaths,
    ) -> tuple[TemplateRegistration, ...]:
        return ()

    def fake_invoke_image(
        _binary: Path,
        _image: Path,
        _config: Path,
    ) -> MatugenTokens:
        return tokens

    def fake_apps(
        _app_paths: AppPaths,
        accent: Accent,
        _palette: Mapping[str, str],
    ) -> tuple[AppResult, ...]:
        captured["app_accent"] = accent
        return ()

    def fake_live(
        _live_paths: LivePaths,
        accent: str,
        _environ: Mapping[str, str],
    ) -> tuple[LiveResult, ...]:
        captured["live_accent"] = accent
        return ()

    monkeypatch.setattr(generation_module, "find_matugen", fake_find)
    monkeypatch.setattr(generation_module, "rebuild_config", fake_rebuild)
    monkeypatch.setattr(
        generation_module,
        "invoke_matugen_image",
        fake_invoke_image,
    )
    monkeypatch.setattr(generation_module, "apply_app_integrations", fake_apps)
    monkeypatch.setattr(generation_module, "apply_live_integrations", fake_live)

    _ = generate_once(paths, {"HOME": str(tmp_path)}, "waywallen")

    assert captured["app_accent"] == Accent(236, 20, 19)
    assert captured["live_accent"] == "#ec1413"


def test_generate_once_validates_all_staging_before_publishing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _paths(tmp_path)
    first = _registration(tmp_path, "first")
    second = _registration(tmp_path, "second", saturation=1.5)
    _ = first.output_path.parent.mkdir(parents=True)
    _ = first.output_path.write_text("old-first", encoding="utf-8")
    _ = second.output_path.write_text("old-second", encoding="utf-8")

    def fake_invoke(
        _binary: Path,
        _accent: str,
        _config: Path,
    ) -> MatugenTokens:
        _ = first.staging_path.write_text("{}", encoding="utf-8")
        _ = second.staging_path.write_text("not-json", encoding="utf-8")
        return _tokens()

    _stub_source(
        monkeypatch,
        ThemeSource(kind="kde", reference="#3daee9", accent="#3daee9"),
    )

    def fake_find(_environ: Mapping[str, str]) -> Path | None:
        return _binary(tmp_path)

    def fake_rebuild(
        _config_paths: ThemePaths,
    ) -> tuple[TemplateRegistration, ...]:
        return (first, second)

    monkeypatch.setattr(generation_module, "find_matugen", fake_find)
    monkeypatch.setattr(generation_module, "rebuild_config", fake_rebuild)
    monkeypatch.setattr(generation_module, "invoke_matugen", fake_invoke)
    _stub_empty_integrations(monkeypatch)

    with pytest.raises(GenerationError, match="JSON"):
        _ = generate_once(paths, {"HOME": str(tmp_path)}, "kde")

    assert first.output_path.read_text(encoding="utf-8") == "old-first"
    assert second.output_path.read_text(encoding="utf-8") == "old-second"


def test_generate_once_does_not_publish_when_staging_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _paths(tmp_path)
    registration = _registration(tmp_path, "colors")
    _ = registration.output_path.parent.mkdir(parents=True)
    _ = registration.output_path.write_text("old", encoding="utf-8")

    _stub_source(
        monkeypatch,
        ThemeSource(kind="kde", reference="#3daee9", accent="#3daee9"),
    )

    def fake_find(_environ: Mapping[str, str]) -> Path | None:
        return _binary(tmp_path)

    def fake_rebuild(
        _config_paths: ThemePaths,
    ) -> tuple[TemplateRegistration, ...]:
        return (registration,)

    def fake_invoke(
        _binary: Path,
        _accent: str,
        _config: Path,
    ) -> MatugenTokens:
        return _tokens()

    monkeypatch.setattr(generation_module, "find_matugen", fake_find)
    monkeypatch.setattr(generation_module, "rebuild_config", fake_rebuild)
    monkeypatch.setattr(generation_module, "invoke_matugen", fake_invoke)
    _stub_empty_integrations(monkeypatch)

    with pytest.raises(GenerationError, match="outputs"):
        _ = generate_once(paths, {"HOME": str(tmp_path)}, "kde")

    assert registration.output_path.read_text(encoding="utf-8") == "old"


def test_generate_once_does_not_write_state_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _paths(tmp_path)
    registration = _registration(tmp_path, "colors")

    _stub_source(
        monkeypatch,
        ThemeSource(kind="kde", reference="#3daee9", accent="#3daee9"),
    )

    def fake_find(_environ: Mapping[str, str]) -> Path | None:
        return _binary(tmp_path)

    def fake_rebuild(
        _config_paths: ThemePaths,
    ) -> tuple[TemplateRegistration, ...]:
        return (registration,)

    def fake_invoke(
        _binary: Path,
        _accent: str,
        _config: Path,
    ) -> MatugenTokens:
        return _tokens()

    monkeypatch.setattr(generation_module, "find_matugen", fake_find)
    monkeypatch.setattr(generation_module, "rebuild_config", fake_rebuild)
    monkeypatch.setattr(generation_module, "invoke_matugen", fake_invoke)
    _stub_empty_integrations(monkeypatch)

    with pytest.raises(GenerationError):
        _ = generate_once(paths, {"HOME": str(tmp_path)}, "kde")

    assert not paths.niri_state.exists()


def test_generate_once_waywallen_writes_kde_colors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _paths(tmp_path)
    tokens = _tokens(surface="#101010", primary="#3daee9", source_color="#ec1413")

    _stub_source(
        monkeypatch,
        ThemeSource(kind="waywallen", reference="27", preview=tmp_path / "preview.gif"),
    )

    def fake_find(_environ: Mapping[str, str]) -> Path | None:
        return _binary(tmp_path)

    def fake_rebuild(
        _config_paths: ThemePaths,
    ) -> tuple[TemplateRegistration, ...]:
        return ()

    def fake_invoke_image(
        _binary: Path,
        _image: Path,
        _config: Path,
    ) -> MatugenTokens:
        return tokens

    monkeypatch.setattr(generation_module, "find_matugen", fake_find)
    monkeypatch.setattr(generation_module, "rebuild_config", fake_rebuild)
    monkeypatch.setattr(
        generation_module,
        "invoke_matugen_image",
        fake_invoke_image,
    )
    _stub_empty_integrations(monkeypatch)

    _ = generate_once(paths, {"HOME": str(tmp_path)}, "waywallen")

    kdeglobals = paths.kde_globals.read_text(encoding="utf-8")
    assert "[Colors:Window]" in kdeglobals
    assert "BackgroundNormal=16,16,16" in kdeglobals
    scheme = paths.kcolor_scheme.read_text(encoding="utf-8")
    assert "ColorScheme=Matugen" in scheme
    assert paths.kde_globals_applied.is_file()


def test_generate_once_kde_restores_the_original_kde_colors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _paths(tmp_path)
    original = (
        "[General]\nAccentColor=169,108,65\n\n"
        "[Colors:Window]\nBackgroundNormal=44,34,29\n"
    )
    _ = paths.kde_globals.parent.mkdir(parents=True, exist_ok=True)
    _ = paths.kde_globals.write_text(original, encoding="utf-8")
    apply_colors(
        KdeGlobalsPaths(
            kdeglobals=paths.kde_globals,
            backup=paths.kde_globals_backup,
            applied=paths.kde_globals_applied,
        ),
        _tokens(surface="#101010").colors,
    )
    assert "BackgroundNormal=16,16,16" in paths.kde_globals.read_text(
        encoding="utf-8",
    )

    _stub_source(
        monkeypatch,
        ThemeSource(kind="kde", reference="#3daee9", accent="#3daee9"),
    )

    def fake_find(_environ: Mapping[str, str]) -> Path | None:
        return _binary(tmp_path)

    def fake_rebuild(
        _config_paths: ThemePaths,
    ) -> tuple[TemplateRegistration, ...]:
        return ()

    def fake_invoke(
        _binary: Path,
        _accent: str,
        _config: Path,
    ) -> MatugenTokens:
        return _tokens()

    monkeypatch.setattr(generation_module, "find_matugen", fake_find)
    monkeypatch.setattr(generation_module, "rebuild_config", fake_rebuild)
    monkeypatch.setattr(generation_module, "invoke_matugen", fake_invoke)
    _stub_empty_integrations(monkeypatch)

    _ = generate_once(paths, {"HOME": str(tmp_path)}, "kde")

    restored = paths.kde_globals.read_text(encoding="utf-8")
    assert "BackgroundNormal=44,34,29" in restored
    assert "AccentColor=169,108,65" in restored
    assert not paths.kde_globals_applied.exists()


def test_generate_once_writes_state_with_deterministic_timestamp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _paths(tmp_path)

    _stub_source(
        monkeypatch,
        ThemeSource(kind="kde", reference="#3daee9", accent="#3daee9"),
    )

    def fake_find(_environ: Mapping[str, str]) -> Path | None:
        return _binary(tmp_path)

    def fake_rebuild(
        _config_paths: ThemePaths,
    ) -> tuple[TemplateRegistration, ...]:
        return ()

    def fake_invoke(
        _binary: Path,
        _accent: str,
        _config: Path,
    ) -> MatugenTokens:
        return _tokens()

    monkeypatch.setattr(generation_module, "find_matugen", fake_find)
    monkeypatch.setattr(generation_module, "rebuild_config", fake_rebuild)
    monkeypatch.setattr(generation_module, "invoke_matugen", fake_invoke)
    _stub_empty_integrations(monkeypatch)

    result = generate_once(
        paths,
        {"HOME": str(tmp_path)},
        "kde",
        generated_at="2026-11-23T20:00:00Z",
    )

    assert result.state.generated_at == "2026-11-23T20:00:00Z"
    document = cast(
        "dict[str, object]",
        json.loads(paths.niri_state.read_text(encoding="utf-8")),
    )
    assert document == {
        "source": "kde",
        "reference": "#3daee9",
        "wallpaperId": None,
        "sourceColor": "#3daee9",
        "generatedAt": "2026-11-23T20:00:00Z",
        "status": "ok",
    }
