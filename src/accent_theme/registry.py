"""Registro declarativo de templates y generación de config.toml para Matugen."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

if TYPE_CHECKING:
    from collections.abc import Iterable

    from accent_theme.paths import ThemePaths

TEMPLATE_NAME_PATTERN: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
REQUIRED_KEYS: Final = frozenset({"name", "input_path", "output_path"})
OPTIONAL_KEYS: Final = frozenset({"saturation"})


class RegistryError(RuntimeError):
    """Error visible en un descriptor o en el registro agregado."""

    @classmethod
    def unreadable(cls, path: Path, error: OSError | UnicodeError) -> RegistryError:
        """Construye el error de lectura de un descriptor."""
        return cls(f"no se pudo leer {path}: {error}")

    @classmethod
    def invalid_line(cls, path: Path, line_number: int) -> RegistryError:
        """Construye el error de una línea TOML mal formada."""
        return cls(f"{path}:{line_number}: se esperaba key = value")

    @classmethod
    def invalid_value(
        cls,
        path: Path,
        line_number: int,
        key: str,
    ) -> RegistryError:
        """Construye el error de un valor TOML no decodificable."""
        return cls(f"{path}:{line_number}: valor no válido para {key}")

    @classmethod
    def non_string_value(
        cls,
        path: Path,
        line_number: int,
        key: str,
    ) -> RegistryError:
        """Construye el error de un valor que no es cadena."""
        return cls(f"{path}:{line_number}: {key} debe ser una cadena")

    @classmethod
    def duplicate_key(cls, path: Path, line_number: int, key: str) -> RegistryError:
        """Construye el error de una clave repetida."""
        return cls(f"{path}:{line_number}: clave duplicada {key}")

    @classmethod
    def missing_keys(cls, path: Path, keys: Iterable[str]) -> RegistryError:
        """Construye el error de claves obligatorias ausentes."""
        names = ", ".join(sorted(keys))
        return cls(f"{path}: faltan claves: {names}")

    @classmethod
    def unknown_keys(cls, path: Path, keys: Iterable[str]) -> RegistryError:
        """Construye el error de claves no soportadas."""
        names = ", ".join(sorted(keys))
        return cls(f"{path}: claves desconocidas: {names}")

    @classmethod
    def invalid_name(cls, path: Path, name: str) -> RegistryError:
        """Construye el error de un nombre de template inválido."""
        return cls(f"{path}: nombre de template inválido: {name}")

    @classmethod
    def duplicate_name(cls, path: Path, name: str, previous: Path) -> RegistryError:
        """Construye el error de un nombre de template repetido."""
        return cls(f"{path}: nombre duplicado {name}; ya existe {previous}")

    @classmethod
    def missing_input(cls, path: Path, input_path: Path) -> RegistryError:
        """Construye el error de un template inexistente."""
        return cls(f"{path}: input_path no existe: {input_path}")

    @classmethod
    def unsafe_output(cls, path: Path, home: Path, output_path: Path) -> RegistryError:
        """Construye el error de una salida fuera del HOME."""
        return cls(f"{path}: output_path debe estar dentro de {home}: {output_path}")

    @classmethod
    def invalid_saturation(cls, path: Path, line_number: int) -> RegistryError:
        """Construye el error de un multiplicador de saturación no válido."""
        return cls(f"{path}:{line_number}: saturation debe ser un número >= 1.0")


@dataclass(frozen=True, slots=True)
class Descriptor:
    """Descriptor TOML ya validado, con sus rutas sin expandir."""

    name: str
    input_path: str
    output_path: str
    saturation: float | None = None


@dataclass(frozen=True, slots=True)
class TemplateRegistration:
    """Template de una app y archivo que Matugen debe producir."""

    name: str
    input_path: Path
    output_path: Path
    saturation: float | None = None

    @property
    def staging_path(self) -> Path:
        """Ruta temporal vecina a la salida final.

        Matugen escribe de forma no atómica, así que publica en ``staging`` y
        el motor renombra al final. La extensión se conserva para que Matugen
        mantenga el formato de salida.
        """
        return self.output_path.with_name(
            f"{self.output_path.stem}.staging{self.output_path.suffix}"
        )


def _parse_saturation(path: Path, line_number: int, value: object) -> float:
    """Valida el multiplicador de saturación de un descriptor."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RegistryError.invalid_saturation(path, line_number)
    saturation = float(value)
    if saturation < 1.0:
        raise RegistryError.invalid_saturation(path, line_number)
    return saturation


def _read_descriptor_lines(
    path: Path,
) -> tuple[dict[str, str], float | None, set[str]]:
    """Lee y decodifica un descriptor, validando cada línea."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise RegistryError.unreadable(path, error) from error

    values: dict[str, str] = {}
    saturation: float | None = None
    seen: set[str] = set()
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise RegistryError.invalid_line(path, line_number)
        key, raw_value = stripped.split("=", 1)
        normalized_key = key.strip()
        try:
            value = cast("object", json.loads(raw_value.strip()))
        except json.JSONDecodeError as error:
            raise RegistryError.invalid_value(
                path,
                line_number,
                normalized_key,
            ) from error
        if normalized_key in seen:
            raise RegistryError.duplicate_key(path, line_number, normalized_key)
        seen.add(normalized_key)
        if normalized_key == "saturation":
            saturation = _parse_saturation(path, line_number, value)
        elif isinstance(value, str):
            values[normalized_key] = value
        else:
            raise RegistryError.non_string_value(path, line_number, normalized_key)
    return values, saturation, seen


def parse_descriptor(path: Path) -> Descriptor:
    """Parsea el subconjunto TOML soportado por los descriptores."""
    values, saturation, seen = _read_descriptor_lines(path)

    missing = REQUIRED_KEYS.difference(values)
    unknown = seen.difference(REQUIRED_KEYS | OPTIONAL_KEYS)
    if missing:
        raise RegistryError.missing_keys(path, missing)
    if unknown:
        raise RegistryError.unknown_keys(path, unknown)
    return Descriptor(
        name=values["name"],
        input_path=values["input_path"],
        output_path=values["output_path"],
        saturation=saturation,
    )


def expand_home_path(raw_path: str, home: Path) -> Path:
    """Resuelve ``~`` y rutas relativas contra el HOME efectivo."""
    if raw_path == "~":
        path = home
    elif raw_path.startswith("~/"):
        path = home / raw_path.removeprefix("~/")
    else:
        path = Path(raw_path)
    if not path.is_absolute():
        path = home / path
    return path.resolve(strict=False)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        _ = path.relative_to(parent)
    except ValueError:
        return False
    return True


def load_registrations(paths: ThemePaths) -> tuple[TemplateRegistration, ...]:
    """Carga y valida todos los descriptores de ``templates.d``."""
    if not paths.templates_d_dir.is_dir():
        return ()

    registrations: list[TemplateRegistration] = []
    names: dict[str, Path] = {}
    for descriptor_path in sorted(paths.templates_d_dir.glob("*.toml")):
        descriptor = parse_descriptor(descriptor_path)
        name = descriptor.name
        if TEMPLATE_NAME_PATTERN.fullmatch(name) is None:
            raise RegistryError.invalid_name(descriptor_path, name)
        if name in names:
            raise RegistryError.duplicate_name(descriptor_path, name, names[name])
        input_path = expand_home_path(descriptor.input_path, paths.home)
        output_path = expand_home_path(descriptor.output_path, paths.home)
        if not input_path.is_file():
            raise RegistryError.missing_input(descriptor_path, input_path)
        if not _is_within(output_path, paths.home):
            raise RegistryError.unsafe_output(descriptor_path, paths.home, output_path)
        names[name] = descriptor_path
        registrations.append(
            TemplateRegistration(
                name=name,
                input_path=input_path,
                output_path=output_path,
                saturation=descriptor.saturation,
            )
        )
    return tuple(registrations)


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_matugen_config(registrations: Iterable[TemplateRegistration]) -> str:
    """Renderiza un ``config.toml`` completo y determinista."""
    lines = [
        "[config]",
        "version_check = false",
        "caching = false",
    ]
    for registration in sorted(registrations, key=lambda item: item.name):
        lines.extend(
            (
                "",
                f"[templates.{registration.name}]",
                f"input_path = {_toml_string(str(registration.input_path))}",
                f"output_path = {_toml_string(str(registration.staging_path))}",
            )
        )
    return "\n".join(lines) + "\n"


def _atomic_write(path: Path, contents: str) -> None:
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


def rebuild_config(paths: ThemePaths) -> tuple[TemplateRegistration, ...]:
    """Valida el registro y regenera el config atomicamente."""
    registrations = load_registrations(paths)
    _atomic_write(paths.matugen_config, render_matugen_config(registrations))
    return registrations
