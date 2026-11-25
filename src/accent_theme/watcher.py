"""Watcher de AccentColor basado en inotifywait, flock y caché local."""

from __future__ import annotations

import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

from accent_theme.accent import accent_to_hex, read_accent
from accent_theme.sources.models import SourceError
from accent_theme.sources.resolver import resolve_source_kind
from accent_theme.sources.waywallen import read_last_wallpaper

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from typing import TextIO

    from accent_theme.sources.models import SourceKind

WATCH_EVENTS: Final = "modify,close_write,moved_to"
LOCK_BUSY_EXIT_CODE: Final = 75
DEFAULT_GENERATE_COMMAND: Final = ("accent-theme", "generate")
SETTLE_SECONDS: Final = 0.3
GENERATE_TIMEOUT_SECONDS: Final = 300.0


class WatcherError(RuntimeError):
    """Error visible del watcher por dependencias o rutas inválidas."""

    @classmethod
    def missing_binary(cls, name: str) -> WatcherError:
        """Construye el error de dependencia ausente."""
        return cls(f"{name} no encontrado; instálalo para usar accent-theme watch")

    @classmethod
    def missing_source_path(cls, kind: str) -> WatcherError:
        """Construye el error de una fuente sin ruta que vigilar."""
        message = f"la fuente {kind} no tiene una ruta de configuración definida"
        return cls(message)


@dataclass(frozen=True, slots=True)
class WatcherPaths:
    """Rutas que el watcher observa y mantiene."""

    kdeglobals: Path
    cache_path: Path
    lock_path: Path
    waywallen_config: Path | None = None


@dataclass(slots=True)
class GenerationState:
    """Estado mutable de la regeneración en curso."""

    lock: threading.Lock = field(default_factory=threading.Lock)
    pending_path: str | None = None
    thread: threading.Thread | None = None


@dataclass(frozen=True, slots=True)
class Watcher:
    """Observa ``kdeglobals`` y regenera la paleta cuando cambia el acento."""

    paths: WatcherPaths
    environ: Mapping[str, str]
    generate_command: Sequence[str] = DEFAULT_GENERATE_COMMAND
    source_request: str = "auto"
    settle_seconds: float = SETTLE_SECONDS
    state: GenerationState = field(default_factory=GenerationState, compare=False)

    def resolved_kind(self) -> SourceKind:
        """Devuelve el tipo de fuente concreto que corresponde vigilar."""
        return resolve_source_kind(
            self.source_request,
            self.environ,
            self.paths.waywallen_config,
        )

    def watch_path(self) -> Path:
        """Devuelve el archivo cuyo cambio dispara una regeneración."""
        kind = self.resolved_kind()
        if kind == "waywallen":
            config = self.paths.waywallen_config
            if config is None:
                raise WatcherError.missing_source_path(kind)
            return config
        return self.paths.kdeglobals

    def current_value(self) -> str:
        """Devuelve el valor observable de la fuente: acento o wallpaper."""
        if self.resolved_kind() == "waywallen":
            return read_last_wallpaper(self.watch_path())
        return accent_to_hex(read_accent(self.paths.kdeglobals))

    def current_accent(self) -> str:
        """Devuelve el valor actual de la fuente en forma canónica."""
        return self.current_value()

    def effective_generate_command(self) -> list[str]:
        """Añade la fuente resuelta y ``--once`` al comando de generación."""
        command = list(self.generate_command)
        if "--source" not in command:
            command.extend(("--source", self.resolved_kind()))
        if "--once" not in command:
            command.append("--once")
        return command

    def cached_accent(self) -> str | None:
        """Devuelve el acento de la última regeneración exitosa."""
        try:
            contents = self.paths.cache_path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            return None
        return contents or None

    def store_accent(self, accent: str) -> None:
        """Guarda el acento que se acaba de regenerar."""
        self.paths.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.paths.cache_path.with_name(
            f".{self.paths.cache_path.name}.tmp"
        )
        _ = temporary.write_text(f"{accent}\n", encoding="utf-8")
        _ = temporary.replace(self.paths.cache_path)

    def accent_changed(self, accent: str) -> bool:
        """Indica si el acento difiere del de la última regeneración."""
        return self.cached_accent() != accent

    def _which(self, name: str) -> str:
        found = shutil.which(name, path=self.environ.get("PATH", ""))
        if found is None:
            raise WatcherError.missing_binary(name)
        return found

    def inotify_command(self) -> list[str]:
        """Construye el comando ``inotifywait`` con los directorios vigilados."""
        directories = [self.watch_path().parent]
        return [
            self._which("inotifywait"),
            "-m",
            "-e",
            WATCH_EVENTS,
            "--format",
            "%w%f",
            *(str(directory) for directory in directories),
        ]

    def locked_command(self, command: Sequence[str]) -> list[str]:
        """Envuelve un comando con ``flock`` no bloqueante."""
        self.paths.lock_path.parent.mkdir(parents=True, exist_ok=True)
        return [
            self._which("flock"),
            "-n",
            "-E",
            str(LOCK_BUSY_EXIT_CODE),
            str(self.paths.lock_path),
            *command,
        ]

    def _run(self, command: Sequence[str]) -> int:
        try:
            process = subprocess.run(  # noqa: S603
                list(command),
                capture_output=True,
                text=True,
                timeout=GENERATE_TIMEOUT_SECONDS,
                check=False,
                env=dict(self.environ),
            )
        except (OSError, subprocess.TimeoutExpired):
            return 1
        return process.returncode

    def is_relevant(self, raw_path: str) -> bool:
        """Indica si el evento corresponde a un archivo vigilado.

        KDE guarda ``kdeglobals`` de forma atómica y en el mismo directorio
        deja ``kdeglobals.lock`` y temporales: solo el archivo exacto cuenta.
        """
        return Path(raw_path) == self.watch_path()

    def handle_event(self, raw_path: str) -> str:
        """Procesa un evento de inotify y devuelve la acción realizada.

        Una configuración ilegible (Waywallen la reescribe al cambiar de
        wallpaper) se reporta como fallo sin tumbar el watcher: el siguiente
        evento volverá a intentarlo.
        """
        if not self.is_relevant(raw_path):
            return "ignored"
        try:
            current = self.current_value()
        except SourceError:
            return "failed"
        if not self.accent_changed(current):
            return "unchanged"

        returncode = self._run(self.locked_command(self.effective_generate_command()))
        if returncode == LOCK_BUSY_EXIT_CODE:
            return "locked"
        if returncode != 0:
            return "failed"
        self.store_accent(current)
        return "regenerated"

    def run(self, events: Iterable[str]) -> int:
        """Procesa una lista de eventos y devuelve cuántas regeneraciones hubo."""
        regenerated = 0
        for event in events:
            if self.handle_event(event) == "regenerated":
                regenerated += 1
        return regenerated

    def request_regeneration(self, raw_path: str) -> None:
        """Pide una regeneración sin bloquear el bucle de eventos.

        Si ya hay una en curso se guarda la ruta pendiente más reciente: la
        ráfaga de eventos que produce KDE se consolida en una sola pasada.
        """
        with self.state.lock:
            self.state.pending_path = raw_path
            thread = self.state.thread
            if thread is not None and thread.is_alive():
                return
            thread = threading.Thread(target=self._regeneration_loop, daemon=True)
            self.state.thread = thread
        thread.start()

    def wait_idle(self, timeout: float = 5.0) -> bool:
        """Espera a que termine la regeneración pendiente."""
        with self.state.lock:
            thread = self.state.thread
        if thread is None:
            return True
        thread.join(timeout)
        return not thread.is_alive()

    def _regeneration_loop(self) -> None:
        """Regenera en segundo plano hasta que no queden peticiones."""
        while True:
            time.sleep(self.settle_seconds)
            with self.state.lock:
                path = self.state.pending_path
                self.state.pending_path = None
            if path is None:
                return
            _ = self.handle_event(path)
            with self.state.lock:
                if self.state.pending_path is None:
                    return

    def watch(self) -> int:
        """Vigila los directorios configurados hasta recibir una interrupción."""
        process = subprocess.Popen(  # noqa: S603
            self.inotify_command(),
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=dict(self.environ),
        )
        try:
            if process.stdout is None:
                return 1
            stream = cast("TextIO", process.stdout)
            for line in stream:
                event = line.strip()
                if not event or not self.is_relevant(event):
                    continue
                self.request_regeneration(event)
        except KeyboardInterrupt:
            pass
        finally:
            _ = self.wait_idle(timeout=30.0)
            process.terminate()
            _ = process.wait(timeout=10)
        return 0
