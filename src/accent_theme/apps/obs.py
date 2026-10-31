"""Tema "Dinamico" para OBS Studio.

OBS no tiene un tema propio: el archivo ``.obt`` es un bundle de Qt con
el QSS dentro. Este módulo parte de un tema base, lo renombra y sustituye
las cinco ranuras de acento por los tonos derivados del acento de KDE.

Hay dos bases posibles. La primera es el tema Venom de FM.VENOM instalado
en la máquina, que da un tema mucho más trabajado; la segunda es
``templates/obs/base.obt``, del propio repo, para que OBS quede temado
también en una instalación limpia donde no esté Venom.

Los naranjas que el autor dejó escritos a mano en el cuerpo del QSS
(textos de menú, handles de sliders, bordes del mezclador) también se
sustituyen. Los verdes, rojos y amarillos de los medidores son semánticos
y se conservan.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from accent_theme.accent import HSV, hsv_to_hex
from accent_theme.apps.base import AppResult, atomic_write_text


def accent_scale(hue: float, saturation: float, value: float) -> tuple[str, ...]:
    """Deriva los cinco naranjas del tema a partir del acento."""
    return (
        hsv_to_hex(hue, max(0.10, saturation - 0.25), min(1.0, value + 0.12)),
        hsv_to_hex(hue, max(0.10, saturation - 0.12), min(1.0, value + 0.06)),
        hsv_to_hex(hue, saturation, value),
        hsv_to_hex(hue, min(1.0, saturation + 0.05), max(0.15, value - 0.15)),
        hsv_to_hex(hue, min(1.0, saturation + 0.08), max(0.10, value - 0.30)),
    )


def _meta_value(content: str, field: str) -> str:
    """Devuelve el valor de un campo del bloque ``@OBSThemeMeta``."""
    match = re.search(rf"{field}:\s*'([^']*)'\s*;", content)
    return match.group(1) if match else ""


def _rename_meta(content: str) -> str:
    """Pone el nombre y la autoría del tema generado.

    La autoría menciona la base solo cuando es de otro autor: así el tema
    propio del repo no se presenta como derivado de nada.
    """
    base_author = _meta_value(content, "author")
    author = "Dinamico (accent KDE)"
    if base_author and base_author != "accent-theme":
        author = f"Dinamico (accent KDE, base {base_author})"
    content = re.sub(r"name:\s*'[^']*'\s*;", "name: 'Dinamico';", content, count=1)
    content = re.sub(
        r"id:\s*'[^']*'\s*;",
        "id: 'com.ezku.Dinamico';",
        content,
        count=1,
    )
    return re.sub(r"author:\s*'[^']*'\s*;", f"author: '{author}';", content, count=1)


def _split_vars(content: str) -> tuple[str, str]:
    """Separa el bloque de variables del cuerpo del QSS.

    Los colores sueltos del cuerpo se sustituyen por variables; los del
    bloque de variables son las ranuras de acento y ya se han rellenado.
    """
    start = content.find("@OBSThemeVars")
    if start < 0:
        return "", content
    end = content.find("}", start)
    if end < 0:
        return "", content
    return content[: end + 1], content[end + 1 :]


def render_obs_theme(base: str, shades: tuple[str, ...]) -> str:
    """Aplica los tonos del acento sobre el texto del tema base."""
    content = _rename_meta(base)

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
    head, body = _split_vars(content)
    for old, new in literals.items():
        body = body.replace(old, new)
    return head + body


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


def resolve_base(installed: Path) -> Path:
    """Devuelve la base del repo si la instalada no está."""
    if installed.is_file():
        return installed
    repository = Path(__file__).resolve().parents[3]
    return repository / "templates" / "obs" / "base.obt"


def apply_obs(
    base_path: Path,
    destinations: tuple[Path, ...],
    hsv: HSV,
    fallback_base: Path,
) -> AppResult:
    """Escribe el tema de OBS en todos los destinos válidos.

    Se usa el tema base de la máquina si está; si no, el del repo, para
    que OBS quede temado también en una instalación limpia.
    """
    source = base_path if base_path.is_file() else resolve_base(fallback_base)
    if not source.is_file():
        return AppResult(app="obs", status="skipped", detail="sin tema base")

    base = source.read_text(encoding="utf-8")
    content = render_obs_theme(base, accent_scale(hsv.hue, hsv.saturation, hsv.value))

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
