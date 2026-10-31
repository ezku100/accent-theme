"""Tipos y utilidades compartidos por las integraciones de apps.

Estas apps no encajan en una plantilla de Matugen: escriben su
configuración en sitios donde una plantilla no llega, como un JSON que hay
que fusionar con lo que ya había o un tema que se deriva de otro archivo.
El motor las aplica desde aquí, con el acento y la paleta ya calculados.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

AppStatus = Literal["applied", "skipped", "failed"]
HEX_DIGITS = 6


@dataclass(frozen=True, slots=True)
class AppResult:
    """Resultado de aplicar el tema de una app."""

    app: str
    status: AppStatus
    detail: str = ""


def atomic_write_text(path: Path, contents: str) -> None:
    """Escribe un fichero de forma atómica.

    Las apps leen su configuración mientras están abiertas: escribir a
    medias las deja con el fichero corrupto. Se conservan los permisos que
    ya tenía el fichero; los nuevos se crean como los de un ``open``
    normal.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        mode = path.stat().st_mode & 0o777
    except OSError:
        mode = 0o644
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            _ = handle.write(contents)
        temporary_path.chmod(mode)
        _ = temporary_path.replace(path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise


def atomic_write_json(path: Path, payload: object) -> None:
    """Escribe un JSON de forma atómica, con el formato que usa Chromium."""
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def accent_channels(accent: str) -> tuple[float, float, float]:
    """Convierte un acento hexadecimal a canales RGB normalizados."""
    raw = accent.lstrip("#")
    if len(raw) != HEX_DIGITS:
        message = f"acento inválido: {accent}"
        raise ValueError(message)
    red = int(raw[0:2], 16) / 255
    green = int(raw[2:4], 16) / 255
    blue = int(raw[4:6], 16) / 255
    return red, green, blue
