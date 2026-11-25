"""Pruebas del modo image de Matugen y sus roles obligatorios."""

from __future__ import annotations

import json
import stat
import sys
from typing import TYPE_CHECKING

import pytest

from accent_theme.matugen import (
    REQUIRED_IMAGE_ROLES,
    REQUIRED_ROLES,
    MatugenOutputError,
    invoke_matugen_image,
    parse_matugen_json,
)

if TYPE_CHECKING:
    from pathlib import Path


def _payload(*, include_source_color: bool = True) -> str:
    roles = (*REQUIRED_ROLES, "background", "surface_variant")
    if include_source_color:
        roles = (*roles, "source_color")
    colors = {
        role: {
            "dark": {"color": "#ec1413" if role == "source_color" else "#123456"},
            "default": {"color": "#123456"},
            "light": {"color": "#abcdef"},
        }
        for role in roles
    }
    return json.dumps({"colors": colors})


def test_invoke_matugen_image_builds_exact_command(tmp_path: Path) -> None:
    binary = tmp_path / "matugen"
    arguments = tmp_path / "arguments.json"
    config = tmp_path / "matugen.toml"
    image = tmp_path / "preview.gif"
    _ = config.write_text("[config]\n", encoding="utf-8")
    _ = binary.write_text(
        f"""#!{sys.executable}
import json, sys
with open({str(arguments)!r}, 'w', encoding='utf-8') as handle:
    json.dump(sys.argv[1:], handle)
print({_payload()!r})
""",
        encoding="utf-8",
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)

    tokens = invoke_matugen_image(binary, image, config)

    assert tokens["source_color"] == "#ec1413"
    assert json.loads(arguments.read_text(encoding="utf-8")) == [
        "image",
        str(image),
        "-c",
        str(config),
        "-t",
        "scheme-fidelity",
        "-m",
        "dark",
        "-j",
        "hex",
        "--prefer",
        "saturation",
    ]


def test_parse_matugen_json_requires_source_color_when_requested() -> None:
    with pytest.raises(MatugenOutputError, match="source_color"):
        _ = parse_matugen_json(
            _payload(include_source_color=False),
            required_roles=REQUIRED_IMAGE_ROLES,
        )


def test_parse_matugen_json_validates_source_color_hex() -> None:
    payload = _payload().replace('"#ec1413"', '"rojo"')

    with pytest.raises(MatugenOutputError, match="source_color"):
        _ = parse_matugen_json(
            payload,
            required_roles=REQUIRED_IMAGE_ROLES,
        )


def test_parse_matugen_json_default_roles_remains_backward_compatible() -> None:
    tokens = parse_matugen_json(_payload(include_source_color=False))

    assert tokens["primary"] == "#123456"
    assert "source_color" not in tokens.colors
