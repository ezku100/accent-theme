# Guía de uso — accent-theme

Guía detallada para instalar, usar, personalizar y ampliar el motor.

- [1. Qué hace](#1-qué-hace)
- [2. Requisitos](#2-requisitos)
- [3. Instalación](#3-instalación)
- [4. Verificar que todo funciona](#4-verificar-que-todo-funciona)
- [5. Las catorce apps](#5-las-catorce-apps)
- [6. Comandos](#6-comandos)
- [7. El servicio](#7-el-servicio)
- [8. Cambiar el acento](#8-cambiar-el-acento)
- [9. Personalizar la paleta](#9-personalizar-la-paleta)
- [10. Añadir una app](#10-añadir-una-app)
- [11. Rutas](#11-rutas)
- [12. Problemas frecuentes](#12-problemas-frecuentes)
- [13. Desinstalar](#13-desinstalar)
- [14. Desarrollo](#14-desarrollo)

---

## 1. Qué hace

`accent-theme` es el motor global de tema de KDE. Lee el color de acento que
tienes puesto en Ajustes del sistema y lo reparte por catorce aplicaciones.

La cadena es siempre la misma:

```
~/.config/kdeglobals  →  AccentColor  →  paleta (50 roles, Matugen)
                                            ├─ 9 apps: fichero de tema
                                            └─ 5 apps: configuración propia
                                                    ↓
                                            recarga en vivo de las abiertas
```

El acento se lee de `~/.config/kdeglobals`, de la clave `General` →
`AccentColor`. Si no está, se usa `Colors:Selection` → `BackgroundNormal`.
La lectura se hace con `kreadconfig6` y, si esa herramienta no está, con el
propio parser del motor.

Lo que hace el motor por app:

| # | App | Mecanismo | Fichero que escribe |
| --- | --- | --- | --- |
| 1 | kitty | plantilla | `~/.config/kitty/theme.conf` |
| 2 | ghostty | plantilla | `~/.config/ghostty/theme` |
| 3 | konsole | plantilla | `~/.local/share/konsole/Dinamico.colorscheme` |
| 4 | kate | plantilla | `~/.local/share/org.kde.syntax-highlighting/themes/dinamico.theme` |
| 5 | cava | plantilla + inyección | `~/.cache/matugen-cava-snippet` → `~/.config/cava/config` |
| 6 | heroic | plantilla | `~/.config/heroic/themes/dinamico.css` |
| 7 | zen | plantilla + despliegue | `~/.cache/matugen-zen-kde-accent.css` → perfiles de Zen |
| 8 | steam | plantilla | `~/.local/share/Steam/millennium/themes/Material-Theme/css/main/colors/matugen.css` |
| 9 | caparazon-shell | plantilla | `~/.cache/caparazon/colors.json` |
| 10 | brave | módulo propio | `Preferences` y `Local State` del perfil |
| 11 | equibop | módulo propio | `~/.config/equibop/themes/midnight-accent-kde.theme.css` |
| 12 | materialgram | módulo propio | `Dinamico.tdesktop-theme` |
| 13 | obs | módulo propio | `Dinamico.obt` |
| 14 | millennium | integración en vivo | `~/.config/millennium/config.json` |

---

## 2. Requisitos

- KDE Plasma 6 sobre Wayland (probado en PikaOS 4, base Debian sid).
- `python3` 3.11 o superior.
- Las siguientes herramientas, que en Debian se instalan así:

```bash
sudo apt install matugen python3 inotify-tools util-linux libkf6config-bin
```

| Herramienta | Para qué la usa el motor |
| --- | --- |
| `matugen` | Genera la paleta de 50 roles a partir del acento |
| `inotifywait` | El servicio vigila `kdeglobals` en tiempo real |
| `flock` | Evita dos generaciones simultáneas |
| `kreadconfig6` | Lee `AccentColor` de forma nativa (si no está, usa su propio parser) |

Las apps que viven en Flatpak (OBS, Materialgram, Millennium) se detectan por
sus rutas bajo `~/.var/app/`; el motor escribe también en la ruta nativa por
si también las tienes instaladas de otra forma.

---

## 3. Instalación

```bash
git clone https://github.com/ezku100/accent-theme.git
cd accent-theme
./install.sh instalar
```

El instalador hace ocho cosas, en este orden:

1. Copia el motor a `~/.local/share/accent-theme/source`.
2. Crea el comando `~/.local/bin/accent-theme`.
3. Registra las nueve apps base en `~/.config/accent-theme/templates.d/`.
4. Copia a `~/.config/accent-theme/templates/` las plantillas que leen las
   apps que no son de Matugen (Materialgram y la base de OBS).
5. Genera `~/.config/accent-theme/matugen.toml` (no toca
   `~/.config/matugen/config.toml`).
6. Instala `~/.config/systemd/user/accent-theme.service`.
7. Guarda un backup fechado en `~/.local/share/accent-theme/backups/`.
8. Habilita `accent-theme.service` y, si todavía existe, deshabilita
   `kitty-theme-watch.service` **sin borrarlo**.

Es idempotente: puedes ejecutarlo tantas veces como quieras.

### Qué necesita una instalación limpia

No hace falta nada más para que las catorce apps queden temadas:

- Las plantillas viajan en el repo y el instalador las copia.
- OBS usa el tema `Venom` si lo tienes instalado y, si no, el tema base del
  propio repo (`templates/obs/base.obt`).
- Brave y Millennium se saltan si no están instalados, sin fallar.

---

## 4. Verificar que todo funciona

```bash
accent-theme doctor
```

Salida esperada en una máquina con todo instalado:

```
matugen: /home/TU_USUARIO/.local/bin/matugen
config: /home/TU_USUARIO/.config/accent-theme/matugen.toml
doctor: 9 integraciones correctas
cobertura: brave: ok; equibop: ok; materialgram: ok; obs: ok; millennium: ok
```

La línea `cobertura` dice el estado de las cinco apps que no son plantillas.
Si una no está instalada, aparece el motivo (`sin instalación`, `sin config`,
`sin plantilla`, `sin tema base`) y el comando sigue devolviendo éxito.

Para forzar una generación:

```bash
accent-theme generate
```

```
paleta generada con #b75bb4; 50 roles disponibles
apps: brave: applied; equibop: applied; materialgram: applied; obs: applied
recargas: kitty: skipped; ghostty: applied; zen: applied; cava: applied; millennium: applied
```

- `apps:` son las apps cuyo motor escribe su configuración.
- `recargas:` son las apps abiertas que se recargan en vivo. `skipped`
  significa que la app no está corriendo, no que haya un error.

---

## 5. Las catorce apps

### 5.1 Las nueve de plantilla

Se generan con Matugen a partir de `templates/` y `templates.d/`. El
resultado es un fichero que la app lee por su cuenta.

**kitty** — `~/.config/kitty/theme.conf`
Si el kitty está abierto, el motor le manda la orden de recargar por su
socket; no hay que reiniciar nada.

**ghostty** — `~/.config/ghostty/theme`
El motor toca el fichero de configuración para que Ghostty lo vuelva a leer.

**konsole** — `~/.local/share/konsole/Dinamico.colorscheme`
Se aplica a las sesiones nuevas. Para verlo en la actual: *Ajustes →
Esquemas de color → Dinamico*.

**kate** — `~/.local/share/org.kde.syntax-highlighting/themes/dinamico.theme`
Se aplica a las ventanas nuevas.

**cava** — `~/.cache/matugen-cava-snippet`
El motor inyecta el fragmento de color en `~/.config/cava/config`, dentro de
la sección `[general]`. Cava lo lee al arrancar.

**heroic** — `~/.config/heroic/themes/dinamico.css`
Heroic lo carga al arrancar.

**zen** — `~/.cache/matugen-zen-kde-accent.css`
El motor copia el CSS a cada perfil de Zen (`chrome/kde-accent.css`) y
asegura que `userChrome.css` lo importe con `@import`.

**steam** — `~/.local/share/Steam/millennium/themes/Material-Theme/css/main/colors/matugen.css`
Steam lo lee al arrancar.

**caparazon-shell** — `~/.cache/caparazon/colors.json`
La shell (Quickshell) escucha ese fichero y recarga la paleta al momento.

### 5.2 Las cinco que aplica el motor

Estas no encajan en una plantilla: escriben archivos donde Matugen no llega.

**brave**
Parchea el `Preferences` y el `Local State` de cada perfil de Brave con el
color de acento (el `profile_color_seed` y el `user_color` de tema).
Necesita Brave cerrado: si está abierto, el navegador pisa los cambios al
salir. El motor escribe en `~/.config/BraveSoftware/Brave-Browser/` y en la
ruta Flatpak `~/.var/app/com.brave.Browser/config/`.

**equibop**
Escribe `~/.config/equibop/themes/midnight-accent-kde.theme.css` con los
cinco tonos del acento en Oklch. El CSS queda listo en la carpeta de temas
de EquiBop; si tu versión pide elegir el tema a mano, selecciónalo una vez.

**materialgram**
Escribe `Dinamico.tdesktop-theme` (base SolidDark, cabecera y atribución
intactas) en las tres rutas donde Telegram Desktop lo busca:
`~/.var/app/io.github.kukuruzka165.materialgram/data/materialgram/tdata/`,
`~/.config/materialgram/themes/` y `~/Documents/`.
**Telegram no recarga el tema solo**: tras cambiar el acento hay que volver a
tocar *Dinamico* en la lista de temas.

**obs**
Escribe el tema `Dinamico.obt` en
`~/.var/app/com.obsproject.Studio/config/obs-studio/themes/` y en
`~/.config/obs-studio/themes/`.
El tema base es el `Venom.obt` de FM.VENOM si lo tienes instalado (y conserva
su crédito en la autoría); si no, se usa `templates/obs/base.obt`, que trae
las cinco ranuras de acento y un QSS oscuro completo.
**OBS no recarga el tema solo**: cambia a otro tema y vuelve a *Dinamico*.
Cuando el motor lo detecta, te avisa por `notify-send`.

**millennium**
Escribe el acento en `~/.config/millennium/config.json` (sección `general` y
el color del tema Material) y en el archivo espejo
`~/.config/millennium/dinamico-accent.txt`.

---

## 6. Comandos

```bash
accent-theme generate        # genera la paleta ahora
accent-theme watch           # vigila el acento (lo usa el servicio)
accent-theme doctor          # comprueba dependencias, registro y cobertura
accent-theme rebuild-config  # valida templates.d y regenera matugen.toml
accent-theme register --app NOMBRE --descriptor RUTA
```

`register` copia el descriptor y su plantilla a
`~/.config/accent-theme/` y regenera `matugen.toml`. Úsalo cuando añadas una
app nueva (ver [10](#10-añadir-una-app)).

---

## 7. El servicio

La unidad vive en `~/.config/systemd/user/accent-theme.service` y arranca
`accent-theme watch`.

```bash
systemctl --user status accent-theme.service     # estado
systemctl --user restart accent-theme.service    # reiniciar
systemctl --user stop accent-theme.service       # parar
journalctl --user -u accent-theme.service -f     # logs en vivo
```

El watcher vigila `~/.config/kdeglobals` con `inotifywait`, ignora los
temporales y `kdeglobals.lock`, y genera solo cuando el acento ha cambiado de
verdad. Usa `flock` sobre `~/.cache/accent-theme/feeder.lock` para que dos
generaciones nunca se pisen.

---

## 8. Cambiar el acento

1. Abre *Ajustes del sistema → Colores*.
2. Elige el color de acento.
3. En menos de un segundo se aplica a las catorce apps.

Si una app no cambia:

- Brave: ciérralo y vuelve a abrirlo.
- OBS y Materialgram: reaplica el tema a mano (ver [5.2](#52-las-cinco-que-aplica-el-motor)).
- Las de plantilla que ya estaban abiertas: reinicia esa app.

Para forzar una generación a mano: `accent-theme generate`.

---

## 9. Personalizar la paleta

La paleta se genera con Matugen en modo `scheme-fidelity`, tema oscuro y
salida en hexadecimal; esos flags están en la invocación del motor
(`src/accent_theme/matugen.py`) y no se tocan desde fuera.

`~/.config/accent-theme/matugen.toml` **no se edita a mano**: el motor lo
genera a partir de los descriptores de `~/.config/accent-theme/templates.d/`
y `accent-theme rebuild-config` lo regenera. Si quieres cambiar cómo se
calcula la paleta, edita el descriptor de la app y vuelve a registrar.

Lo que sí puedes editar son las plantillas, en
`~/.config/accent-theme/templates/<app>/`. Tras cambiarlas:

```bash
accent-theme generate
```

Las variables que usan las plantillas son las de Matugen:
`{{colors.<rol>.<esquema>.hex}}`, `{{colors.<rol>.<esquema>.rgb}}` y
`{{base16.baseNN.<esquema>.hex}}`.

Los marcadores que usa la plantilla de Materialgram son
`{{matugen_grey}}`, `{{matugen_bg}}`, `{{matugen_bg_over}}`,
`{{matugen_bg_over2}}`, `{{matugen_fg}}`, `{{matugen_accent}}`,
`{{matugen_accent_light}}` y `{{matugen_accent_pressed}}`.

### Cómo se publica el resultado

Matugen escribe en ficheros `.staging` (por ejemplo
`~/.cache/caparazon/colors.staging.json`) y el motor los renombra a su
nombre final de forma atómica, solo si la generación terminó bien. Por eso
una app nunca ve un fichero a medio escribir, y por eso un error de Matugen
deja el tema anterior intacto.

---

## 10. Añadir una app

Hay dos caminos. Usa el primero si la app solo necesita un fichero de tema;
el segundo si hay que tocar su configuración a mano.

### 10.1 Como app de plantilla (Matugen)

1. Crea la plantilla en `templates/mi-app/`, por ejemplo
   `templates/mi-app/mi-app-matugen.json`:

```json
{
  "primary": "{{colors.primary.dark.hex}}",
  "background": "{{colors.surface_container.dark.hex}}"
}
```

2. Crea el descriptor `templates.d/mi-app.toml`:

```toml
name = "mi-app-matugen"
input_path = "~/.config/accent-theme/templates/mi-app/mi-app-matugen.json"
output_path = "~/.cache/mi-app/colors.json"
```

   El descriptor admite una cuarta clave opcional, `saturation` (número
   `>= 1.0`), que multiplica la saturación HSV de cada color hexadecimal del
   template antes de publicarlo. Úsala cuando la paleta vaya sobre un fondo
   muy oscuro y el acento necesite más viveza; los grises neutros no cambian:

```toml
saturation = 1.45
```

3. Añade `mi-app` a `BASE_APPS` en `install.sh` y ejecuta
   `./install.sh instalar` para registrarla.

4. Comprueba con `accent-theme doctor`.

### 10.2 Como app del motor

Si la app necesita fusionar JSON, derivar un tema de otro archivo o tocar
varios sitios a la vez:

1. Crea `src/accent_theme/apps/mi_app.py` con una función `apply_mi_app(...)`
   que devuelva un `AppResult` (`applied`, `skipped` o `failed`).
2. Añade sus rutas a `AppPaths` en `src/accent_theme/apps/paths.py`.
3. Llámala desde `apply_app_integrations` en
   `src/accent_theme/apps/__init__.py`.
4. Si necesita una plantilla propia (como Materialgram o OBS), mete el
   fichero en `templates/mi-app/` y añádelo a `NATIVE_TEMPLATE_APPS` en
   `install.sh`.
5. Añade el caso al `doctor` para que se vea en la cobertura.
6. Escribe un test en `tests/test_apps.py`.

Reglas del código:

- Escribe siempre de forma atómica (`atomic_write_text` / `atomic_write_json`):
  muchas apps leen su configuración mientras están abiertas.
- Conserva los permisos que ya tenía el fichero; los nuevos, 644.
- Si la app no está instalada, devuelve `skipped` con el motivo. Nunca
  falles la generación por una app que no existe en la máquina.

---

## 11. Rutas

| Qué | Dónde |
| --- | --- |
| Motor | `~/.local/share/accent-theme/source/` |
| Comando | `~/.local/bin/accent-theme` |
| Configuración del motor | `~/.config/accent-theme/` |
| Config de Matugen del motor | `~/.config/accent-theme/matugen.toml` |
| Descriptores registrados | `~/.config/accent-theme/templates.d/` |
| Plantillas instaladas | `~/.config/accent-theme/templates/` |
| Unidad del servicio | `~/.config/systemd/user/accent-theme.service` |
| Backups | `~/.local/share/accent-theme/backups/<fecha>/` |
| Caché y bloqueo | `~/.cache/accent-theme/` |

---

## 12. Problemas frecuentes

**`doctor` dice `matugen no encontrado`.**
Falta el paquete: `sudo apt install matugen`.

**`doctor` dice `output ausente: ...`.**
La plantilla se registró pero su fichero de salida no existe. Ejecuta
`accent-theme generate`.

**Una app no cambia de color.**
1. `accent-theme doctor` → mira su estado en la línea `cobertura`.
2. `accent-theme generate` → ¿aparece `applied`?
3. Si aparece `applied` pero la app no cambia, es que la app no recarga en
   vivo: ciérrala y vuelve a abrirla (Brave, Heroic, Steam, Kate, Konsole) o
   reaplica el tema a mano (OBS, Materialgram).

**OBS dice `sin tema base`.**
No hay `Venom.obt` y tampoco está `templates/obs/base.obt` en
`~/.config/accent-theme/templates/obs/`. Ejecuta `./install.sh instalar`.

**Los cambios en `kdeglobals` no se ven.**
El servicio vigila ese fichero exacto: `systemctl --user restart
accent-theme.service` y revisa `journalctl --user -u accent-theme.service`.

**Quiero tocar una plantilla sin que el instalador me la pise.**
Edita la copia de `~/.config/accent-theme/templates/<app>/`, no la del repo.

---

## 13. Desinstalar

```bash
cd ~/Projects/accent-theme   # o donde clonaste el repo
./install.sh desinstalar
```

Deshabilita `accent-theme.service` y elimina el wrapper, la unidad y las
plantillas registradas. La configuración heredada nunca se borra; si la
unidad heredada (`kitty-theme-watch.service`) sigue presente, la rehabilita.
Los ficheros de tema que ya estaban escritos en las apps no se tocan.

---

## 14. Desarrollo

```bash
uv run pytest -q          # 93 tests
uv run ruff check .       # lint, select = ALL
```

Estructura del repo:

```
src/accent_theme/
  accent.py       lee el acento de KDE
  matugen.py      invoca Matugen y construye su entorno
  registry.py     descriptores TOML y matugen.toml
  watcher.py      vigilancia de kdeglobals con inotifywait
  cli.py          la interfaz de línea de comandos
  paths.py        rutas del motor
  apps/           las apps que el motor aplica por su cuenta
  live/           las recargas en vivo
templates/        las plantillas de cada app
templates.d/      un descriptor TOML por app
systemd/          la unidad del servicio
tests/            la suite
```

Convenciones:

- Python con tipos estrictos, `ruff` con `select = ALL`.
- Nada de `as any`, `@ts-ignore` ni silenciados de errores.
- Los ficheros de configuración se escriben de forma atómica.
- Todo cambio de comportamiento viene con su test.
