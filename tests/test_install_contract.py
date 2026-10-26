"""Contrato de los templates, descriptores, servicio e instalador del motor."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from accent_theme.registry import parse_descriptor

if TYPE_CHECKING:
    from collections.abc import Mapping

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = REPOSITORY_ROOT / "templates"
DESCRIPTORS_DIR = REPOSITORY_ROOT / "templates.d"
SERVICE_FILE = REPOSITORY_ROOT / "systemd" / "accent-theme.service"
INSTALLER = REPOSITORY_ROOT / "install.sh"
BASE_APPS = (
    "kitty",
    "ghostty",
    "konsole",
    "kate",
    "cava",
    "heroic",
    "zen",
    "steam",
)
REQUIRED_ROLES = (
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


def make_stub(directory: Path, name: str, body: str) -> Path:
    """Crea un ejecutable stub que simula una dependencia externa."""
    binary = directory / name
    _ = binary.write_text(f"#!{sys.executable}\n{body}\n", encoding="utf-8")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    return binary


def make_fake_matugen(directory: Path) -> Path:
    """Crea un Matugen falso que crea los outputs declarados en el config."""
    payload = json.dumps(
        {"colors": {role: {"dark": {"color": "#123456"}} for role in REQUIRED_ROLES}}
    )
    body = "\n".join(
        (
            "import os",
            "import sys",
            "import tomllib",
            "arguments = sys.argv[1:]",
            "config = arguments[arguments.index('-c') + 1]",
            "with open(config, 'rb') as handle:",
            "    parsed = tomllib.load(handle)",
            "for template in parsed.get('templates', {}).values():",
            "    output = os.path.expanduser(template['output_path'])",
            "    os.makedirs(os.path.dirname(output), exist_ok=True)",
            "    with open(output, 'w', encoding='utf-8') as handle:",
            "        handle.write('generado')",
            f"print({payload!r})",
        )
    )
    return make_stub(directory, "matugen", body)


def make_fake_systemctl(directory: Path, log: Path) -> Path:
    """Crea un ``systemctl`` falso que registra las llamadas del instalador."""
    body = "\n".join(
        (
            "import sys",
            f"with open({str(log)!r}, 'a', encoding='utf-8') as handle:",
            "    handle.write(' '.join(sys.argv[1:]) + '\\n')",
        )
    )
    return make_stub(directory, "systemctl", body)


def install_environment(
    tmp_path: Path,
    *,
    hooks_dir: Path,
) -> tuple[dict[str, str], Path]:
    """Prepara un entorno aislado con dependencias simuladas."""
    home = tmp_path / "home"
    binaries = tmp_path / "bin"
    binaries.mkdir(parents=True)
    home.mkdir()
    _ = make_fake_matugen(binaries)
    log = tmp_path / "systemctl.log"
    _ = make_fake_systemctl(binaries, log)
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    environ = {
        "HOME": str(home),
        "PATH": f"{binaries}:/usr/bin:/bin",
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_RUNTIME_DIR": str(runtime_dir),
        "ACCENT_THEME_HOOKS_DIR": str(hooks_dir),
    }
    return environ, log


def run_installer(
    action: str,
    environ: Mapping[str, str],
) -> subprocess.CompletedProcess[str]:
    """Ejecuta el instalador con la acción indicada."""
    return subprocess.run(  # noqa: S603
        [str(INSTALLER), action],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
        env=dict(environ),
    )


def test_service_unit_watches_the_accent_color() -> None:
    contents = SERVICE_FILE.read_text(encoding="utf-8")

    assert "ExecStart=" in contents
    assert "accent-theme watch" in contents
    assert "WantedBy=default.target" in contents
    assert "[Service]" in contents
    assert "[Install]" in contents


def test_base_descriptors_are_complete() -> None:
    for app in BASE_APPS:
        descriptor = DESCRIPTORS_DIR / f"{app}.toml"
        assert descriptor.is_file(), f"falta el descriptor de {app}"
        values = parse_descriptor(descriptor)
        assert values["name"]
        assert values["input_path"].startswith("~/.config/accent-theme/templates/")
        assert values["output_path"].startswith("~/")


def test_every_descriptor_points_to_an_installed_template() -> None:
    for app in BASE_APPS:
        values = parse_descriptor(DESCRIPTORS_DIR / f"{app}.toml")
        template_name = Path(values["input_path"]).name
        template = TEMPLATES_DIR / app / template_name
        assert template.is_file(), f"falta el template {template}"


def test_every_template_has_a_descriptor() -> None:
    referenced = {
        Path(parse_descriptor(DESCRIPTORS_DIR / f"{app}.toml")["input_path"]).name
        for app in BASE_APPS
    }
    shipped = {
        path.name
        for app in BASE_APPS
        for path in (TEMPLATES_DIR / app).glob("*")
        if path.is_file()
    }

    assert shipped == referenced


def test_descriptor_names_are_unique() -> None:
    names = [
        parse_descriptor(DESCRIPTORS_DIR / f"{app}.toml")["name"] for app in BASE_APPS
    ]

    assert len(set(names)) == len(names)


def test_installer_supports_both_actions() -> None:
    contents = INSTALLER.read_text(encoding="utf-8")

    assert "instalar" in contents
    assert "desinstalar" in contents
    assert os.access(INSTALLER, os.X_OK)


def test_install_prepares_the_engine_and_migrates_the_service(
    tmp_path: Path,
) -> None:
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    environ, log = install_environment(tmp_path, hooks_dir=hooks_dir)

    result = run_installer("instalar", environ)

    home = tmp_path / "home"
    assert result.returncode == 0, result.stderr
    wrapper = home / ".local" / "bin" / "accent-theme"
    assert wrapper.is_file()
    assert os.access(wrapper, os.X_OK)
    assert (
        home / ".config" / "systemd" / "user" / "accent-theme.service"
    ).is_file()
    assert (home / ".config" / "accent-theme" / "matugen.toml").is_file()
    for app in BASE_APPS:
        assert (
            home / ".config" / "accent-theme" / "templates.d" / f"{app}.toml"
        ).is_file()
    assert (home / ".config" / "kitty" / "theme.conf").is_file()

    calls = log.read_text(encoding="utf-8")
    assert "disable --now kitty-theme-watch.service" in calls
    assert "enable --now accent-theme.service" in calls


def test_install_is_idempotent(tmp_path: Path) -> None:
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    environ, _ = install_environment(tmp_path, hooks_dir=hooks_dir)

    first = run_installer("instalar", environ)
    second = run_installer("instalar", environ)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    descriptors = sorted(
        path.name
        for path in (
            tmp_path / "home" / ".config" / "accent-theme" / "templates.d"
        ).glob("*.toml")
    )
    assert descriptors == sorted(f"{app}.toml" for app in BASE_APPS)


def test_uninstall_restores_the_legacy_service(tmp_path: Path) -> None:
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    environ, log = install_environment(tmp_path, hooks_dir=hooks_dir)
    _ = run_installer("instalar", environ)

    result = run_installer("desinstalar", environ)

    home = tmp_path / "home"
    assert result.returncode == 0, result.stderr
    assert not (home / ".local" / "bin" / "accent-theme").exists()
    calls = log.read_text(encoding="utf-8")
    assert "disable --now accent-theme.service" in calls
    assert "enable --now kitty-theme-watch.service" in calls


def test_install_reports_missing_dependencies(tmp_path: Path) -> None:
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    home = tmp_path / "home"
    binaries = tmp_path / "bin"
    binaries.mkdir(parents=True)
    home.mkdir()
    environ = {
        "HOME": str(home),
        "PATH": str(binaries),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "ACCENT_THEME_HOOKS_DIR": str(hooks_dir),
    }

    result = run_installer("instalar", environ)

    assert result.returncode != 0
    assert "matugen" in result.stderr


def test_installer_rejects_unknown_actions(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    result = subprocess.run(  # noqa: S603
        [str(INSTALLER), "otra-cosa"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env={"HOME": str(home), "PATH": "/usr/bin:/bin"},
    )

    assert result.returncode != 0
    assert "instalar" in result.stderr


def test_generated_config_lists_every_base_app(tmp_path: Path) -> None:
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    environ, _ = install_environment(tmp_path, hooks_dir=hooks_dir)
    _ = run_installer("instalar", environ)

    config = (
        tmp_path / "home" / ".config" / "accent-theme" / "matugen.toml"
    ).read_text(encoding="utf-8")
    names = [
        parse_descriptor(DESCRIPTORS_DIR / f"{app}.toml")["name"] for app in BASE_APPS
    ]

    for name in names:
        assert f"[templates.{name}]" in config
