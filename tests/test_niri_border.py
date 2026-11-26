"""Pruebas del borde de niri: lo publica el motor con el acento de la shell."""

from __future__ import annotations

from typing import TYPE_CHECKING

from accent_theme.accent import Accent
from accent_theme.niri_border import (
    border_colors,
    overview_backdrop_color,
    render_border,
    render_niri_accent,
    write_niri_border,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_the_active_border_uses_the_shell_accent() -> None:
    """La ventana activa seCiñe al acento que la shell publica."""
    colors = border_colors(Accent(11, 121, 194))

    assert colors.active == "#0b79c2"


def test_the_inactive_border_is_a_dimmed_variant_of_the_accent() -> None:
    """La ventana inactiva se apaga, pero sin salirse de la familia del acento."""
    colors = border_colors(Accent(255, 255, 255))

    assert colors.inactive != colors.active
    assert colors.inactive.startswith("#")
    assert int(colors.inactive[1:3], 16) < 255


def test_the_snippet_turns_the_border_on_with_the_accent() -> None:
    """El snippet de niri enciende el borde y le da el color de acento."""
    contents = render_border(border_colors(Accent(11, 121, 194)))

    assert "border {" in contents
    assert "\n        on\n" in contents
    assert 'active-color "#0b79c2"' in contents


def test_the_border_is_drawn_thin() -> None:
    """El borde marca la ventana activa con dos píxeles, sin tapar el contenido."""
    contents = render_border(border_colors(Accent(11, 121, 194)))

    assert "\n        width 2\n" in contents


def test_writing_the_border_creates_the_file_and_its_directory(
    tmp_path: Path,
) -> None:
    """El motor deja el snippet listo aunque la carpeta no exista todavía."""
    target = tmp_path / "niri" / "config.d" / "25-border-accent.kdl"

    write_niri_border(target, Accent(11, 121, 194))

    assert target.is_file()
    assert 'active-color "#0b79c2"' in target.read_text(encoding="utf-8")


def test_writing_the_border_leaves_no_temporary_files(tmp_path: Path) -> None:
    """La publicación es atómica: no queda ningún temporal junto al snippet."""
    target = tmp_path / "niri" / "config.d" / "25-border-accent.kdl"

    write_niri_border(target, Accent(11, 121, 194))

    assert [item.name for item in target.parent.iterdir()] == [target.name]


def test_the_overview_backdrop_is_the_accent_dimmed_towards_black() -> None:
    """El fondo del overview es el acento apagado, mezclado con negro."""
    assert overview_backdrop_color(Accent(236, 20, 19)) == "#5e0807"


def test_the_overview_backdrop_is_lowercase_hex() -> None:
    """El color del overview sale en hexadecimal minúsculas."""
    color = overview_backdrop_color(Accent(171, 205, 255))

    assert color is not None
    assert color == color.lower()
    assert len(color) == 7


def test_the_snippet_publishes_the_overview_backdrop_next_to_the_border() -> None:
    """El mismo snippet lleva el borde y el fondo del overview."""
    contents = render_niri_accent(border_colors(Accent(236, 20, 19)), "#5e0807")

    assert 'active-color "#ec1413"' in contents
    assert "overview {" in contents
    assert 'backdrop-color "#5e0807"' in contents


def test_the_snippet_keeps_the_generated_header() -> None:
    """La cabecera avisa de que el fichero lo genera el motor."""
    contents = render_niri_accent(border_colors(Accent(236, 20, 19)), "#5e0807")

    assert contents.startswith("// Generado por accent-theme")


def test_writing_the_accent_publishes_the_border_and_the_overview(
    tmp_path: Path,
) -> None:
    """El motor escribe el borde y el fondo del overview en el mismo snippet."""
    target = tmp_path / "niri" / "config.d" / "25-border-accent.kdl"

    write_niri_border(target, Accent(236, 20, 19))

    contents = target.read_text(encoding="utf-8")
    assert 'active-color "#ec1413"' in contents
    assert 'backdrop-color "#5e0807"' in contents


def test_the_overview_keeps_the_last_published_color_when_the_accent_is_unusable(
    tmp_path: Path,
) -> None:
    """Si el acento no se puede leer, se conserva el último fondo válido."""
    target = tmp_path / "niri" / "config.d" / "25-border-accent.kdl"
    write_niri_border(target, Accent(236, 20, 19))

    write_niri_border(target, Accent(-1, 20, 19))

    contents = target.read_text(encoding="utf-8")
    assert 'backdrop-color "#5e0807"' in contents
    assert 'active-color "#3a3a3a"' in contents


def test_the_overview_falls_back_to_grey_without_a_previous_snippet(
    tmp_path: Path,
) -> None:
    """Sin snippet previo, el fondo del overview usa el gris de respaldo."""
    target = tmp_path / "niri" / "config.d" / "25-border-accent.kdl"

    write_niri_border(target, Accent(-1, 20, 19))

    assert 'backdrop-color "#3a3a3a"' in target.read_text(encoding="utf-8")
