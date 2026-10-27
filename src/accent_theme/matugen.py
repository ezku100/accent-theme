"""Localización, invocación y parsing de la salida de Matugen 4.x."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

if TYPE_CHECKING:
    from collections.abc import Mapping

HEX_COLOR_PATTERN: Final = re.compile(r"^#[0-9a-fA-F]{6}$")
DEFAULT_TIMEOUT_SECONDS: Final = 60.0
REQUIRED_ROLES: Final = (
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


class MatugenError(RuntimeError):
    """Error base de la integración con Matugen."""


class MatugenNotFoundError(MatugenError):
    """El ejecutable de Matugen no está disponible."""

    @classmethod
    def missing(cls, path: Path) -> MatugenNotFoundError:
        """Construye el error de binario ausente."""
        return cls(f"matugen no encontrado en {path}")


class MatugenCommandError(MatugenError):
    """Matugen terminó con un estado de error."""

    @classmethod
    def failed(cls, returncode: int, detail: str) -> MatugenCommandError:
        """Construye el error de ejecución fallida."""
        message = detail.strip() or f"código de salida {returncode}"
        return cls(f"matugen falló: {message}")


class MatugenTimeoutError(MatugenError):
    """Matugen excedió el tiempo de espera."""

    @classmethod
    def expired(cls, timeout: float) -> MatugenTimeoutError:
        """Construye el error de tiempo de espera agotado."""
        return cls(f"matugen excedió el tiempo de espera de {timeout:g} segundos")


class MatugenOutputError(MatugenError):
    """La salida JSON de Matugen no cumple el contrato esperado."""

    @classmethod
    def malformed_json(cls, detail: str) -> MatugenOutputError:
        """Construye el error de JSON mal formado."""
        return cls(f"JSON inválido de Matugen: {detail}")

    @classmethod
    def missing_role(cls, role: str) -> MatugenOutputError:
        """Construye el error de role ausente."""
        return cls(f"la salida de Matugen no contiene el role requerido {role}")


@dataclass(frozen=True, slots=True)
class MatugenTokens:
    """Tokens hexadecimales del esquema oscuro de Matugen."""

    colors: Mapping[str, str]

    def __getitem__(self, role: str) -> str:
        """Devuelve el color de un role del esquema oscuro."""
        return self.colors[role]

    def legacy_environment(self) -> dict[str, str]:
        """Construye las variables ``MATUGEN_*`` consumidas por hooks legacy."""
        accent = self.colors.get("source_color", self.colors["primary"])
        background = self.colors.get("background", accent)
        card = self.colors.get("surface_variant", accent)
        foreground = self.colors.get(
            "on_secondary_container", self.colors["on_surface"]
        )
        primary = self.colors["primary"]
        secondary = self.colors["secondary"]
        tertiary = self.colors["tertiary"]
        outline = self.colors["outline"]
        return {
            "MATUGEN_ACCENT": accent,
            "MATUGEN_BG": background,
            "MATUGEN_CARD": card,
            "MATUGEN_FG": foreground,
            "MATUGEN_PRIMARY": primary,
            "MATUGEN_SECONDARY": secondary,
            "MATUGEN_TERTIARY": tertiary,
            "MATUGEN_OUTLINE": outline,
            "MATUGEN_BG_OVER": card,
            "MATUGEN_BG_OVER2": outline,
            "MATUGEN_GREY": outline,
            "MATUGEN_ACCENT_LIGHT": primary,
            "MATUGEN_ACCENT_PRESSED": self.colors.get("secondary_container", secondary),
        }


def _as_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return cast("dict[str, object]", value)


def _optional_dark_color(colors: Mapping[str, object], role: str) -> str | None:
    role_value = colors.get(role)
    if role_value is None:
        return None
    role_object = _as_object(role_value)
    dark_value = role_object.get("dark")
    if dark_value is None:
        return None
    dark_object = _as_object(dark_value)
    color = dark_object.get("color")
    if not isinstance(color, str) or HEX_COLOR_PATTERN.fullmatch(color) is None:
        return None
    return color


def _extract_dark_color(colors: Mapping[str, object], role: str) -> str:
    color = _optional_dark_color(colors, role)
    if color is None:
        raise MatugenOutputError.missing_role(role)
    return color


def parse_matugen_json(text: str) -> MatugenTokens:
    """Parsea el JSON role-first de Matugen 4.2 y valida sus roles."""
    try:
        raw = cast("object", json.loads(text))
    except json.JSONDecodeError as error:
        raise MatugenOutputError.malformed_json(str(error)) from error

    root = _as_object(raw)
    colors = _as_object(root.get("colors"))
    parsed = {
        role: color
        for role in colors
        if (color := _optional_dark_color(colors, role)) is not None
    }
    for role in REQUIRED_ROLES:
        _ = _extract_dark_color(colors, role)
    return MatugenTokens(colors=parsed)


def _effective_home(environ: Mapping[str, str]) -> Path:
    return Path(environ.get("HOME", str(Path.home()))).expanduser()


def _executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def find_matugen(environ: Mapping[str, str]) -> Path | None:
    """Busca Matugen en ``$MATUGEN``, ``$PATH`` y el binario local."""
    home = _effective_home(environ)
    explicit = environ.get("MATUGEN")
    if explicit:
        candidate = Path(explicit).expanduser()
        if not candidate.is_absolute():
            candidate = home / candidate
        if _executable(candidate):
            return candidate.resolve(strict=False)

    path_result = shutil.which("matugen", path=environ.get("PATH", ""))
    if path_result is not None:
        candidate = Path(path_result)
        if _executable(candidate):
            return candidate.resolve(strict=False)

    local_candidate = home / ".local" / "bin" / "matugen"
    if _executable(local_candidate):
        return local_candidate.resolve(strict=False)
    return None


def invoke_matugen(
    binary: Path,
    accent: str,
    config: Path,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> MatugenTokens:
    """Ejecuta Matugen con el config propio y devuelve sus tokens validados."""
    if not _executable(binary):
        raise MatugenNotFoundError.missing(binary)

    command = [
        str(binary),
        "color",
        "hex",
        accent,
        "-c",
        str(config),
        "-t",
        "scheme-fidelity",
        "-m",
        "dark",
        "-j",
        "hex",
    ]
    try:
        process = subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise MatugenTimeoutError.expired(timeout) from error
    except OSError as error:
        raise MatugenCommandError.failed(1, str(error)) from error

    if process.returncode != 0:
        detail = process.stderr or process.stdout
        raise MatugenCommandError.failed(process.returncode, detail)
    return parse_matugen_json(process.stdout)
