# accent-theme

Motor global de tema para KDE Plasma basado en `AccentColor` y
[Matugen](https://github.com/Innovative-System-Design/Matugen).

Lee el color de acento de `~/.config/kdeglobals`, genera una paleta Material
completa y la reparte entre las aplicaciones integradas: Kitty, Ghostty,
Konsole, Kate, Cava, Heroic, Zen Browser, Millennium (Steam) y Caparazón
Shell. Un servicio de usuario regenera la paleta cada vez que cambia el
acento.

Cuatro apps más no encajan en una plantilla de Matugen, porque escriben su
configuración en sitios donde una plantilla no llega (un JSON que hay que
fusionar con lo que ya había, un tema que se deriva de otro archivo). El
motor las aplica directamente: Brave, EquiBop, Materialgram y OBS Studio.

## Requisitos

| Dependencia | Paquete Debian | Uso |
| --- | --- | --- |
| `matugen` | `matugen` | Genera la paleta y los archivos por app |
| `python3` (>= 3.11) | `python3` | Ejecuta el motor |
| `inotifywait` | `inotify-tools` | Vigila `kdeglobals` |
| `flock` | `util-linux` | Serializa las regeneraciones |
| `kreadconfig6` | `libkf6config-bin` | Lee `AccentColor` |

```bash
sudo apt install matugen python3 inotify-tools util-linux libkf6config-bin
```

## Instalación

```bash
git clone https://github.com/ezku100/accent-theme.git
cd accent-theme
./install.sh instalar
```

El instalador:

1. Copia el motor a `~/.local/share/accent-theme/source`.
2. Crea el comando `~/.local/bin/accent-theme`.
3. Registra las nueve apps base en `~/.config/accent-theme/templates.d/`.
4. Copia a `~/.config/accent-theme/templates/` las plantillas que leen las
   apps que no son de Matugen (Materialgram y la base de OBS).
5. Genera `~/.config/accent-theme/matugen.toml` (sin tocar
   `~/.config/matugen/config.toml`).
6. Instala `~/.config/systemd/user/accent-theme.service`.
7. Genera un backup fechado en `~/.local/share/accent-theme/backups/`.
8. Habilita `accent-theme.service` y, si aún existe, deshabilita
   `kitty-theme-watch.service` **sin borrarlo**.

Es idempotente: puedes ejecutarlo las veces que quieras. No hace falta
tener nada más instalado para que las catorce apps queden temadas: las que
dependen de un archivo de la máquina (OBS con Venom, Brave con sus perfiles)
caen a su equivalente del repo o se saltan sin fallar.

### Desinstalación

```bash
./install.sh desinstalar
```

Deshabilita `accent-theme.service` y elimina el wrapper y la unit. La
configuración heredada nunca se borra; si la unidad heredada sigue presente, la
rehabilita.

## Uso

```bash
accent-theme generate        # genera la paleta ahora
accent-theme watch           # vigila el acento (lo usa el servicio)
accent-theme doctor          # comprueba dependencias, registro y outputs
accent-theme rebuild-config  # valida templates.d y regenera matugen.toml
accent-theme register --app NOMBRE --descriptor RUTA
```

### Apps que aplica el motor

El motor temea catorce aplicaciones. Nueve son plantillas de Matugen (kitty,
ghostty, konsole, kate, cava, heroic, zen, steam y caparazon-shell) y las
cinco restantes las aplica él mismo, escribiendo su configuración en
`src/accent_theme/apps/` y `src/accent_theme/live/`.

| App | Qué hace |
| --- | --- |
| Brave | Parchea `Local State` y `Preferences` con el color de acento |
| EquiBop | Escribe el tema CSS con los tonos del acento |
| Materialgram | Escribe el tema `.tdesktop-theme` desde la plantilla de SolidDark |
| OBS Studio | Escribe el tema `Dinamico` a partir del tema Venom instalado, o del propio (`templates/obs/base.obt`) si no lo hay |
| Millennium | Escribe el color de acento en su configuración |

Si una app no está instalada, su paso se salta sin fallar. `accent-theme
doctor` dice qué queda temado en cada máquina:

```
doctor: 9 integraciones correctas
cobertura: brave: ok; equibop: ok; materialgram: ok; obs: ok; millennium: ok
```

### Integrar otra aplicación

Publica un template de Matugen y un descriptor TOML:

```toml
name = "mi-app-matugen"
input_path = "~/.config/accent-theme/templates/mi-app/mi-app-matugen.json"
output_path = "~/.cache/mi-app/colors.json"
```

Y regístrala:

```bash
accent-theme register --app mi-app --descriptor ./mi-app.toml
```

El registro valida que el template exista, que el destino esté dentro del
`HOME` y que no haya nombres duplicados.

## Rutas

```text
~/.local/share/accent-theme/source/       # motor instalado
~/.local/share/accent-theme/backups/      # backups de la migración
~/.local/bin/accent-theme                 # comando de usuario
~/.config/accent-theme/templates.d/       # un descriptor por app
~/.config/accent-theme/templates/         # templates instaladas
~/.config/accent-theme/matugen.toml       # config generada para Matugen
~/.config/systemd/user/accent-theme.service
```

## Rollback

El servicio heredado `kitty-theme-watch.service` ya no existe: el motor
`accent-theme` es el único que regenera el tema. Cada instalación deja un
backup en `~/.local/share/accent-theme/backups/` con la unit y la configuración
del motor; desde ahí puedes restaurar una instalación anterior.

## Desarrollo

```bash
uv sync
uv run pytest tests/ -q
uv run ruff check .
uv run basedpyright
```

## Licencia

MIT. Ver [LICENSE](LICENSE).
