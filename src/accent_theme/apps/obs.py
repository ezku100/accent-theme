"""Tema "Dinamico" para OBS Studio, derivado del tema Venom de FM.VENOM.

OBS no tiene un tema propio: el archivo ``.obt`` es un bundle de Qt con
el QSS dentro. Este módulo parte del tema Venom instalado en la máquina,
lo renombra y sustituye los naranjas del autor por los tonos del acento.

Los naranjas que el autor dejó escritos a mano en el cuerpo del QSS
(textos de menú, handles de sliders, bordes del mezclador) también se
sustituyen. Los verdes, rojos y amarillos de los medidores son semánticos
y se conservan.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import TYPE_CHECKING

from accent_theme.accent import hsv_to_hex
from accent_theme.apps.base import AppResult, atomic_write_text

if TYPE_CHECKING:
    from pathlib import Path


def accent_scale(hue: float, saturation: float, value: float) -> tuple[str, ...]:
    """Deriva los cinco naranjas del tema a partir del acento."""
    return (
        hsv_to_hex(hue, max(0.10, saturation - 0.25), min(1.0, value + 0.12)),
        hsv_to_hex(hue, max(0.10, saturation - 0.12), min(1.0, value + 0.06)),
        hsv_to_hex(hue, saturation, value),
        hsv_to_hex(hue, min(1.0, saturation + 0.05), max(0.15, value - 0.15)),
        hsv_to_hex(hue, min(1.0, saturation + 0.08), max(0.10, value - 0.30)),
    )


def render_obs_theme(base: str, shades: tuple[str, ...]) -> str:
    """Aplica los tonos del acento sobre el texto del tema base."""
    content = base.replace("name: 'Venom';", "name: 'Dinamico';", 1)
    content = content.replace(
        "id: 'com.obsproject.Venom';",
        "id: 'com.ezku.Dinamico';",
        1,
    )
    content = content.replace(
        "author: 'FM.VENOM';",
        "author: 'Dinamico (accent KDE, base Venom de FM.VENOM)';",
        1,
    )

    for index, shade in enumerate(shades, start=1):
        content = re.sub(
            rf"(--orange{index}:\s*)#[0-9a-fA-F]+",
            rf"\g<1>{shade}",
            content,
        )

    literals = {
        "#ff7f50": "var(--primary)",
        "#ff955b": "var(--primary)",
        "#ffb08a": "var(--primary_lighter)",
        "#ffb26b": "var(--primary)",
        "#ffc49d": "var(--white1)",
        "#fffae5": "var(--white1)",
        "#ffb74d !important": "var(--white1) !important",
    }
    for old, new in literals.items():
        content = content.replace(old, new)
    return content


def _destination_allowed(path: Path) -> bool:
    """No crea la carpeta de una app que no está instalada."""
    return path.parent.parent.is_dir()


def notify_obs() -> None:
    """Avisa por escritorio si OBS está abierto (best effort).

    OBS no recarga el tema solo, así que el aviso evita tener que
    acordarse de alternar el tema a mano.
    """
    pgrep = shutil.which("pgrep")
    if pgrep is None:
        return
    try:
        process = subprocess.run(  # noqa: S603
            [pgrep, "-f", "com.obsproject.Studio"],
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return
    if process.returncode != 0:
        return
    notifier = shutil.which("notify-send")
    if notifier is None:
        return
    try:
        subprocess.run(  # noqa: S603
            [
                notifier,
                "-a",
                "Dinamico",
                "Tema OBS actualizado",
                "Pasá a otro tema y volvé a Dinamico para aplicar el accent.",
            ],
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return


def apply_obs(
    base_path: Path,
    destinations: tuple[Path, ...],
    hue: float,
    saturation: float,
    value: float,
) -> AppResult:
    """Escribe el tema de OBS en todos los destinos válidos."""
    if not base_path.is_file():
        return AppResult(app="obs", status="skipped", detail="sin tema base")

    base = base_path.read_text(encoding="utf-8")
    content = render_obs_theme(base, accent_scale(hue, saturation, value))

    written = 0
    for destination in destinations:
        if not _destination_allowed(destination):
            continue
        try:
            atomic_write_text(destination, content)
        except OSError:
            continue
        written += 1

    if written == 0:
        return AppResult(app="obs", status="skipped", detail="sin destinos")
    notify_obs()
    return AppResult(app="obs", status="applied", detail=f"{written} destinos")
