from __future__ import annotations

import stat
import time
from typing import TYPE_CHECKING

from accent_theme.watcher import (
    DEFAULT_GENERATE_COMMAND,
    LOCK_BUSY_EXIT_CODE,
    WATCH_EVENTS,
    Watcher,
    WatcherPaths,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path


def make_script(path: Path, body: str) -> None:
    _ = path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def make_fake_flock(directory: Path, *, busy: bool = False) -> Path:
    """Crea un ``flock`` falso compatible con la invocación del watcher."""
    binary = directory / "flock"
    body = f"exit {LOCK_BUSY_EXIT_CODE}" if busy else 'shift 4\nexec "$@"'
    make_script(binary, body)
    return binary


def make_environment(tmp_path: Path, *, busy: bool = False) -> dict[str, str]:
    binaries = tmp_path / "bin"
    binaries.mkdir(parents=True, exist_ok=True)
    _ = make_fake_flock(binaries, busy=busy)
    make_script(binaries / "inotifywait", "sleep 1")
    return {"PATH": str(binaries), "HOME": str(tmp_path)}


def make_watcher(
    tmp_path: Path,
    *,
    environ: Mapping[str, str],
    generate_command: Sequence[str],
    derive_command: Sequence[str] | None = None,
    accent: str | None = "61,174,233",
) -> Watcher:
    kdeglobals = tmp_path / "kdeglobals"
    if accent is not None:
        _ = kdeglobals.write_text(
            f"[General]\nAccentColor={accent}\n", encoding="utf-8"
        )
    waywallen = tmp_path / "waywallen" / "config.toml"
    waywallen.parent.mkdir(parents=True, exist_ok=True)
    _ = waywallen.write_text("[global]\n", encoding="utf-8")
    paths = WatcherPaths(
        kdeglobals=kdeglobals,
        cache_path=tmp_path / "cache" / "last-watch-accent",
        lock_path=tmp_path / "cache" / "feeder.lock",
        waywallen_config=waywallen,
    )
    return Watcher(
        paths=paths,
        environ=environ,
        generate_command=generate_command,
        derive_command=derive_command,
    )


def test_read_cache_is_none_when_missing(tmp_path: Path) -> None:
    watcher = make_watcher(
        tmp_path,
        environ=make_environment(tmp_path),
        generate_command=("true",),
    )

    assert watcher.cached_accent() is None
    assert watcher.accent_changed("#3daee9") is True


def test_stored_accent_is_not_reported_as_changed(tmp_path: Path) -> None:
    watcher = make_watcher(
        tmp_path,
        environ=make_environment(tmp_path),
        generate_command=("true",),
    )

    watcher.store_accent("#3daee9")

    assert watcher.cached_accent() == "#3daee9"
    assert watcher.accent_changed("#3daee9") is False
    assert watcher.accent_changed("#ff0000") is True


def test_inotify_command_watches_events_and_directories(tmp_path: Path) -> None:
    watcher = make_watcher(
        tmp_path,
        environ=make_environment(tmp_path),
        generate_command=("true",),
    )

    command = watcher.inotify_command()

    assert command[0].endswith("inotifywait")
    assert WATCH_EVENTS in command
    assert str(tmp_path) in command
    assert str(tmp_path / "waywallen") in command


def test_locked_command_wraps_generate_with_flock(tmp_path: Path) -> None:
    watcher = make_watcher(
        tmp_path,
        environ=make_environment(tmp_path),
        generate_command=("accent-theme", "generate"),
    )

    command = watcher.locked_command(watcher.generate_command)

    assert command[0].endswith("flock")
    assert "-n" in command
    assert str(tmp_path / "cache" / "feeder.lock") in command
    assert command[-2:] == ["accent-theme", "generate"]


def test_waywallen_derive_only_runs_without_explicit_accent(tmp_path: Path) -> None:
    with_accent = make_watcher(
        tmp_path,
        environ=make_environment(tmp_path),
        generate_command=("true",),
        derive_command=("true",),
    )
    without_accent = make_watcher(
        tmp_path / "otro",
        environ=make_environment(tmp_path / "otro"),
        generate_command=("true",),
        derive_command=("true",),
        accent=None,
    )

    assert with_accent.needs_waywallen_derive() is False
    assert without_accent.needs_waywallen_derive() is True


def test_handle_event_ignores_unrelated_files(tmp_path: Path) -> None:
    watcher = make_watcher(
        tmp_path,
        environ=make_environment(tmp_path),
        generate_command=("true",),
    )

    assert watcher.handle_event(str(tmp_path / "otro.txt")) == "ignored"


def test_is_relevant_only_accepts_watched_files(tmp_path: Path) -> None:
    watcher = make_watcher(
        tmp_path,
        environ=make_environment(tmp_path),
        generate_command=("true",),
    )

    assert watcher.is_relevant(str(tmp_path / "kdeglobals")) is True
    assert watcher.is_relevant(str(tmp_path / "waywallen" / "config.toml")) is True
    assert watcher.is_relevant(str(tmp_path / "kdeglobals.lock")) is False
    assert watcher.is_relevant(str(tmp_path / "kdeglobals.YzcWHU")) is False
    assert watcher.is_relevant(str(tmp_path / "#1209961923")) is False
    assert watcher.is_relevant(str(tmp_path / "otro.txt")) is False


def test_handle_event_skips_regeneration_when_accent_unchanged(tmp_path: Path) -> None:
    log = tmp_path / "generate.log"
    make_script(tmp_path / "generate.sh", f"echo generado >> {log}")
    watcher = make_watcher(
        tmp_path,
        environ=make_environment(tmp_path),
        generate_command=(str(tmp_path / "generate.sh"),),
    )
    watcher.store_accent(watcher.current_accent())

    result = watcher.handle_event(str(tmp_path / "kdeglobals"))

    assert result == "unchanged"
    assert not log.exists()


def test_handle_event_regenerates_and_updates_cache(tmp_path: Path) -> None:
    log = tmp_path / "generate.log"
    make_script(tmp_path / "generate.sh", f"echo generado >> {log}")
    watcher = make_watcher(
        tmp_path,
        environ=make_environment(tmp_path),
        generate_command=(str(tmp_path / "generate.sh"),),
    )

    result = watcher.handle_event(str(tmp_path / "kdeglobals"))

    assert result == "regenerated"
    assert log.read_text(encoding="utf-8").strip() == "generado"
    assert watcher.cached_accent() == "#3daee9"


def test_handle_event_reports_busy_lock_without_regenerating(tmp_path: Path) -> None:
    log = tmp_path / "generate.log"
    make_script(tmp_path / "generate.sh", f"echo generado >> {log}")
    watcher = make_watcher(
        tmp_path,
        environ=make_environment(tmp_path, busy=True),
        generate_command=(str(tmp_path / "generate.sh"),),
    )

    result = watcher.handle_event(str(tmp_path / "kdeglobals"))

    assert result == "locked"
    assert not log.exists()
    assert watcher.cached_accent() is None


def test_handle_event_reports_failure_without_caching(tmp_path: Path) -> None:
    make_script(tmp_path / "generate.sh", "exit 4")
    watcher = make_watcher(
        tmp_path,
        environ=make_environment(tmp_path),
        generate_command=(str(tmp_path / "generate.sh"),),
    )

    result = watcher.handle_event(str(tmp_path / "kdeglobals"))

    assert result == "failed"
    assert watcher.cached_accent() is None


def test_handle_event_runs_derive_for_waywallen_change(tmp_path: Path) -> None:
    log = tmp_path / "derive.log"
    make_script(tmp_path / "derive.sh", f"echo derivado >> {log}")
    watcher = make_watcher(
        tmp_path,
        environ=make_environment(tmp_path),
        generate_command=("true",),
        derive_command=(str(tmp_path / "derive.sh"),),
        accent=None,
    )

    result = watcher.handle_event(str(tmp_path / "waywallen" / "config.toml"))

    assert result == "derived"
    assert log.read_text(encoding="utf-8").strip() == "derivado"


def test_run_processes_events_and_counts_regenerations(tmp_path: Path) -> None:
    log = tmp_path / "generate.log"
    make_script(tmp_path / "generate.sh", f"echo generado >> {log}")
    watcher = make_watcher(
        tmp_path,
        environ=make_environment(tmp_path),
        generate_command=(str(tmp_path / "generate.sh"),),
    )

    regenerated = watcher.run(
        [
            str(tmp_path / "kdeglobals"),
            str(tmp_path / "kdeglobals"),
        ]
    )

    assert regenerated == 1
    assert len(log.read_text(encoding="utf-8").splitlines()) == 1


def test_default_generate_command_targets_the_cli() -> None:
    assert DEFAULT_GENERATE_COMMAND == ("accent-theme", "generate")


def test_request_regeneration_collapses_a_burst_into_one_run(tmp_path: Path) -> None:
    log = tmp_path / "generate.log"
    make_script(tmp_path / "generate.sh", f"echo generado >> {log}")
    watcher = make_watcher(
        tmp_path,
        environ=make_environment(tmp_path),
        generate_command=(str(tmp_path / "generate.sh"),),
    )

    for _ in range(6):
        watcher.request_regeneration(str(tmp_path / "kdeglobals"))

    assert watcher.wait_idle(timeout=5.0) is True
    assert log.read_text(encoding="utf-8").splitlines() == ["generado"]


def test_accent_change_during_a_run_is_regenerated(tmp_path: Path) -> None:
    log = tmp_path / "generate.log"
    make_script(tmp_path / "generate.sh", f"sleep 0.3; echo generado >> {log}")
    watcher = make_watcher(
        tmp_path,
        environ=make_environment(tmp_path),
        generate_command=(str(tmp_path / "generate.sh"),),
    )

    watcher.request_regeneration(str(tmp_path / "kdeglobals"))
    time.sleep(0.4)
    _ = (tmp_path / "kdeglobals").write_text(
        "[General]\nAccentColor=255,0,0\n", encoding="utf-8"
    )
    watcher.request_regeneration(str(tmp_path / "kdeglobals"))

    assert watcher.wait_idle(timeout=5.0) is True
    assert watcher.cached_accent() == "#ff0000"
