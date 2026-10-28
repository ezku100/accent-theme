"""El config temporal de matugen debe cumplir el esquema de matugen 4.x."""

from __future__ import annotations

import importlib.util
import subprocess
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Protocol, cast

if TYPE_CHECKING:
    import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = REPOSITORY_ROOT / "hooks" / "active" / "generate_noctalia_theme.py"

TokenGetter = Callable[[str, str], str]


class NoctaliaHook(Protocol):
    """Superficie del hook que usa este test."""

    def matugen_tokens(self, accent: str) -> TokenGetter: ...


def load_hook() -> NoctaliaHook:
    """Importa el hook sin ejecutar ``main``."""
    spec = importlib.util.spec_from_file_location("noctalia_hook", HOOK_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = ModuleType("noctalia_hook")
    module.__file__ = str(HOOK_PATH)
    spec.loader.exec_module(module)
    return cast("NoctaliaHook", cast("object", module))


def test_matugen_config_declares_the_templates_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hook = load_hook()
    seen: list[str] = []

    def fake_run(
        argv: list[str], **_: object
    ) -> subprocess.CompletedProcess[str]:
        config = Path(argv[argv.index("-c") + 1])
        seen.append(config.read_text(encoding="utf-8"))
        return subprocess.CompletedProcess(argv, 0, '{"colors": {}}', "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    _ = hook.matugen_tokens("#a86a40")

    assert len(seen) == 1
    assert "[config]" in seen[0]
    assert "[templates]" in seen[0]
