"""Interfaz de línea de comandos del motor accent-theme."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Final

from accent_theme.accent import accent_to_hex, read_kde_accent
from accent_theme.hooks import (
    build_hook_environment,
    discover_hooks,
    format_results,
    resolve_hooks_dir,
    resolve_support_dir,
    run_hooks,
)
from accent_theme.live import LivePaths, apply_live_integrations
from accent_theme.matugen import (
    MatugenError,
    find_matugen,
    invoke_matugen,
)
from accent_theme.paths import ThemePaths
from accent_theme.registry import (
    RegistryError,
    expand_home_path,
    parse_descriptor,
    rebuild_config,
)
from accent_theme.watcher import (
    DEFAULT_GENERATE_COMMAND,
    Watcher,
    WatcherError,
    WatcherPaths,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

APP_NAME_PATTERN: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
WAYWALLEN_CONFIG_RELATIVE: Final = (
    ".var/app/org.waywallen.waywallen/config/waywallen/config.toml"
)


class CliError(RuntimeError):
    """Error de uso con mensaje accionable para el usuario."""

    @classmethod
    def missing_template(cls, template_name: str, descriptor_path: Path) -> CliError:
        """Construye el error de template ausente."""
        return cls(
            f"no se encontró el template {template_name} junto a {descriptor_path}"
        )

    @classmethod
    def invalid_app(cls, app: str) -> CliError:
        """Construye el error de aplicación inválida."""
        return cls(f"nombre de aplicación inválido: {app}")

    @classmethod
    def missing_descriptor(cls, descriptor_path: Path) -> CliError:
        """Construye el error de descriptor ausente."""
        return cls(f"descriptor no encontrado: {descriptor_path}")

    @classmethod
    def missing_matugen(cls) -> CliError:
        """Construye el error de Matugen ausente."""
        return cls(
            "matugen no encontrado; instala matugen o define MATUGEN con su ruta"
        )

    @classmethod
    def missing_outputs(cls, output_paths: list[str]) -> CliError:
        """Construye el error de outputs no generados."""
        missing = ", ".join(output_paths)
        return cls(f"Matugen no creó los outputs esperados: {missing}")

    @classmethod
    def missing_option_value(cls, option: str) -> CliError:
        """Construye el error de opción sin valor."""
        return cls(f"falta el valor de {option}")

    @classmethod
    def unknown_command(cls, command: str) -> CliError:
        """Construye el error de comando no soportado."""
        return cls(f"comando desconocido: {command}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="accent-theme",
        description="Motor global de tema KDE basado en AccentColor y Matugen",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    _ = subparsers.add_parser(
        "generate",
        help="genera la paleta con el acento actual de KDE",
    )

    _ = subparsers.add_parser(
        "rebuild-config",
        help="valida el registro y regenera matugen.toml",
    )

    register = subparsers.add_parser(
        "register",
        help="registra el template y descriptor de una aplicación",
    )
    _ = register.add_argument(
        "--app",
        required=True,
        help="identificador de la aplicación",
    )
    _ = register.add_argument(
        "--descriptor",
        required=True,
        type=Path,
        help="descriptor TOML de la aplicación",
    )

    _ = subparsers.add_parser(
        "doctor",
        help="comprueba dependencias, registro y outputs",
    )

    _ = subparsers.add_parser(
        "watch",
        help="vigila AccentColor y regenera la paleta cuando cambia",
    )
    return parser


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with source.open("rb") as source_handle, os.fdopen(descriptor, "wb") as handle:
            _ = shutil.copyfileobj(source_handle, handle)
        _ = temporary_path.replace(destination)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise


def _atomic_write_text(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            _ = handle.write(contents)
        _ = temporary_path.replace(path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _find_source_template(
    descriptor_path: Path,
    input_path: str,
    home: Path,
) -> Path:
    template_name = Path(input_path).name
    sibling = descriptor_path.parent / template_name
    if sibling.is_file():
        return sibling
    expanded = expand_home_path(input_path, home)
    if expanded.is_file():
        return expanded
    raise CliError.missing_template(template_name, descriptor_path)


def _handle_register(
    paths: ThemePaths,
    app: str,
    descriptor_path: Path,
) -> int:
    descriptor_path = descriptor_path.expanduser().resolve(strict=False)
    if APP_NAME_PATTERN.fullmatch(app) is None:
        raise CliError.invalid_app(app)
    if not descriptor_path.is_file():
        raise CliError.missing_descriptor(descriptor_path)

    values = parse_descriptor(descriptor_path)
    source_template = _find_source_template(
        descriptor_path,
        values["input_path"],
        paths.home,
    )
    template_name = source_template.name
    installed_template = paths.templates_dir / app / template_name
    output_path = expand_home_path(values["output_path"], paths.home)

    _atomic_copy(source_template, installed_template)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    installed_descriptor = paths.templates_d_dir / f"{app}.toml"
    descriptor_contents = "\n".join(
        (
            f"name = {_toml_string(values['name'])}",
            f"input_path = {_toml_string(str(installed_template))}",
            f"output_path = {_toml_string(str(output_path))}",
            "",
        )
    )
    _atomic_write_text(installed_descriptor, descriptor_contents)
    registrations = rebuild_config(paths)
    _ = sys.stdout.write(
        f"registrado {values['name']} ({len(registrations)} integraciones activas)\n"
    )
    return 0


def _handle_rebuild_config(paths: ThemePaths) -> int:
    registrations = rebuild_config(paths)
    _ = sys.stdout.write(f"config generado con {len(registrations)} integraciones\n")
    return 0


def _handle_generate(
    paths: ThemePaths,
    environ: Mapping[str, str],
) -> int:
    binary = find_matugen(environ)
    if binary is None:
        raise CliError.missing_matugen()

    registrations = rebuild_config(paths)
    for registration in registrations:
        registration.output_path.parent.mkdir(parents=True, exist_ok=True)

    kdeglobals = paths.config_home.parent / "kdeglobals"
    accent = accent_to_hex(read_kde_accent(kdeglobals, environ))
    tokens = invoke_matugen(binary, accent, paths.matugen_config)
    for registration in registrations:
        if registration.staging_path.exists():
            _ = registration.staging_path.replace(registration.output_path)
    missing_outputs = [
        str(registration.output_path)
        for registration in registrations
        if not registration.output_path.is_file()
    ]
    if missing_outputs:
        raise CliError.missing_outputs(missing_outputs)

    hook_results = run_hooks(
        discover_hooks(resolve_hooks_dir(environ)),
        build_hook_environment(tokens, environ),
    )
    live_results = apply_live_integrations(
        LivePaths.from_environment(environ),
        accent,
        environ,
    )
    failed_hooks = [result for result in hook_results if not result.succeeded]
    failed_live = [result for result in live_results if result.status == "failed"]
    for result in failed_hooks:
        _ = sys.stderr.write(f"hook fallido {result.name}: {result.stderr}\n")
    for result in failed_live:
        _ = sys.stderr.write(f"recarga fallida {result.app}: {result.detail}\n")

    _ = sys.stdout.write(
        f"paleta generada con {accent}; {len(tokens.colors)} roles disponibles\n"
    )
    _ = sys.stdout.write(f"hooks: {format_results(hook_results)}\n")
    _ = sys.stdout.write(
        "recargas: "
        + "; ".join(f"{result.app}: {result.status}" for result in live_results)
        + "\n"
    )
    return 0


def _watcher_paths(paths: ThemePaths) -> WatcherPaths:
    """Construye las rutas que vigila el watcher."""
    waywallen = paths.home / WAYWALLEN_CONFIG_RELATIVE
    return WatcherPaths(
        kdeglobals=paths.config_home.parent / "kdeglobals",
        cache_path=paths.cache_home / "last-watch-accent",
        lock_path=paths.cache_home / "feeder.lock",
        waywallen_config=waywallen if waywallen.is_file() else None,
    )


def _derive_command(environ: Mapping[str, str]) -> tuple[str, ...] | None:
    """Construye el comando que deriva el acento desde Waywallen."""
    driver = resolve_support_dir(environ) / "derive_waywallen_accent.py"
    if not driver.is_file():
        return None
    return (sys.executable, str(driver))


def _handle_watch(
    paths: ThemePaths,
    environ: Mapping[str, str],
) -> int:
    watcher = Watcher(
        paths=_watcher_paths(paths),
        environ=environ,
        generate_command=DEFAULT_GENERATE_COMMAND,
        derive_command=_derive_command(environ),
    )
    try:
        _ = watcher.watch()
    except WatcherError as error:
        raise CliError(str(error)) from error
    return 0


def _handle_doctor(
    paths: ThemePaths,
    environ: Mapping[str, str],
) -> int:
    problems: list[str] = []
    binary = find_matugen(environ)
    if binary is None:
        problems.append("matugen no encontrado")
    else:
        _ = sys.stdout.write(f"matugen: {binary}\n")
    if not paths.matugen_config.is_file():
        problems.append(f"config ausente: {paths.matugen_config}")
    else:
        _ = sys.stdout.write(f"config: {paths.matugen_config}\n")

    try:
        registrations = rebuild_config(paths)
    except RegistryError as error:
        problems.append(str(error))
        registrations = ()
    problems.extend(
        f"output ausente: {registration.output_path}"
        for registration in registrations
        if not registration.output_path.is_file()
    )

    if problems:
        for problem in problems:
            _ = sys.stderr.write(f"problema: {problem}\n")
        return 1
    _ = sys.stdout.write(f"doctor: {len(registrations)} integraciones correctas\n")
    return 0


def _option_value(arguments: Sequence[str], option: str) -> str:
    for index, argument in enumerate(arguments):
        if argument != option:
            continue
        if index + 1 >= len(arguments):
            raise CliError.missing_option_value(option)
        return arguments[index + 1]
    raise CliError.missing_option_value(option)


def _dispatch(
    command: str,
    argument_list: Sequence[str],
    paths: ThemePaths,
    environ: Mapping[str, str],
) -> int:
    """Ejecuta el subcomando solicitado."""
    match command:
        case "generate":
            return _handle_generate(paths, environ)
        case "watch":
            return _handle_watch(paths, environ)
        case "doctor":
            return _handle_doctor(paths, environ)
        case "rebuild-config":
            return _handle_rebuild_config(paths)
        case "register":
            app = _option_value(argument_list, "--app")
            descriptor = Path(_option_value(argument_list, "--descriptor"))
            return _handle_register(paths, app, descriptor)
        case _:
            raise CliError.unknown_command(command)


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    """Ejecuta la CLI y devuelve su código de salida."""
    effective_environ = os.environ if environ is None else environ
    argument_list = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    _ = parser.parse_args(argument_list)
    if not argument_list:
        parser.print_help()
        return 2
    paths = ThemePaths.from_environment(effective_environ)
    command = argument_list[0]
    try:
        return _dispatch(command, argument_list, paths, effective_environ)
    except (CliError, MatugenError, RegistryError, OSError) as error:
        _ = sys.stderr.write(f"accent-theme: {error}\n")
        return 1
