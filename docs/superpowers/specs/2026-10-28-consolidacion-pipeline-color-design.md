# Consolidación del pipeline de color — Caparazón + accent-theme

Fecha: 2026-10-28
Estado: propuesta para aprobar
Repos: `ezku100/accent-theme` (motor), `ezku100/caparazon-shell` (shell)

## Objetivo

Que el cambio de AccentColor de KDE llegue a la shell de Caparazón en menos de un
segundo, con una sola regeneración del tema y sin procesos duplicados.

Hoy: **~2.1 s** de latencia, **2–3 regeneraciones** por cambio, **~26 procesos
Python** lanzados, **3–4 escrituras** de `~/.cache/caparazon/colors.json`.

## Causas medidas

1. **El watcher duerme por evento antes de filtrar.** En
   `accent_theme/watcher.py::watch()` el bucle hace `time.sleep(0.5)` *antes* de
   `handle_event()`, así que cuenta como espera los eventos que va a descartar.
   El guardado atómico de KDE produce ~8 eventos (`kdeglobals.lock`,
   `#<pid>`, `kdeglobals.XXXXXX`, `close_write`, `moved_to`…): ~2–2.5 s de sueño
   antes de procesar el `moved_to kdeglobals` que sí importa.
2. **El generate es síncrono y bloquea el bucle.** `handle_event()` espera al
   `accent-theme generate` completo (0.9 s: matugen + 11 hooks + recargas en
   vivo). Mientras tanto los eventos se acumulan en el pipe de inotify.
3. **Dos pipelines escriben el mismo archivo.** El motor y el legacy
   `~/.config/kitty/watch_accent.sh` (2 procesos huérfanos, unidad systemd ya
   desactivada) escriben `~/.cache/caparazon/colors.json`: el legacy a los
   ~0.3 s y el motor a los ~2 s. Trabajo duplicado y doble aplicación de paleta.
4. **La publicación no es atómica.** matugen escribe `colors.json` con
   truncate+write. La shell puede leer JSON a medias, quedarse con la paleta
   fallback y esperar al Timer de 1 s para recuperarse.
5. **La shell recarga el JSON cada segundo.** `theme/MatugenPalette.qml` tiene
   un `Timer` de 1 s que fuerza `reload()` ("red de seguridad") y mantiene el
   ruido permanente.

## Decisiones

### 1. Un solo dueño del pipeline: el motor

- El motor `accent-theme` es el único que escribe `~/.cache/caparazon/colors.json`
  y el único que regenera el resto de apps.
- Se apagan los procesos legacy huérfanos y se elimina `kitty-theme-watch.service`
  (ya `disabled`, pero con procesos vivos lanzados a mano desde una scope de kitty).
- Se borra de la shell el watcher muerto `scripts/accent-watcher.sh` +
  `scripts/accent-watcher.service` (polling cada 2 s, ya no corre).
- Se commitean los borrados ya presentes en el working tree de la shell
  (`integration/theme/kitty/accent_to_matugen.py`, `integration/theme/kitty/watch_accent.sh`).
- Cada pipeline usa su propia caché y su propio lock; el motor usa
  `~/.cache/accent-theme/last-watch-accent` (hex) y **nadie** toca
  `~/.cache/caparazon/last-watch-accent`.

### 2. Watcher reactivo y coalescente (motor)

- Filtrar el evento **antes** de esperar: solo cuentan `kdeglobals` y el config
  de Waywallen.
- Debounce coalescente con reloj (no `sleep` por evento): una ráfaga de N
  eventos produce **una** espera y **un** generate.
- El generate deja de ejecutarse en el bucle: se lanza en segundo plano y el
  watcher sigue escuchando. Si llegan eventos durante un generate, se marca
  `pending` y al terminar se ejecuta **uno solo** más (nunca dos en paralelo).
- Un cambio de acento que no cambia el valor sigue siendo un no-op (se conserva
  la comparación con la caché).

### 3. Publicación atómica (motor)

- Tras `invoke_matugen`, el motor publica las salidas JSON registradas con
  tmp + `os.replace` → el archivo cambia de inode de golpe y nunca queda
  truncado. Beneficia a la shell y a cualquier consumidor de `colors.json`.

### 4. Shell sin polling (Caparazón)

- `theme/MatugenPalette.qml`: se quita el `Timer` de 1 s. Se queda
  `watchChanges: true` + `onFileChanged: adapter.reload()`, con un fallback de
  5 s (una lectura cada 5 s no es ruido y cubre una pérdida del watcher).
- Con la publicación atómica no hace falta red de seguridad de 1 s.

## No-objetivos

- No se cambia la paleta ni el aspecto visual.
- No se rediseña la integración de las demás apps (kitty, brave, cava, zen…):
  solo se deja de duplicar su trabajo.
- No se cambia de motor de color ni se migra a otro formato de paleta.
- No se toca KWin, Plasma ni el display manager.

## Verificación

1. **Motor (pytest)**: ráfaga de eventos KDE → exactamente 1 generate; evento
   irrelevante → 0; la publicación deja el archivo íntegro (se renombra, no se
   trunca).
2. **Máquina**: cambiar el AccentColor → `colors.json` actualizado en **< 0.8 s**,
   **1 sola escritura**, **1 sola regeneración** (contando escrituras con
   inotifywait).
3. **Servicios**: `accent-theme.service` activo sin errores; ningún proceso
   `watch_accent.sh` vivo; `journalctl --user -u accent-theme.service` sin
   fallos de hooks.
4. **Shell**: captura de pantalla antes/después con el color nuevo aplicado.

## Reparto de cambios

| Repo | Cambio |
|---|---|
| `accent-theme` | `src/accent_theme/watcher.py` (filtro + debounce + generate en segundo plano), `src/accent_theme/cli.py` (publicación atómica), tests |
| `caparazon-shell` | `theme/MatugenPalette.qml` (sin Timer de 1 s), borrar `scripts/accent-watcher.*`, commitear borrados de `integration/theme/kitty/*` |
| máquina | parar legacy huérfano, reiniciar `accent-theme.service`, verificar |
