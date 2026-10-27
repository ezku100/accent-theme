from __future__ import annotations

import stat
import sys
from typing import TYPE_CHECKING

from accent_theme.hooks import (
    build_hook_environment,
    discover_hooks,
    run_hook,
    run_hooks,
)
from accent_theme.matugen import MatugenTokens

if TYPE_CHECKING:
    from pathlib import Path


def make_tokens() -> MatugenTokens:
    return MatugenTokens(
        colors={
            "primary": "#3daee9",
            "secondary": "#6a4c93",
            "tertiary": "#b5651d",
            "outline": "#7a7a7a",
            "on_surface": "#f2f2f2",
            "background": "#101010",
            "surface_variant": "#202020",
            "source_color": "#3daee9",
        }
    )


def write_script(path: Path, body: str) -> None:
    _ = path.write_text(f"#!{sys.executable}\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_build_hook_environment_merges_tokens_and_keeps_base() -> None:
    environment = build_hook_environment(
        make_tokens(),
        {"HOME": "/home/usuario", "PATH": "/usr/bin"},
    )

    assert environment["MATUGEN_ACCENT"] == "#3daee9"
    assert environment["MATUGEN_PRIMARY"] == "#3daee9"
    assert environment["MATUGEN_BG"] == "#101010"
    assert environment["HOME"] == "/home/usuario"
    assert environment["PATH"] == "/usr/bin"


def test_run_hook_passes_matugen_environment_to_script(tmp_path: Path) -> None:
    output = tmp_path / "seen.txt"
    script = tmp_path / "hook.py"
    write_script(
        script,
        "\n".join(
            [
                "import os",
                f"with open({str(output)!r}, 'w', encoding='utf-8') as handle:",
                "    handle.write(os.environ['MATUGEN_ACCENT'])",
            ]
        ),
    )

    result = run_hook(script, build_hook_environment(make_tokens(), {}))

    assert result.status == "ok"
    assert result.returncode == 0
    assert output.read_text(encoding="utf-8") == "#3daee9"


def test_run_hook_reports_timeout_without_raising(tmp_path: Path) -> None:
    script = tmp_path / "slow.py"
    write_script(script, "import time\ntime.sleep(5)")

    result = run_hook(script, {}, timeout=0.05)

    assert result.status == "timeout"
    assert result.returncode is None


def test_run_hook_reports_failure_without_raising(tmp_path: Path) -> None:
    script = tmp_path / "broken.py"
    write_script(script, "raise SystemExit(3)")

    result = run_hook(script, {})

    assert result.status == "failed"
    assert result.returncode == 3


def test_run_hook_skips_missing_script(tmp_path: Path) -> None:
    result = run_hook(tmp_path / "ausente.py", {})

    assert result.status == "skipped"
    assert result.returncode is None


def test_run_hooks_isolates_failure_from_other_hooks(tmp_path: Path) -> None:
    marker = tmp_path / "marker.txt"
    failing = tmp_path / "falla.py"
    working = tmp_path / "funciona.py"
    write_script(failing, "raise SystemExit(1)")
    write_script(working, f"open({str(marker)!r}, 'w', encoding='utf-8').write('ok')")

    results = run_hooks([failing, working], {})

    assert [result.status for result in results] == ["failed", "ok"]
    assert marker.read_text(encoding="utf-8") == "ok"


def test_run_hooks_keeps_going_after_timeout(tmp_path: Path) -> None:
    marker = tmp_path / "marker.txt"
    slow = tmp_path / "lento.py"
    working = tmp_path / "rapido.py"
    write_script(slow, "import time\ntime.sleep(5)")
    write_script(working, f"open({str(marker)!r}, 'w', encoding='utf-8').write('ok')")

    results = run_hooks([slow, working], {}, timeout=0.05)

    assert [result.status for result in results] == ["timeout", "ok"]
    assert marker.read_text(encoding="utf-8") == "ok"


def test_discover_hooks_returns_sorted_python_files(tmp_path: Path) -> None:
    _ = (tmp_path / "b.py").write_text("", encoding="utf-8")
    _ = (tmp_path / "a.py").write_text("", encoding="utf-8")
    _ = (tmp_path / "nota.txt").write_text("", encoding="utf-8")

    discovered = discover_hooks(tmp_path)

    assert [path.name for path in discovered] == ["a.py", "b.py"]


def test_discover_hooks_returns_empty_for_missing_directory(tmp_path: Path) -> None:
    assert discover_hooks(tmp_path / "ausente") == ()
