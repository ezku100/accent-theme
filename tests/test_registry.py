from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from accent_theme.paths import ThemePaths
from accent_theme.registry import (
    RegistryError,
    TemplateRegistration,
    load_registrations,
    rebuild_config,
    render_matugen_config,
)

if TYPE_CHECKING:
    from pathlib import Path


def make_paths(tmp_path: Path) -> ThemePaths:
    return ThemePaths.from_environment(
        {
            "HOME": str(tmp_path),
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
            "XDG_DATA_HOME": str(tmp_path / "data"),
            "XDG_CACHE_HOME": str(tmp_path / "cache"),
        }
    )


def write_descriptor(
    paths: ThemePaths,
    filename: str,
    name: str,
    input_path: Path,
    output_path: Path,
) -> None:
    paths.templates_d_dir.mkdir(parents=True, exist_ok=True)
    descriptor = paths.templates_d_dir / filename
    _ = descriptor.write_text(
        "\n".join(
            (
                f'name = "{name}"',
                f'input_path = "{input_path}"',
                f'output_path = "{output_path}"',
            )
        )
        + "\n",
        encoding="utf-8",
    )


def test_load_registrations_parses_normalized_descriptor(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    template = tmp_path / "config" / "accent-theme" / "templates" / "app" / "theme.json"
    template.parent.mkdir(parents=True)
    _ = template.write_text("{}", encoding="utf-8")
    write_descriptor(
        paths,
        "app.toml",
        "app-matugen",
        template,
        tmp_path / "cache" / "colors.json",
    )

    registrations = load_registrations(paths)

    assert registrations == (
        TemplateRegistration(
            name="app-matugen",
            input_path=template,
            output_path=tmp_path / "cache" / "colors.json",
        ),
    )


def test_load_registrations_expands_home_against_effective_home(
    tmp_path: Path,
) -> None:
    paths = make_paths(tmp_path)
    template = tmp_path / "template.json"
    _ = template.write_text("{}", encoding="utf-8")
    paths.templates_d_dir.mkdir(parents=True, exist_ok=True)
    descriptor = paths.templates_d_dir / "home-app.toml"
    _ = descriptor.write_text(
        """name = "home-app"
input_path = "~/template.json"
output_path = "~/cache/colors.json"
""",
        encoding="utf-8",
    )

    registrations = load_registrations(paths)

    assert registrations == (
        TemplateRegistration(
            name="home-app",
            input_path=template,
            output_path=tmp_path / "cache" / "colors.json",
        ),
    )


def test_load_registrations_rejects_duplicate_names(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    template = tmp_path / "config" / "accent-theme" / "templates" / "app" / "theme.json"
    template.parent.mkdir(parents=True)
    _ = template.write_text("{}", encoding="utf-8")
    write_descriptor(paths, "one.toml", "duplicate", template, tmp_path / "one")
    write_descriptor(paths, "two.toml", "duplicate", template, tmp_path / "two")

    with pytest.raises(RegistryError, match="duplicate"):
        _ = load_registrations(paths)


def test_load_registrations_rejects_missing_template(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    missing = tmp_path / "missing.json"
    write_descriptor(paths, "app.toml", "app-matugen", missing, tmp_path / "output")

    with pytest.raises(RegistryError, match="input_path"):
        _ = load_registrations(paths)


def test_load_registrations_rejects_output_outside_home(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    template = tmp_path / "config" / "accent-theme" / "templates" / "app" / "theme.json"
    template.parent.mkdir(parents=True)
    _ = template.write_text("{}", encoding="utf-8")
    write_descriptor(
        paths,
        "app.toml",
        "app-matugen",
        template,
        tmp_path.parent / "escape",
    )

    with pytest.raises(RegistryError, match="output_path"):
        _ = load_registrations(paths)


def test_render_matugen_config_is_sorted_and_escaped(tmp_path: Path) -> None:
    registrations = (
        TemplateRegistration(
            name="z-app",
            input_path=tmp_path / 'templates"z.json',
            output_path=tmp_path / "cache" / "z.json",
        ),
        TemplateRegistration(
            name="a-app",
            input_path=tmp_path / "templates" / "a.json",
            output_path=tmp_path / "cache" / "a.json",
        ),
    )

    rendered = render_matugen_config(registrations)

    assert rendered.index("[templates.a-app]") < rendered.index("[templates.z-app]")
    assert 'templates\\"z.json' in rendered
    assert rendered.startswith("[config]\nversion_check = false\ncaching = false\n")


def test_rebuild_config_is_idempotent(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    template = tmp_path / "config" / "accent-theme" / "templates" / "app" / "theme.json"
    template.parent.mkdir(parents=True)
    _ = template.write_text("{}", encoding="utf-8")
    write_descriptor(
        paths, "app.toml", "app-matugen", template, tmp_path / "output.json"
    )

    first = rebuild_config(paths)
    first_contents = paths.matugen_config.read_text(encoding="utf-8")
    second = rebuild_config(paths)
    second_contents = paths.matugen_config.read_text(encoding="utf-8")

    assert first == second
    assert first_contents == second_contents
    assert first_contents.count("[templates.app-matugen]") == 1


def test_render_matugen_config_accepts_empty_registration() -> None:
    assert render_matugen_config(()) == (
        "[config]\nversion_check = false\ncaching = false\n"
    )


def test_staging_path_keeps_the_final_extension(tmp_path: Path) -> None:
    registration = TemplateRegistration(
        name="caparazon-shell-matugen",
        input_path=tmp_path / "quickshell-matugen.json",
        output_path=tmp_path / "colors.json",
    )

    assert registration.staging_path == tmp_path / "colors.staging.json"


def test_staging_path_keeps_non_json_extensions(tmp_path: Path) -> None:
    registration = TemplateRegistration(
        name="kitty-matugen",
        input_path=tmp_path / "kitty-matugen.conf",
        output_path=tmp_path / "theme.conf",
    )

    assert registration.staging_path == tmp_path / "theme.staging.conf"
