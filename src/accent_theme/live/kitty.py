"""Recarga en vivo de las instancias de Kitty."""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING, Final

from accent_theme.live.base import LiveResult

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

KITTY_SOCKET_PATTERN: Final = "kitty-socket-*"
KITTY_TIMEOUT_SECONDS: Final = 3.0


def _kitty_binary(environ: Mapping[str, str]) -> str | None:
    """Localiza el ejecutable de Kitty en el PATH efectivo."""
    return shutil.which("kitty", path=environ.get("PATH", ""))


def reload_kitty(
    theme: Path,
    socket_dir: Path,
    environ: Mapping[str, str],
) -> LiveResult:
    """Aplica el theme de Kitty a cada socket activo."""
    if not theme.is_file():
        return LiveResult(app="kitty", status="skipped", detail="sin theme.conf")
    binary = _kitty_binary(environ)
    if binary is None:
        return LiveResult(app="kitty", status="skipped", detail="kitty no instalado")
    sockets = sorted(socket_dir.glob(KITTY_SOCKET_PATTERN))
    if not sockets:
        return LiveResult(app="kitty", status="skipped", detail="sin sockets activos")

    applied = 0
    failures = 0
    for socket in sockets:
        command = [
            binary,
            "@",
            "--to",
            f"unix:{socket}",
            "set-colors",
            "-a",
            str(theme),
        ]
        try:
            process = subprocess.run(  # noqa: S603
                command,
                capture_output=True,
                text=True,
                timeout=KITTY_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            failures += 1
            continue
        if process.returncode == 0:
            applied += 1
        else:
            failures += 1

    if failures:
        return LiveResult(
            app="kitty",
            status="failed",
            detail=f"{applied} sockets actualizados, {failures} fallaron",
        )
    return LiveResult(
        app="kitty",
        status="applied",
        detail=f"{applied} sockets actualizados",
    )
