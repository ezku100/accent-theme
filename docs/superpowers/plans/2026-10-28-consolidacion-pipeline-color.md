# Consolidación del pipeline de color de Caparazón — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el cambio de AccentColor de KDE llegue a la shell de Caparazón en menos de 0.8 s, con una sola regeneración del tema y sin procesos duplicados.

**Architecture:** El motor `accent-theme` queda como único dueño del pipeline de color. Su watcher filtra el ruido antes de dormir, consolida ráfagas de eventos y ejecuta la regeneración en segundo plano (una sola a la vez). Las salidas de matugen se publican de forma atómica (staging + `os.replace`), así que la shell nunca lee un JSON a medias. La shell deja de hacer polling: se queda con `watchChanges` y un fallback de 5 s.

**Tech Stack:** Python ≥ 3.11 (uv, pytest, ruff, basedpyright), Quickshell 0.3.2 / QML, systemd --user, inotifywait.

**Spec:** `docs/superpowers/specs/2026-10-28-consolidacion-pipeline-color-design.md` (en este repo).

## Global Constraints

- Idioma del código, comentarios, mensajes de error y documentación: **español**.
- `accent-theme`: `uv run pytest`, `uv run ruff check .`, `uv run basedpyright`. Python ≥ 3.11, ruff `select = ["ALL"]` con `line-length = 88`, basedpyright `typeCheckingMode = "all"`.
- `caparazon-shell`: `uv run pytest`, `uv run ruff check .`. Mismas reglas de estilo.
- Prohibido `as any`, `# type: ignore`, `# noqa` sin motivo justificado en el código nuevo.
- Nada de dependencias nuevas: solo biblioteca estándar.
- No se toca la paleta ni el aspecto visual; no se toca KWin, Plasma ni el display manager.
- No se hace `git commit` ni `git push` sin autorización explícita del usuario (Task 6).
- Todo comando del sistema es no interactivo.

## Review Focus

- **Ráfaga de eventos de KDE:** `kdeglobals.lock`, `#<pid>` y `kdeglobals.XXXXXX` accompanied de un `moved_to` → una sola regeneración, no seis. (Task 1)
- **Cambio de acento durante una regeneración en curso:** el acento nuevo no se pierde; tras terminar la primera, el motor regenera con el valor vigente. (Task 1)
- **`colors.json` ausente o corrupto:** la shell conserva la paleta de reserva y el motor no revienta ni borra el archivo. (Task 2)
- **Otro proceso escribiendo `colors.json` a la vez:** la publicación atómica no deja archivos a medias ni pisa un cambio ajeno con contenido vacío. (Task 2)
- **Motor parado o servicio detenido:** cambiar el acento no rompe nada y no deja procesos zombis. (Task 4)

---

### Task 1: Watcher reactivo — filtrar el ruido y regenerar en segundo plano

**Files:**
- Modify: `src/accent_theme/watcher.py`
- Test: `tests/test_watcher.py`

**Interfaces:**
- Consumes: `Watcher.handle_event(raw_path) -> str` (existente, sin cambios), `WatcherPaths`.
- Produces:
  - `Watcher.is_relevant(raw_path: str) -> bool` — `True` solo para la ruta exacta de `kdeglobals` o del config de Waywallen.
  - `Watcher.request_regeneration(raw_path: str) -> None` — programa la regeneración sin bloquear; si ya hay una en curso, guarda la ruta pendiente más reciente.
  - `Watcher.wait_idle(timeout: float = 5.0) -> bool` — espera a que termine la regeneración pendiente; `True` si quedó inactivo dentro del plazo.
  - `Watcher.settle_seconds: float` — campo del dataclass, valor por defecto `0.3`; ventana de consolidación de la ráfaga.
  - `Watcher` deja de usar `DEBOUNCE_SECONDS` y `time.sleep` en el bucle de eventos.

- [ ] **Step 1: Escribir el test que falla — el filtro de relevancia**

Añadir a `tests/test_watcher.py`:

```python
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
```

- [ ] **Step 2: Ejecutar el test y ver que falla**

Run: `uv run pytest tests/test_watcher.py::test_is_relevant_only_accepts_watched_files -v`
Expected: FAIL con `AttributeError: 'Watcher' object has no attribute 'is_relevant'`

- [ ] **Step 3: Implementar `is_relevant` en `src/accent_theme/watcher.py`**

Comparar la ruta **completa** contra `self.paths.kdeglobals` y `self.paths.waywallen_config` (este último solo si no es `None`). No comparar por nombre de archivo: `kdeglobals.lock` y `kdeglobals.YzcWHU` se descartarían mal.

- [ ] **Step 4: Ejecutar el test y ver que pasa**

Run: `uv run pytest tests/test_watcher.py::test_is_relevant_only_accepts_watched_files -v`
Expected: PASS

- [ ] **Step 5: Escribir el test que falla — la ráfaga se consolida en una regeneración**

Añadir a `tests/test_watcher.py`:

```python
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
```

- [ ] **Step 6: Ejecutar el test y ver que falla**

Run: `uv run pytest tests/test_watcher.py::test_request_regeneration_collapses_a_burst_into_one_run -v`
Expected: FAIL con `AttributeError: 'Watcher' object has no attribute 'request_regeneration'`

- [ ] **Step 7: Implementar la regeneración en segundo plano**

En `src/accent_theme/watcher.py`:

1. Declarar un dataclass **no congelado** que agrupe el estado mutable (el `Watcher` es `frozen=True, slots=True`, así que no se le puede reasignar un atributo):

```python
@dataclass(slots=True)
class _GenerationState:
    """Estado mutable de la regeneración en curso."""

    lock: threading.Lock = field(default_factory=threading.Lock)
    pending_path: str | None = None
    thread: threading.Thread | None = None
```

2. Añadir al dataclass `Watcher` dos campos con valor por defecto: `settle_seconds: float = 0.3` y `state: _GenerationState = field(default_factory=_GenerationState, compare=False)`.
3. `request_regeneration(raw_path)`:
   - Con el lock, guardar `self._pending_path = raw_path`.
   - Si ya hay un hilo vivo, terminar (no lanzar otro).
   - Si no, lanzar un hilo daemon que ejecute el bucle de regeneración.
3. El bucle de regeneración (método privado `_regeneration_loop`):
   - Espera `settle_seconds` para que se apague la ráfaga.
   - Toma la ruta pendiente; si durante la espera llegó otra más reciente, se queda con la más reciente.
   - Llama a `self.handle_event(path)` una sola vez.
   - Si mientras corría `handle_event` llegó otra ruta pendiente, repite el ciclo (el `handle_event` interno ya descarta el caso "el acento no cambió").
4. `wait_idle(timeout)`: hace `join` del hilo con el plazo dado y devuelve `True` si terminó, `False` si expiró.
5. Reescribir `watch()`: quitar `time.sleep(DEBOUNCE_SECONDS)`; por cada línea, si `not event` o `not self.is_relevant(event)` → `continue`; si no, `self.request_regeneration(event)`. Al salir, llamar a `wait_idle()` antes de terminar el proceso de inotify.
6. Borrar la constante `DEBOUNCE_SECONDS` si deja de usarse.

- [ ] **Step 8: Ejecutar el test y ver que pasa**

Run: `uv run pytest tests/test_watcher.py::test_request_regeneration_collapses_a_burst_into_one_run -v`
Expected: PASS

- [ ] **Step 9: Test extra — el acento nuevo durante una regeneración no se pierde**

Añadir a `tests/test_watcher.py`:

```python
def test_accent_change_during_a_run_is_regenerated(tmp_path: Path) -> None:
    log = tmp_path / "generate.log"
    make_script(tmp_path / "generate.sh", f"echo generado >> {log}")
    watcher = make_watcher(
        tmp_path,
        environ=make_environment(tmp_path),
        generate_command=(str(tmp_path / "generate.sh"),),
    )

    watcher.request_regeneration(str(tmp_path / "kdeglobals"))
    (tmp_path / "kdeglobals").write_text(
        "[General]\nAccentColor=255,0,0\n", encoding="utf-8"
    )
    watcher.request_regeneration(str(tmp_path / "kdeglobals"))

    assert watcher.wait_idle(timeout=5.0) is True
    assert watcher.cached_accent() == "#ff0000"
```

Si la implementación consolida la ráfaga en una sola pasada, este test documenta que el acento que queda en el archivo es el que se publica.

- [ ] **Step 10: Ejecutar toda la suite del motor**

Run: `uv run pytest`
Expected: PASS (90 tests Collected antes del cambio; todos en verde)

- [ ] **Step 11: Lint y tipos**

Run: `uv run ruff check .` → Expected: sin salida (sin errores)
Run: `uv run basedpyright` → Expected: 0 errores

---

### Task 2: Publicación atómica de las salidas de matugen

**Files:**
- Modify: `src/accent_theme/registry.py`
- Modify: `src/accent_theme/cli.py`
- Test: `tests/test_registry.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `TemplateRegistration(name, input_path, output_path)`, `render_matugen_config(registrations) -> str`, `invoke_matugen(...)`.
- Produces:
  - `TemplateRegistration.staging_path -> Path` — `output_path` con `.staging` insertado antes de la extensión final (`colors.json` → `colors.staging.json`; `theme.conf` → `theme.staging.conf`). La extensión final se conserva para que matugen mantenga el formato.
  - `render_matugen_config` sigue devolviendo el mismo texto, pero la línea `output_path` de cada template apunta ahora a `staging_path`.
  - `cli._handle_generate` publica cada salida con `os.replace(staging_path, output_path)` y **después** valida que `output_path` existe.

- [ ] **Step 1: Escribir el test que falla — la ruta de staging**

Añadir a `tests/test_registry.py`:

```python
def test_staging_path_keeps_the_final_extension(tmp_path: Path) -> None:
    registration = TemplateRegistration(
        name="caparazon-shell-matugen",
        input_path=tmp_path / "quickshell-matugen.json",
        output_path=tmp_path / "colors.json",
    )

    assert registration.staging_path == tmp_path / "colors.staging.json"
```

Y un caso más:

```python
def test_staging_path_keeps_non_json_extensions(tmp_path: Path) -> None:
    registration = TemplateRegistration(
        name="kitty-matugen",
        input_path=tmp_path / "kitty-matugen.conf",
        output_path=tmp_path / "theme.conf",
    )

    assert registration.staging_path == tmp_path / "theme.staging.conf"
```

- [ ] **Step 2: Ejecutar los tests y ver que fallan**

Run: `uv run pytest tests/test_registry.py -k staging_path -v`
Expected: FAIL con `AttributeError: 'TemplateRegistration' object has no attribute 'staging_path'`

- [ ] **Step 3: Implementar `staging_path` y usarlo en `render_matugen_config`**

En `src/accent_theme/registry.py`:

- Añadir la propiedad `staging_path` a `TemplateRegistration` (el dataclass es `frozen=True, slots=True` → usar `@property`).
- En `render_matugen_config`, cambiar `output_path = _toml_string(str(registration.output_path))` por `output_path = _toml_string(str(registration.staging_path))`.

- [ ] **Step 4: Ejecutar los tests y ver que pasan**

Run: `uv run pytest tests/test_registry.py -v`
Expected: PASS. Si `test_registry.py` tiene un test que fija el `output_path` del config renderizado, actualizarlo para esperar la ruta de staging (es un cambio de contrato intencionado).

- [ ] **Step 5: Escribir el test que falla — la publicación deja el archivo final íntegro**

El `make_fake_matugen` actual solo imprime el payload por stdout: no escribe los archivos de salida, que es justo lo que hace matugen con `-c config`. Primero hay que hacer el fake honesto.

En `tests/test_cli.py`, sustituir `make_fake_matugen` por una versión que además escriba cada `output_path` del config que recibe en `-c`:

```python
def matugen_payload() -> str:
    """Payload role-first válido que exige ``parse_matugen_json``."""
    roles = (
        "surface",
        "surface_container_lowest",
        "surface_container_low",
        "surface_container",
        "surface_container_high",
        "surface_container_highest",
        "on_surface",
        "on_surface_variant",
        "outline",
        "outline_variant",
        "primary",
        "on_primary",
        "secondary",
        "tertiary",
        "error",
        "error_container",
        "on_error_container",
    )
    return json.dumps(
        {"colors": {role: {"dark": {"color": "#123456"}} for role in roles}}
    )


def make_fake_matugen(directory: Path, payload: str) -> Path:
    """Crea un binario Matugen falso que escribe el payload en cada salida."""
    binary = directory / "matugen"
    _ = binary.write_text(
        f"""#!{sys.executable}
import pathlib, sys, tomllib
config = tomllib.loads(pathlib.Path(sys.argv[sys.argv.index("-c") + 1]).read_text())
for template in config.get("templates", {{}}).values():
    output = pathlib.Path(template["output_path"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text({payload!r})
print({payload!r})
""",
        encoding="utf-8",
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    return binary
```

Los tests existentes de `tests/test_cli.py` que llaman a `make_fake_matugen` siguen funcionando: ahora el fake escribe el archivo de salida en el path que le da el config.

- [ ] **Step 6: Escribir el test que falla — la publicación es atómica**

Añadir a `tests/test_cli.py`:

```python
def test_cli_generate_publishes_the_output_atomically(tmp_path: Path) -> None:
    descriptor = write_registration_source(tmp_path)
    assert main(
        [
            "register",
            "--app",
            "caparazon-shell",
            "--descriptor",
            str(descriptor),
        ],
        environ={"HOME": str(tmp_path), "PATH": ""},
    ) == 0

    binaries = tmp_path / "bin"
    binaries.mkdir()
    payload = matugen_payload()
    _ = make_fake_matugen(binaries, payload)
    output = tmp_path / ".cache" / "caparazon" / "colors.json"
    staging = output.parent / "colors.staging.json"

    exit_code = main(
        ["generate"],
        environ={
            "HOME": str(tmp_path),
            "PATH": str(binaries),
            "MATUGEN": str(binaries / "matugen"),
            "ACCENT_THEME_HOOKS_DIR": str(tmp_path / "hooks"),
        },
    )

    assert exit_code == 0
    assert output.is_file()
    assert output.read_text(encoding="utf-8").strip() == payload.strip()
    assert not staging.exists()
```

- [ ] **Step 7: Ejecutar el test y ver que falla**

Run: `uv run pytest tests/test_cli.py::test_cli_generate_publishes_the_output_atomically -v`
Expected: FAIL — el motor deja el archivo en `colors.staging.json` y `colors.json` no existe.

- [ ] **Step 8: Publicar de forma atómica en `cli._handle_generate`**

En `src/accent_theme/cli.py`, dentro de `_handle_generate`, después de `tokens = invoke_matugen(...)` y **antes** del bloque `missing_outputs`:

1. Por cada `registration`, si `registration.staging_path` existe → `os.replace(registration.staging_path, registration.output_path)`.
2. Si el staging no existe pero el `output_path` sí → no hacer nada (una integración puede no producir archivo; el motor no debe fallar por eso).
3. Si ninguno de los dos existe → el bloque `missing_outputs` existente ya lo reporta con el nombre del archivo.

El directorio de salida ya se crea antes de invocar matugen (`registration.output_path.parent.mkdir(...)`); como el staging vive en el mismo directorio, no hace falta nada nuevo.

- [ ] **Step 9: Ejecutar el test y ver que pasa**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 10: Ejecutar toda la suite del motor**

Run: `uv run pytest`
Expected: PASS

- [ ] **Step 11: Lint y tipos**

Run: `uv run ruff check .` → sin errores
Run: `uv run basedpyright` → 0 errores

---

### Task 3: La shell deja de hacer polling

**Files:**
- Modify: `~/Projects/caparazon-shell/theme/MatugenPalette.qml`
- Create: `~/Projects/caparazon-shell/tests/test_palette_polling.py`

**Interfaces:**
- Consumes: `Quickshell.Io.FileView` (`watchChanges`, `fileChanged`, `reload()`), `JsonAdapter`.
- Produces: `MatugenPalette.qml` sin `Timer` de 1 s; el `Timer` de red de seguridad pasa a `interval: 5000`.

- [ ] **Step 1: Escribir el test que falla — la shell no sondea cada segundo**

Crear `~/Projects/caparazon-shell/tests/test_palette_polling.py`:

```python
"""La paleta no debe sonararse cada segundo.

`colors.json` se publica de forma atómica y la shell lo ve con
`watchChanges`; un temporizador de 1 s es ruido permanente en el compositor.
"""

from __future__ import annotations

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PALETTE = REPOSITORY_ROOT / "theme" / "MatugenPalette.qml"

TIMER_INTERVAL = re.compile(r"interval:\s*(\d+)")


def test_the_palette_watches_the_file_instead_of_polling() -> None:
    contents = PALETTE.read_text(encoding="utf-8")

    assert "watchChanges: true" in contents


def test_the_fallback_timer_is_not_faster_than_five_seconds() -> None:
    contents = PALETTE.read_text(encoding="utf-8")
    intervals = [int(value) for value in TIMER_INTERVAL.findall(contents)]

    assert intervals
    assert min(intervals) >= 5000
```

- [ ] **Step 2: Ejecutar el test y ver que falla**

Run: `cd ~/Projects/caparazon-shell && uv run pytest tests/test_palette_polling.py -v`
Expected: FAIL en `test_the_fallback_timer_is_not_faster_than_five_seconds` (`min(intervals) == 1000`)

- [ ] **Step 3: Cambiar el QML**

En `~/Projects/caparazon-shell/theme/MatugenPalette.qml`, en el bloque `Timer` final:

- `interval: 1000` → `interval: 5000`.
- Actualizar el comentario: explicar que el motor publica `colors.json` de forma atómica y que `watchChanges` es la vía principal; el temporizador es solo la red de seguridad.

- [ ] **Step 4: Ejecutar el test y ver que pasa**

Run: `cd ~/Projects/caparazon-shell && uv run pytest tests/test_palette_polling.py -v`
Expected: PASS

- [ ] **Step 5: Suite completa de la shell**

Run: `cd ~/Projects/caparazon-shell && uv run pytest`
Expected: PASS (107 tests antes del cambio)

- [ ] **Step 6: Lint de la shell**

Run: `cd ~/Projects/caparazon-shell && uv run ruff check .` → sin errores

---

### Task 4: Apagar el pipeline legacy y reiniciar el motor

**Files:**
- Modify (máquina): `~/.config/systemd/user/kitty-theme-watch.service` (eliminar)
- Modify (máquina): `~/.config/kitty/watch_accent.sh` (eliminar)
- Modify (máquina): `~/.config/kitty/accent_to_matugen.py` (eliminar)

**Interfaces:**
- Consumes: Task 1 y Task 2 ya instaladas y con tests en verde.
- Produces: un solo proceso que regenera el tema (`accent-theme watch`) y ningún proceso `watch_accent.sh` vivo.

- [ ] **Step 1: Confirmar el estado antes de tocar nada**

Run:
```bash
ps -eo pid,cmd | grep -E "watch_accent.sh|accent_theme watch" | grep -v grep
systemctl --user is-enabled kitty-theme-watch.service; systemctl --user is-active kitty-theme-watch.service
```
Expected: dos procesos `watch_accent.sh` (padre e hijo del pipe) y la unidad `disabled`/`inactive`. **Si aparece algún proceso con otro nombre, parar y preguntar antes de continuar.**

- [ ] **Step 2: Parar los procesos legacy**

Run:
```bash
pkill -f "$HOME/.config/kitty/watch_accent.sh"
```
Expected: sin salida; los procesos terminan.

- [ ] **Step 3: Verificar que no queda ningún watcher legacy**

Run: `ps -eo pid,cmd | grep "watch_accent.sh" | grep -v grep`
Expected: sin salida

- [ ] **Step 4: Eliminar la unidad y los scripts legacy**

Run:
```bash
systemctl --user disable --now kitty-theme-watch.service
rm -f "$HOME/.config/systemd/user/kitty-theme-watch.service" "$HOME/.config/kitty/watch_accent.sh" "$HOME/.config/kitty/accent_to_matugen.py"
systemctl --user daemon-reload
```
Expected: sin salida

- [ ] **Step 5: Reiniciar el motor con el código nuevo**

Run:
```bash
systemctl --user restart accent-theme.service
sleep 1
systemctl --user status accent-theme.service --no-pager
```
Expected: `active (running)`, el journal muestra "Watches established."

- [ ] **Step 6: Comprobar el contrato del motor**

Run: `accent-theme doctor`
Expected: `doctor: N integraciones correctas` y código de salida 0

- [ ] **Step 7: Medir la latencia real y el número de escrituras**

Run:
```bash
python3 - <<'PY'
import json, os, pathlib, subprocess, time
cache = pathlib.Path.home() / ".cache" / "caparazon" / "colors.json"
before = json.loads(cache.read_text())["primary"]
subprocess.run(["kwriteconfig6", "--file", str(pathlib.Path.home() / ".config" / "kdeglobals"),
                "--group", "General", "--key", "AccentColor", "220,110,134"], check=True)
start = time.monotonic()
while time.monotonic() - start < 10:
    try:
        if json.loads(cache.read_text())["primary"] != before:
            print(f"latencia: {time.monotonic() - start:.2f}s")
            break
    except (OSError, ValueError):
        pass
    time.sleep(0.02)
else:
    raise SystemExit("TIMEOUT: la paleta no cambió")
subprocess.run(["kwriteconfig6", "--file", str(pathlib.Path.home() / ".config" / "kdeglobals"),
                "--group", "General", "--key", "AccentColor", "110,220,134"], check=True)
PY
```
Expected: `latencia:` menor de **0.8 s**. Si no se cumple, volver a Task 1 y medir dónde se va el tiempo.

- [ ] **Step 8: Contar las escrituras de colors.json**

Run:
```bash
timeout 8 inotifywait -m -e modify,close_write,moved_to --timefmt "%H:%M:%S" \
  --format "%T %e %w%f" "$HOME/.cache/caparazon/colors.json" &
sleep 1
kwriteconfig6 --file "$HOME/.config/kdeglobals" --group General --key AccentColor 220,110,134
sleep 3
kwriteconfig6 --file "$HOME/.config/kdeglobals" --group General --key AccentColor 110,220,134
sleep 3
```
Expected: **una sola** publicación por cambio de acento (un `MOVED_TO` por cambio), no varias escrituras `MODIFY`.

- [ ] **Step 9: La shell sobrevive a una paleta ausente**

Run:
```bash
mv "$HOME/.cache/caparazon/colors.json" "$HOME/.cache/caparazon/colors.json.bak"
sleep 6
journalctl --user -u "app-caparazon@autostart.service" -n 10 --no-pager | tail -5
mv "$HOME/.cache/caparazon/colors.json.bak" "$HOME/.cache/caparazon/colors.json"
```
Expected: la shell sigue viva (no se reinicia) y usa la paleta de reserva. Si el journal muestra un crash o un reinicio, la paleta ausente es un problema de la shell y hay que corregirlo antes de seguir.

- [ ] **Step 10: Estado final de los servicios**

Run: `systemctl --user --failed --no-pager`
Expected: sin unidades fallidas.

---

### Task 5: Limpieza del repositorio de la shell

**Files:**
- Delete: `~/Projects/caparazon-shell/scripts/accent-watcher.sh`
- Delete: `~/Projects/caparazon-shell/scripts/accent-watcher.service`
- Modify: `~/Projects/caparazon-shell/install.sh`
- Modify: `~/Projects/caparazon-shell/README.md`

**Interfaces:**
- Consumes: Task 3 (la shell ya no necesita su propio watcher).
- Produces: `install.sh` que instala el motor `accent-theme` y ningún watcher propio; README sin referencias al servicio heredado.

- [ ] **Step 1: Localizar las referencias**

Run:
```bash
cd ~/Projects/caparazon-shell
grep -rn "accent-watcher\|accent_watcher" --include="*.sh" --include="*.service" --include="*.md" .
```
Expected: referencias en `install.sh` (funciones `install_accent_watcher` y `remove_accent_watcher`) y en `scripts/`.

- [ ] **Step 2: Quitar el watcher muerto de la shell**

Run:
```bash
cd ~/Projects/caparazon-shell
git rm scripts/accent-watcher.sh scripts/accent-watcher.service
```
Expected: los dos archivos salen del índice.

- [ ] **Step 3: Limpiar `install.sh`**

Borrar las funciones `install_accent_watcher()` y `remove_accent_watcher()` y sus llamadas. La instalación del tema debe apoyarse solo en el motor (`install_theme`).

- [ ] **Step 4: Verificar que `install.sh` sigue siendo coherente**

Run: `cd ~/Projects/caparazon-shell && bash -n install.sh`
Expected: sin salida (sintaxis válida)

- [ ] **Step 5: Actualizar el README**

En `~/Projects/caparazon-shell/README.md`:
- Quitar la frase que dice que la desinstalación devuelve el tema al servicio heredado `kitty-theme-watch.service`.
- En la sección «Tema», dejar claro que el motor `accent-theme` es el único que regenera la paleta y que la shell solo la lee.

- [ ] **Step 6: Suite de la shell**

Run: `cd ~/Projects/caparazon-shell && uv run pytest`
Expected: PASS

---

### Task 6: Commit y publicación (solo con autorización del usuario)

**Files:**
- `accent-theme`: `src/accent_theme/watcher.py`, `src/accent_theme/registry.py`, `src/accent_theme/cli.py`, `tests/`, `docs/superpowers/`
- `caparazon-shell`: `theme/MatugenPalette.qml`, `tests/test_palette_polling.py`, `scripts/` (borrados), `install.sh`, `README.md`

- [ ] **Step 1: Preguntar al usuario antes de commitear**

Preguntar: «¿Commiteo y subo los cambios a `ezku100/accent-theme` y `ezku100/caparazon-shell`?». Si no autoriza, parar aquí y dejar los repos con los cambios sin commitear.

- [ ] **Step 2: Revisar el diff antes de commitear**

Run:
```bash
git -C ~/.local/share/accent-theme/source status --short
git -C ~/.local/share/accent-theme/source diff
git -C ~/Projects/caparazon-shell status --short
git -C ~/Projects/caparazon-shell diff
```
Expected: solo los archivos del plan, sin secretos.

- [ ] **Step 3: Commit del motor**

Run:
```bash
cd ~/.local/share/accent-theme/source
git add -A
git commit -m "Motor: filtra el ruido del watcher y publica la paleta de forma atómica"
```
Expected: commit creado en `main`.

- [ ] **Step 4: Commit de la shell**

Run:
```bash
cd ~/Projects/caparazon-shell
git add -A
git commit -m "Tema: la shell deja de sondear la paleta y espera al motor"
```
Expected: commit creado en `main`.

- [ ] **Step 5: Publicar**

Run:
```bash
git -C ~/.local/share/accent-theme/source push
git -C ~/Projects/caparazon-shell push
```
Expected: push sin errores.

- [ ] **Step 6: Comprobación final**

Run:
```bash
systemctl --user is-active accent-theme.service
ps -eo cmd | grep -c "[w]atch_accent.sh"
```
Expected: `active` y `0` procesos legacy.
