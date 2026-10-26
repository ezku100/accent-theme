"""Despliegue en vivo del CSS de acento en los perfiles de Zen."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Final

from accent_theme.live.base import LiveResult

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

CSS_NAME: Final = "kde-accent.css"
GENERATED_HEADER: Final = (
    "/* Generado por accent-theme — no editar la línea de import */"
)
IMPORT_LINE: Final = '@import url("kde-accent.css");'
USER_JS_PREFERENCE: Final = (
    'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);'
)
PROFILE_GLOB: Final = "*.Default*"


def _find_profiles(roots: Sequence[Path]) -> tuple[Path, ...]:
    """Devuelve los directorios de perfil de Zen de todas las raíces."""
    profiles: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        profiles.extend(
            path for path in sorted(root.glob(PROFILE_GLOB)) if path.is_dir()
        )
    return tuple(profiles)


def _ensure_import(userchrome: Path) -> None:
    """Agrega el import del CSS al userChrome.css si falta."""
    if userchrome.is_file():
        contents = userchrome.read_text(encoding="utf-8")
        if CSS_NAME in contents:
            return
        with userchrome.open("a", encoding="utf-8") as handle:
            _ = handle.write(f"\n{IMPORT_LINE}\n")
        return
    userchrome.parent.mkdir(parents=True, exist_ok=True)
    _ = userchrome.write_text(
        f"{GENERATED_HEADER}\n{IMPORT_LINE}\n",
        encoding="utf-8",
    )


def _ensure_userjs(profile: Path) -> None:
    """Habilita las hojas de estilo personalizadas en el perfil."""
    userjs = profile / "user.js"
    if userjs.is_file():
        contents = userjs.read_text(encoding="utf-8")
        if "legacyUserProfileCustomizations" in contents:
            return
        with userjs.open("a", encoding="utf-8") as handle:
            _ = handle.write(f"\n// Añadido por accent-theme\n{USER_JS_PREFERENCE}\n")
        return
    _ = userjs.write_text(
        f"// Añadido por accent-theme\n{USER_JS_PREFERENCE}\n",
        encoding="utf-8",
    )


def deploy_zen(css: Path, profile_roots: Sequence[Path]) -> LiveResult:
    """Copia el CSS de acento a cada perfil de Zen y asegura el import."""
    if not css.is_file():
        return LiveResult(app="zen", status="skipped", detail="sin CSS de acento")
    profiles = _find_profiles(profile_roots)
    if not profiles:
        return LiveResult(app="zen", status="skipped", detail="sin perfiles")

    deployed = 0
    for profile in profiles:
        chrome = profile / "chrome"
        chrome.mkdir(parents=True, exist_ok=True)
        _ = shutil.copyfile(css, chrome / CSS_NAME)
        _ensure_import(chrome / "userChrome.css")
        _ensure_userjs(profile)
        deployed += 1
    return LiveResult(
        app="zen",
        status="applied",
        detail=f"{deployed} perfiles actualizados",
    )
