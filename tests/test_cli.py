from __future__ import annotations

import json
import stat
import sys
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


def matugen_payload() -> str:
    """Payload role-first válido que exige ``parse_matugen_json``."""
    roles = (
        "surface",
        "surface_container_lowest",
        "surface_container_low",
        "surface_container",
        "surface_container_high",
        "surface_container_highest",
        "on_surface",
        "on_surface_variant",
        "outline",
        "outline_variant",
        "primary",
        "on_primary",
        "secondary",
        "tertiary",
        "error",
        "error_container",
        "on_error_container",
    )
    return json.dumps(
        {"colors": {role: {"dark": {"color": "#123456"}} for role in roles}}
    )


def make_fake_matugen(directory: Path, payload: str) -> Path:
    """Crea un binario Matugen falso que escribe el payload en cada salida."""
    binary = directory / "matugen"
    _ = binary.write_text(
        f"""#!{sys.executable}
import pathlib, sys, tomllib
config = tomllib.loads(pathlib.Path(sys.argv[sys.argv.index("-c") + 1]).read_text())
for template in config.get("templates", {{}}).values():
    output = pathlib.Path(template["output_path"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text({payload!r})
print({payload!r})
""",
        encoding="utf-8",
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    return binary


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
        tmp_path / ".cache" / "caparazon" / "colors.staging.json"
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


def test_cli_generate_runs_hooks_with_token_environment(tmp_path: Path) -> None:
    descriptor = write_registration_source(tmp_path)
    assert main(
        [
            "register",
            "--app",
            "caparazon-shell",
            "--descriptor",
            str(descriptor),
        ],
        environ={"HOME": str(tmp_path), "PATH": ""},
    ) == 0

    payload = matugen_payload()
    binaries = tmp_path / "bin"
    binaries.mkdir(parents=True)
    _ = make_fake_matugen(binaries, payload)
    output = tmp_path / ".cache" / "caparazon" / "colors.json"
    _ = output.parent.mkdir(parents=True, exist_ok=True)
    _ = output.write_text("{}\n", encoding="utf-8")

    hook_marker = tmp_path / "hook.txt"
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    hook = hooks_dir / "echo_hook.py"
    _ = hook.write_text(
        "\n".join(
            [
                "import os",
                f"with open({str(hook_marker)!r}, 'w', encoding='utf-8') as h:",
                "    h.write(os.environ['MATUGEN_ACCENT'] + '|'",
                "             + os.environ['MATUGEN_PRIMARY'])",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(
        ["generate"],
        environ={
            "HOME": str(tmp_path),
            "PATH": str(binaries),
            "MATUGEN": str(binaries / "matugen"),
            "ACCENT_THEME_HOOKS_DIR": str(hooks_dir),
        },
    )

    assert exit_code == 0
    assert hook_marker.read_text(encoding="utf-8") == "#123456|#123456"


def test_cli_generate_keeps_going_when_a_hook_fails(tmp_path: Path) -> None:
    descriptor = write_registration_source(tmp_path)
    assert main(
        [
            "register",
            "--app",
            "caparazon-shell",
            "--descriptor",
            str(descriptor),
        ],
        environ={"HOME": str(tmp_path), "PATH": ""},
    ) == 0

    payload = matugen_payload()
    binaries = tmp_path / "bin"
    binaries.mkdir(parents=True)
    _ = make_fake_matugen(binaries, payload)
    output = tmp_path / ".cache" / "caparazon" / "colors.json"
    _ = output.parent.mkdir(parents=True, exist_ok=True)
    _ = output.write_text("{}\n", encoding="utf-8")

    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    failing = hooks_dir / "aaa_falla.py"
    _ = failing.write_text("raise SystemExit(2)\n", encoding="utf-8")
    marker = tmp_path / "ok.txt"
    working = hooks_dir / "zzz_funciona.py"
    _ = working.write_text(
        f"open({str(marker)!r}, 'w', encoding='utf-8').write('ok')\n",
        encoding="utf-8",
    )

    exit_code = main(
        ["generate"],
        environ={
            "HOME": str(tmp_path),
            "PATH": str(binaries),
            "MATUGEN": str(binaries / "matugen"),
            "ACCENT_THEME_HOOKS_DIR": str(hooks_dir),
        },
    )

    assert exit_code == 0
    assert marker.read_text(encoding="utf-8") == "ok"


def test_cli_watch_reports_missing_inotifywait(tmp_path: Path) -> None:
    exit_code = main(
        ["watch"],
        environ={"HOME": str(tmp_path), "PATH": ""},
    )

    assert exit_code == 1


def test_cli_generate_publishes_the_output_atomically(tmp_path: Path) -> None:
    descriptor = write_registration_source(tmp_path)
    assert main(
        [
            "register",
            "--app",
            "caparazon-shell",
            "--descriptor",
            str(descriptor),
        ],
        environ={"HOME": str(tmp_path), "PATH": ""},
    ) == 0

    binaries = tmp_path / "bin"
    binaries.mkdir()
    payload = matugen_payload()
    _ = make_fake_matugen(binaries, payload)
    output = tmp_path / ".cache" / "caparazon" / "colors.json"
    staging = output.parent / "colors.staging.json"

    exit_code = main(
        ["generate"],
        environ={
            "HOME": str(tmp_path),
            "PATH": str(binaries),
            "MATUGEN": str(binaries / "matugen"),
            "ACCENT_THEME_HOOKS_DIR": str(tmp_path / "hooks"),
        },
    )

    assert exit_code == 0
    assert output.is_file()
    assert output.read_text(encoding="utf-8").strip() == payload.strip()
    assert not staging.exists()
