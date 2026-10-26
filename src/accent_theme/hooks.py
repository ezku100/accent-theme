"""Ejecución aislada de hooks legacy con el entorno de tokens de Matugen."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal

from accent_theme.paths import ThemePaths

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from accent_theme.matugen import MatugenTokens

HOOK_TIMEOUT_SECONDS: Final = 180.0
HOOKS_DIR_VARIABLE: Final = "ACCENT_THEME_HOOKS_DIR"
SUPPORT_DIR_VARIABLE: Final = "ACCENT_THEME_SUPPORT_DIR"
HookStatus = Literal["ok", "failed", "timeout", "skipped"]


@dataclass(frozen=True, slots=True)
class HookResult:
    """Resultado de ejecutar un hook legacy de forma aislada."""

    name: str
    status: HookStatus
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""

    @property
    def succeeded(self) -> bool:
        """Indica si el hook terminó correctamente."""
        return self.status == "ok"


def package_parent() -> Path:
    """Devuelve el directorio que contiene el paquete ``accent_theme``."""
    return Path(__file__).resolve().parents[1]


def repository_root() -> Path:
    """Devuelve la raíz del checkout cuando el motor corre desde el repo."""
    return Path(__file__).resolve().parents[2]


def resolve_hooks_dir(environ: Mapping[str, str]) -> Path:
    """Resuelve el directorio con los hooks activos a ejecutar."""
    override = environ.get(HOOKS_DIR_VARIABLE)
    if override:
        return Path(override).expanduser()
    installed = ThemePaths.from_environment(environ).hooks_active_dir
    if installed.is_dir():
        return installed
    return repository_root() / "hooks" / "active"


def resolve_support_dir(environ: Mapping[str, str]) -> Path:
    """Resuelve el directorio con los scripts de soporte de los hooks."""
    override = environ.get(SUPPORT_DIR_VARIABLE)
    if override:
        return Path(override).expanduser()
    installed = ThemePaths.from_environment(environ).hooks_support_dir
    if installed.is_dir():
        return installed
    return repository_root() / "hooks" / "support"


def build_hook_environment(
    tokens: MatugenTokens,
    base: Mapping[str, str],
) -> dict[str, str]:
    """Construye el entorno de un hook con las variables ``MATUGEN_*``."""
    environment = dict(base)
    environment.update(tokens.legacy_environment())
    package = str(package_parent())
    existing = environment.get("PYTHONPATH", "")
    parts = [package] if not existing else [package, existing]
    environment["PYTHONPATH"] = os.pathsep.join(parts)
    return environment


def discover_hooks(directory: Path) -> tuple[Path, ...]:
    """Lista los hooks Python de un directorio en orden determinista."""
    if not directory.is_dir():
        return ()
    return tuple(sorted(directory.glob("*.py")))


def run_hook(
    script: Path,
    environment: Mapping[str, str],
    *,
    timeout: float = HOOK_TIMEOUT_SECONDS,
) -> HookResult:
    """Ejecuta un hook sin propagar sus fallos al motor."""
    if not script.is_file():
        return HookResult(name=script.name, status="skipped")

    try:
        process = subprocess.run(  # noqa: S603
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=dict(environment),
        )
    except subprocess.TimeoutExpired:
        return HookResult(name=script.name, status="timeout")
    except OSError as error:
        return HookResult(
            name=script.name,
            status="failed",
            stderr=str(error),
        )

    return HookResult(
        name=script.name,
        status="ok" if process.returncode == 0 else "failed",
        returncode=process.returncode,
        stdout=process.stdout.strip(),
        stderr=process.stderr.strip(),
    )


def run_hooks(
    scripts: Iterable[Path],
    environment: Mapping[str, str],
    *,
    timeout: float = HOOK_TIMEOUT_SECONDS,
) -> tuple[HookResult, ...]:
    """Ejecuta todos los hooks; un fallo no impide ejecutar los demás."""
    return tuple(
        run_hook(script, environment, timeout=timeout) for script in scripts
    )


def format_results(results: Sequence[HookResult]) -> str:
    """Resume los resultados de una tanda de hooks en español."""
    if not results:
        return "sin hooks"
    parts = [
        f"{result.name}: {result.status}"
        + (f" (exit={result.returncode})" if result.returncode is not None else "")
        for result in results
    ]
    return "; ".join(parts)
