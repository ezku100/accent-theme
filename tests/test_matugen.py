from __future__ import annotations

import json
import stat
import sys
from typing import TYPE_CHECKING

import pytest

from accent_theme.matugen import (
    REQUIRED_ROLES,
    MatugenCommandError,
    MatugenNotFoundError,
    MatugenOutputError,
    MatugenTimeoutError,
    find_matugen,
    invoke_matugen,
    parse_matugen_json,
)

if TYPE_CHECKING:
    from pathlib import Path


def make_payload(
    missing_role: str | None = None,
    overrides: dict[str, str] | None = None,
) -> str:
    role_colors = overrides or {}
    colors = {
        role: {
            "dark": {"color": role_colors.get(role, "#123456")},
            "default": {"color": "#123456"},
            "light": {"color": "#abcdef"},
        }
        for role in (*REQUIRED_ROLES, "background", "source_color", "surface_variant")
    }
    if missing_role is not None:
        _ = colors.pop(missing_role)
    return json.dumps({"colors": colors})


def test_parse_matugen_json_reads_role_first_tokens() -> None:
    tokens = parse_matugen_json(make_payload())

    assert tokens["primary"] == "#123456"
    assert tokens["surface"] == "#123456"
    assert tokens.legacy_environment()["MATUGEN_PRIMARY"] == "#123456"
    assert tokens.legacy_environment()["MATUGEN_ACCENT"] == "#123456"


def test_parse_matugen_json_preserves_optional_legacy_roles() -> None:
    tokens = parse_matugen_json(
        make_payload(
            overrides={
                "background": "#101010",
                "source_color": "#abcdef",
                "surface_variant": "#202020",
            }
        )
    )

    assert tokens["background"] == "#101010"
    assert tokens["source_color"] == "#abcdef"
    assert tokens["surface_variant"] == "#202020"
    assert tokens.legacy_environment()["MATUGEN_BG"] == "#101010"
    assert tokens.legacy_environment()["MATUGEN_CARD"] == "#202020"


def test_parse_matugen_json_rejects_malformed_json() -> None:
    with pytest.raises(MatugenOutputError, match="JSON"):
        _ = parse_matugen_json("{no-json")


def test_parse_matugen_json_rejects_missing_quickshell_role() -> None:
    with pytest.raises(MatugenOutputError, match="surface_container_highest"):
        _ = parse_matugen_json(make_payload("surface_container_highest"))


def test_find_matugen_returns_none_when_binary_is_missing(tmp_path: Path) -> None:
    environ = {
        "HOME": str(tmp_path),
        "MATUGEN": str(tmp_path / "missing-matugen"),
        "PATH": "",
    }

    assert find_matugen(environ) is None


def test_find_matugen_prefers_explicit_environment_path(tmp_path: Path) -> None:
    binary = tmp_path / "matugen"
    _ = binary.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)

    assert find_matugen({"MATUGEN": str(binary), "PATH": ""}) == binary


def test_invoke_matugen_uses_custom_config_and_parses_output(
    tmp_path: Path,
) -> None:
    binary = tmp_path / "matugen"
    arguments = tmp_path / "arguments.json"
    config = tmp_path / "matugen.toml"
    _ = config.write_text("[config]\n", encoding="utf-8")
    _ = binary.write_text(
        f"""#!/usr/bin/env python3
import sys
with open({str(arguments)!r}, 'w', encoding='utf-8') as handle:
    handle.write("\\n".join(sys.argv[1:]))
print({make_payload()!r})
""",
        encoding="utf-8",
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)

    tokens = invoke_matugen(binary, "#3daee9", config)

    assert tokens["primary"] == "#123456"
    assert arguments.read_text(encoding="utf-8").splitlines() == [
        "color",
        "hex",
        "#3daee9",
        "-c",
        str(config),
        "-t",
        "scheme-fidelity",
        "-m",
        "dark",
        "-j",
        "hex",
    ]


def test_invoke_matugen_reports_missing_binary(tmp_path: Path) -> None:
    config = tmp_path / "matugen.toml"
    _ = config.write_text("[config]\n", encoding="utf-8")

    with pytest.raises(MatugenNotFoundError, match="no encontrado"):
        _ = invoke_matugen(tmp_path / "missing", "#3daee9", config)


def test_invoke_matugen_reports_command_failure(tmp_path: Path) -> None:
    binary = tmp_path / "matugen"
    config = tmp_path / "matugen.toml"
    _ = config.write_text("[config]\n", encoding="utf-8")
    _ = binary.write_text(
        f"""#!{sys.executable}
import sys
print('fallo explicito', file=sys.stderr)
raise SystemExit(7)
""",
        encoding="utf-8",
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)

    with pytest.raises(MatugenCommandError, match="fallo explicito"):
        _ = invoke_matugen(binary, "#3daee9", config)


def test_invoke_matugen_reports_timeout(tmp_path: Path) -> None:
    binary = tmp_path / "matugen"
    config = tmp_path / "matugen.toml"
    _ = config.write_text("[config]\n", encoding="utf-8")
    _ = binary.write_text(
        f"#!{sys.executable}\nimport time\ntime.sleep(1)\n",
        encoding="utf-8",
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)

    with pytest.raises(MatugenTimeoutError, match="tiempo"):
        _ = invoke_matugen(binary, "#3daee9", config, timeout=0.01)
