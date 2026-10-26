# accent-theme

Motor global de tema para KDE Plasma basado en `AccentColor` y
[Matugen](https://github.com/Innovative-System-Design/Matugen).

Lee el color de acento de `~/.config/kdeglobals`, genera una paleta Material
completa y la reparte entre las aplicaciones integradas: Kitty, Ghostty,
Konsole, Kate, Cava, Heroic, Zen Browser y Millennium (Steam). Un servicio de
usuario regenera la paleta cada vez que cambia el acento.

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
3. Registra las ocho apps base en `~/.config/accent-theme/templates.d/`.
4. Genera `~/.config/accent-theme/matugen.toml` (sin tocar
   `~/.config/matugen/config.toml`).
5. Instala `~/.config/systemd/user/accent-theme.service`.
6. Genera un backup fechado en `~/.local/share/accent-theme/backups/`.
7. Deshabilita `kitty-theme-watch.service` **sin borrarlo** y habilita
   `accent-theme.service`.

Es idempotente: puedes ejecutarlo las veces que quieras.

### Desinstalación

```bash
./install.sh desinstalar
```

Deshabilita `accent-theme.service`, rehabilita `kitty-theme-watch.service` y
elimina el wrapper y la unit. La configuración heredada nunca se borra.

## Uso

```bash
accent-theme generate        # genera la paleta ahora
accent-theme watch           # vigila el acento (lo usa el servicio)
accent-theme doctor          # comprueba dependencias, registro y outputs
accent-theme rebuild-config  # valida templates.d y regenera matugen.toml
accent-theme register --app NOMBRE --descriptor RUTA
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

Si algo no cuadra, vuelve al servicio heredado:

```bash
systemctl --user disable --now accent-theme.service
systemctl --user enable --now kitty-theme-watch.service
```

`kitty-theme-watch.service` y `~/.config/kitty/` se conservan intactos, así que
el rollback es inmediato. Los backups de la migración están en
`~/.local/share/accent-theme/backups/`.

## Desarrollo

```bash
uv sync
uv run pytest tests/ -q
uv run ruff check .
uv run basedpyright
```

## Licencia

MIT. Ver [LICENSE](LICENSE).
