from __future__ import annotations

import json
import tomllib
from typing import TYPE_CHECKING

from accent_theme.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def write_registration_source(tmp_path: Path) -> Path:
    source = tmp_path / "integration" / "theme"
    source.mkdir(parents=True)
    template = source / "quickshell-matugen.json"
    _ = template.write_text(
        '{"primary": "{{colors.primary.dark.hex}}"}\n', encoding="utf-8"
    )
    descriptor = source / "accent-theme.toml"
    _ = descriptor.write_text(
        """name = "quickshell-matugen"
input_path = "~/.config/accent-theme/templates/caparazon-shell/quickshell-matugen.json"
output_path = "~/.cache/caparazon/colors.json"
""",
        encoding="utf-8",
    )
    return descriptor


def test_cli_register_installs_template_descriptor_and_config(tmp_path: Path) -> None:
    descriptor = write_registration_source(tmp_path)
    environ = {"HOME": str(tmp_path), "PATH": ""}

    exit_code = main(
        [
            "register",
            "--app",
            "caparazon-shell",
            "--descriptor",
            str(descriptor),
        ],
        environ=environ,
    )

    config_home = tmp_path / ".config" / "accent-theme"
    installed_descriptor = config_home / "templates.d" / "caparazon-shell.toml"
    installed_template = (
        config_home / "templates" / "caparazon-shell" / "quickshell-matugen.json"
    )
    generated = config_home / "matugen.toml"
    assert exit_code == 0
    assert installed_descriptor.is_file()
    assert installed_template.is_file()
    assert json.loads(installed_template.read_text(encoding="utf-8")) == {
        "primary": "{{colors.primary.dark.hex}}"
    }
    parsed = tomllib.loads(generated.read_text(encoding="utf-8"))
    assert parsed["templates"]["quickshell-matugen"]["input_path"] == str(
        installed_template
    )
    assert parsed["templates"]["quickshell-matugen"]["output_path"] == str(
        tmp_path / ".cache" / "caparazon" / "colors.json"
    )


def test_cli_rebuild_config_is_idempotent(tmp_path: Path) -> None:
    descriptor = write_registration_source(tmp_path)
    environ = {"HOME": str(tmp_path), "PATH": ""}
    args = [
        "register",
        "--app",
        "caparazon-shell",
        "--descriptor",
        str(descriptor),
    ]

    first = main(args, environ=environ)
    generated = tmp_path / ".config" / "accent-theme" / "matugen.toml"
    first_contents = generated.read_text(encoding="utf-8")
    second = main(["rebuild-config"], environ=environ)
    second_contents = generated.read_text(encoding="utf-8")

    assert first == 0
    assert second == 0
    assert first_contents == second_contents


def test_cli_generate_reports_missing_matugen(tmp_path: Path) -> None:
    exit_code = main(
        ["generate"],
        environ={"HOME": str(tmp_path), "PATH": ""},
    )

    assert exit_code == 1


def test_cli_doctor_reports_missing_matugen(tmp_path: Path) -> None:
    exit_code = main(
        ["doctor"],
        environ={"HOME": str(tmp_path), "PATH": ""},
    )

    assert exit_code == 1
