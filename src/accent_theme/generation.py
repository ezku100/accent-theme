"""Orquestación de una generación completa de tema."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from accent_theme.accent import accent_from_hex, accent_to_hex
from accent_theme.apps import AppPaths, apply_app_integrations
from accent_theme.apps.base import AppResult, atomic_write_text
from accent_theme.kde_globals import (
    KdeGlobalsPaths,
    apply_colors,
    restore_colors,
    write_kcolor_scheme,
)
from accent_theme.live import LivePaths, apply_live_integrations
from accent_theme.matugen import (
    MatugenTokens,
    find_matugen,
    invoke_matugen,
    invoke_matugen_image,
)
from accent_theme.registry import TemplateRegistration, rebuild_config
from accent_theme.sources import ThemeSource, resolve_source
from accent_theme.state import ThemeState, write_state
from accent_theme.transform import boost_saturation

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from accent_theme.apps.base import AppResult
    from accent_theme.live.base import LiveResult
    from accent_theme.paths import ThemePaths


class GenerationError(RuntimeError):
    """Error al generar y publicar una paleta de tema."""

    @classmethod
    def missing_matugen(cls) -> GenerationError:
        """Construye el error de Matugen ausente."""
        return cls(
            "matugen no encontrado; instala matugen o define MATUGEN con su ruta"
        )

    @classmethod
    def missing_outputs(cls, output_paths: list[str]) -> GenerationError:
        """Construye el error de staging ausente."""
        missing = ", ".join(output_paths)
        return cls(f"Matugen no creó los outputs esperados: {missing}")

    @classmethod
    def invalid_staging_json(cls, path: Path) -> GenerationError:
        """Construye el error de un staging JSON inválido."""
        return cls(f"{path}: se esperaba un objeto JSON de token a color")

    @classmethod
    def missing_source_color(cls) -> GenerationError:
        """Construye el error de una fuente sin color utilizable."""
        return cls("la fuente resuelta no tiene un color de acento válido")


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """Resultado completo de una generación publicada."""

    source: ThemeSource
    tokens: MatugenTokens
    source_color: str
    registrations: tuple[TemplateRegistration, ...]
    app_results: tuple[AppResult, ...]
    live_results: tuple[LiveResult, ...]
    state: ThemeState


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_saturated_document(path: Path) -> Mapping[str, str]:
    """Lee un staging de tokens y valida que sea un objeto de cadenas."""
    try:
        raw = cast("object", json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise GenerationError.invalid_staging_json(path) from error
    if not isinstance(raw, dict):
        raise GenerationError.invalid_staging_json(path)
    document = cast("dict[str, object]", raw)
    if not all(isinstance(value, str) for value in document.values()):
        raise GenerationError.invalid_staging_json(path)
    return cast("dict[str, str]", document)


def _validate_staging(
    registrations: tuple[TemplateRegistration, ...],
) -> dict[Path, Mapping[str, str]]:
    missing = [
        str(registration.staging_path)
        for registration in registrations
        if not registration.staging_path.is_file()
    ]
    if missing:
        raise GenerationError.missing_outputs(missing)

    saturated: dict[Path, Mapping[str, str]] = {}
    for registration in registrations:
        if registration.saturation is None:
            continue
        saturated[registration.staging_path] = _read_saturated_document(
            registration.staging_path
        )
    return saturated


def _publish(
    registrations: tuple[TemplateRegistration, ...],
    saturated: dict[Path, Mapping[str, str]],
) -> None:
    for registration in registrations:
        staging = registration.staging_path
        document = saturated.get(staging)
        if document is not None and registration.saturation is not None:
            boosted = boost_saturation(document, registration.saturation)
            atomic_write_text(
                staging,
                json.dumps(boosted, ensure_ascii=False, indent=2) + "\n",
            )
        _ = staging.replace(registration.output_path)


def _source_color(source: ThemeSource, tokens: MatugenTokens) -> str:
    match source.kind:
        case "kde":
            if source.accent is None:
                raise GenerationError.missing_source_color()
            return accent_to_hex(accent_from_hex(source.accent))
        case "waywallen":
            return accent_to_hex(accent_from_hex(tokens["source_color"]))


def _state(
    source: ThemeSource,
    source_color: str,
    generated_at: str | None,
) -> ThemeState:
    match source.kind:
        case "kde":
            return ThemeState(
                source="kde",
                reference=source_color,
                wallpaper_id=None,
                source_color=source_color,
                generated_at=generated_at or _timestamp(),
                status="ok",
            )
        case "waywallen":
            return ThemeState(
                source="waywallen",
                reference=source.reference,
                wallpaper_id=source.reference,
                source_color=source_color,
                generated_at=generated_at or _timestamp(),
                status="ok",
            )


def _sync_kde(
    paths: ThemePaths,
    source: ThemeSource,
    tokens: MatugenTokens,
) -> None:
    """Sincroniza los colores de KDE con la fuente activa.

    Con la fuente KDE manda ``AccentColor``: se devuelve ``kdeglobals`` a
    su bloque original. Con Waywallen se escriben sólo las secciones
    ``[Colors:*]`` y se publica el esquema ``Matugen.colors``.
    """
    kde_paths = KdeGlobalsPaths(
        kdeglobals=paths.kde_globals,
        backup=paths.kde_globals_backup,
        applied=paths.kde_globals_applied,
    )
    match source.kind:
        case "kde":
            _ = restore_colors(kde_paths)
        case "waywallen":
            apply_colors(kde_paths, tokens.colors)
            write_kcolor_scheme(paths.kcolor_scheme, tokens.colors)


def generate_once(
    paths: ThemePaths,
    environ: Mapping[str, str],
    source_request: str = "auto",
    *,
    generated_at: str | None = None,
) -> GenerationResult:
    """Genera, valida y publica una paleta desde la fuente solicitada."""
    source = resolve_source(source_request, paths, environ)
    binary = find_matugen(environ)
    if binary is None:
        raise GenerationError.missing_matugen()

    registrations = rebuild_config(paths)
    for registration in registrations:
        registration.output_path.parent.mkdir(parents=True, exist_ok=True)

    match source.kind:
        case "kde":
            if source.accent is None:
                raise GenerationError.missing_source_color()
            tokens = invoke_matugen(binary, source.accent, paths.matugen_config)
        case "waywallen":
            if source.preview is None:
                raise GenerationError.missing_source_color()
            tokens = invoke_matugen_image(binary, source.preview, paths.matugen_config)

    source_color = _source_color(source, tokens)
    saturated = _validate_staging(registrations)
    _publish(registrations, saturated)
    _sync_kde(paths, source, tokens)

    accent = accent_from_hex(source_color)
    app_results = apply_app_integrations(
        AppPaths.from_environment(environ),
        accent,
        tokens.app_environment(),
    )
    live_results = apply_live_integrations(
        LivePaths.from_environment(environ),
        source_color,
        environ,
    )
    state = _state(source, source_color, generated_at)
    write_state(paths.niri_state, state)
    return GenerationResult(
        source=source,
        tokens=tokens,
        source_color=source_color,
        registrations=registrations,
        app_results=app_results,
        live_results=live_results,
        state=state,
    )
