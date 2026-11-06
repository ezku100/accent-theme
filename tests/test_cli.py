from __future__ import annotations

import json
import stat
import sys
import tomllib
from typing import TYPE_CHECKING, cast

from accent_theme.cli import main
from accent_theme.transform import boost_saturation

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


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


def write_saturated_registration_source(tmp_path: Path) -> Path:
    """Descriptor como el de OLED: plantilla propia y saturación boosteada."""
    source = tmp_path / "integration" / "theme"
    source.mkdir(parents=True)
    template = source / "quickshell-oled.json"
    _ = template.write_text(
        '{"primary": "{{colors.primary.dark.hex}}"}\n', encoding="utf-8"
    )
    descriptor = source / "accent-theme-oled.toml"
    _ = descriptor.write_text(
        """name = "caparazon-shell-oled"
input_path = "~/.config/accent-theme/templates/oled/quickshell-oled.json"
output_path = "~/.cache/caparazon/colors-oled.json"
saturation = 1.45
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


def make_fake_matugen_output(
    directory: Path,
    document: dict[str, str],
    payload: str,
) -> Path:
    """Crea un Matugen falso que escribe un documento renderizado en cada salida.

    ``payload`` es lo que imprime por stdout, que es lo que el motor parsea
    como roles del esquema.
    """
    binary = directory / "matugen"
    contents = json.dumps(document)
    _ = binary.write_text(
        f"""#!{sys.executable}
import pathlib, sys, tomllib
config = tomllib.loads(pathlib.Path(sys.argv[sys.argv.index("-c") + 1]).read_text())
for template in config.get("templates", {{}}).values():
    output = pathlib.Path(template["output_path"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text({contents!r})
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


def test_cli_doctor_reports_the_coverage_of_the_apps(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    descriptor = write_registration_source(tmp_path)
    binaries = tmp_path / "bin"
    binaries.mkdir()
    _ = make_fake_matugen(binaries, matugen_payload())
    environ = {
        "HOME": str(tmp_path),
        "PATH": str(binaries),
        "MATUGEN": str(binaries / "matugen"),
    }

    assert main(
        [
            "register",
            "--app",
            "caparazon-shell",
            "--descriptor",
            str(descriptor),
        ],
        environ=environ,
    ) == 0
    assert main(["generate"], environ=environ) == 0
    assert main(["doctor"], environ=environ) == 0

    output = capsys.readouterr().out
    assert "cobertura: " in output
    assert "materialgram: ok" in output
    assert "obs: ok" in output
    assert "equibop: ok" in output


def test_cli_generate_applies_the_apps_with_the_token_palette(
    tmp_path: Path,
) -> None:
    """Las apps que no son plantillas reciben la paleta ya calculada."""
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

    exit_code = main(
        ["generate"],
        environ={
            "HOME": str(tmp_path),
            "PATH": str(binaries),
            "MATUGEN": str(binaries / "matugen"),
        },
    )

    assert exit_code == 0
    equibop = (
        tmp_path / ".config" / "equibop" / "themes" / "midnight-accent-kde.theme.css"
    )
    assert "--blue-3: oklch(" in equibop.read_text(encoding="utf-8")
    materialgram = (
        tmp_path / ".config" / "materialgram" / "themes" / "Dinamico.tdesktop-theme"
    )
    assert "COLOR_PURPLE_DARK: #123456;" in materialgram.read_text(encoding="utf-8")


def test_cli_generate_keeps_going_when_an_app_fails(tmp_path: Path) -> None:
    """Una app que falla no detiene a las demás ni al propio generate."""
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

    # Un directorio donde va el tema de EquiBop hace fallar su escritura.
    blocked = tmp_path / ".config" / "equibop" / "themes"
    blocked.mkdir(parents=True)
    _ = (blocked / "midnight-accent-kde.theme.css").mkdir()

    exit_code = main(
        ["generate"],
        environ={
            "HOME": str(tmp_path),
            "PATH": str(binaries),
            "MATUGEN": str(binaries / "matugen"),
        },
    )

    assert exit_code == 0
    materialgram = (
        tmp_path / ".config" / "materialgram" / "themes" / "Dinamico.tdesktop-theme"
    )
    assert materialgram.is_file()


def test_cli_watch_reports_missing_inotifywait(tmp_path: Path) -> None:
    exit_code = main(
        ["watch"],
        environ={"HOME": str(tmp_path), "PATH": ""},
    )

    assert exit_code == 1


def test_cli_register_keeps_the_saturation_key(tmp_path: Path) -> None:
    descriptor = write_saturated_registration_source(tmp_path)

    assert main(
        [
            "register",
            "--app",
            "caparazon-shell-oled",
            "--descriptor",
            str(descriptor),
        ],
        environ={"HOME": str(tmp_path), "PATH": ""},
    ) == 0

    installed = (
        tmp_path
        / ".config"
        / "accent-theme"
        / "templates.d"
        / "caparazon-shell-oled.toml"
    )
    parsed = tomllib.loads(installed.read_text(encoding="utf-8"))
    assert parsed["saturation"] == 1.45


def test_cli_generate_boosts_the_saturation_of_tagged_templates(
    tmp_path: Path,
) -> None:
    descriptor = write_saturated_registration_source(tmp_path)
    assert main(
        [
            "register",
            "--app",
            "caparazon-shell-oled",
            "--descriptor",
            str(descriptor),
        ],
        environ={"HOME": str(tmp_path), "PATH": ""},
    ) == 0

    document = {"primary": "#84cfff", "surface": "#000000"}
    binaries = tmp_path / "bin"
    binaries.mkdir()
    _ = make_fake_matugen_output(binaries, document, matugen_payload())
    output = tmp_path / ".cache" / "caparazon" / "colors-oled.json"

    exit_code = main(
        ["generate"],
        environ={
            "HOME": str(tmp_path),
            "PATH": str(binaries),
            "MATUGEN": str(binaries / "matugen"),
        },
    )

    published = cast(
        "dict[str, str]",
        json.loads(output.read_text(encoding="utf-8")),
    )
    assert exit_code == 0
    assert published == boost_saturation(document, 1.45)
    assert published["primary"] != document["primary"]
    assert published["surface"] == "#000000"


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
        },
    )

    assert exit_code == 0
    assert output.is_file()
    assert output.read_text(encoding="utf-8").strip() == payload.strip()
    assert not staging.exists()
