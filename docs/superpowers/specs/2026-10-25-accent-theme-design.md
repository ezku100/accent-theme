# Diseño: `accent-theme`

**Estado:** aprobado por el usuario el 2026-10-25.

## Objetivo

Extraer el motor global de tema de KDE/Matugen desde `~/.config/kitty/` a un repositorio público independiente, `ezku100/accent-theme`, y hacer que `caparazon-shell/install.sh` instale ese motor y registre la plantilla de Quickshell para que la shell deje de depender de una paleta de reserva silenciosa.

## Alcance

- Motor central para leer `AccentColor` de KDE, ejecutar Matugen y generar todas las plantillas registradas.
- Watcher global y servicio systemd de usuario con nombre nuevo `accent-theme.service`.
- Plantillas Matugen de las apps que actualmente usa el usuario.
- Hooks legacy activos, separados de la configuración de Kitty.
- Registro declarativo por app: cada integración publica una plantilla y un descriptor; añadir una app no exige editar un `config.toml` central.
- Integración de `caparazon-shell` con una plantilla propia y un instalador que deja `~/.cache/caparazon/colors.json` generado y validado.
- Migración local reversible desde `kitty-theme-watch.service`.

## Fuera de alcance

- Convertir todas las apps legacy en integraciones Matugen puras.
- Sustituir todavía los hooks que dependen de APIs específicas de una app.
- Eliminar destructivamente los archivos legados; la migración los conserva como rollback.
- Añadir una GUI al motor.

## Arquitectura

### Repositorio y rutas instaladas

`accent-theme` será un proyecto Python estándar, sin dependencias runtime obligatorias:

```text
accent-theme/
├── src/accent_theme/
│   ├── accent.py       # lectura y conversión de AccentColor
│   ├── cli.py          # generate, rebuild-config, doctor
│   ├── hooks.py        # ejecución de hooks legacy
│   ├── matugen.py      # locating, invocation y parsing JSON
│   └── registry.py     # descriptors y agregación TOML
├── templates/          # templates de apps gestionadas por el motor
├── hooks/              # hooks legacy migrados
├── systemd/            # accent-theme.service
├── install.sh          # instalación/migración/desinstalación
└── tests/
```

Rutas de usuario:

```text
~/.local/share/accent-theme/       # runtime del motor
~/.local/bin/accent-theme          # comando de usuario
~/.config/accent-theme/
├── templates.d/*.toml             # un descriptor por app
├── templates/<app>/               # templates instaladas
└── matugen.toml                   # config generada para Matugen
~/.config/systemd/user/accent-theme.service
```

### Registro por app

Cada app publica un descriptor TOML en `~/.config/accent-theme/templates.d/`. El formato normalizado es:

```toml
name = "quickshell-matugen"
input_path = "~/.config/accent-theme/templates/caparazon-shell/quickshell-matugen.json"
output_path = "~/.cache/caparazon/colors.json"
```

`accent-theme rebuild-config` valida los descriptors, rechaza nombres duplicados y genera `~/.config/accent-theme/matugen.toml` con una sección `[templates.<name>]` por integración. Matugen recibe ese archivo con `-c`; por tanto el `~/.config/matugen/config.toml` personal del usuario no se sobrescribe.

Una app nueva debe:

1. Publicar su template.
2. Publicar su descriptor.
3. Copiar ambos a `~/.config/accent-theme/` durante su instalador.

No hay que editar un archivo central.

### Flujo de generación

1. El watcher detecta cambios en `~/.config/kdeglobals` y, si existe, en la configuración de Waywallen.
2. `accent-theme generate` lee `AccentColor` con `kreadconfig6` y un fallback parseable.
3. Ejecuta `matugen -c ~/.config/accent-theme/matugen.toml color hex <accent> -t scheme-fidelity -m dark -j hex`.
4. Matugen genera todos los outputs declarados en el registro.
5. El motor parsea la misma salida JSON y expone tokens `MATUGEN_*` a los hooks legacy.
6. Se ejecutan los hooks disponibles; un hook ausente no es un error.
7. Se recargan en vivo las apps que lo soportan.

### Migración y rollback

La instalación nueva:

- Deshabilita, pero no borra, `kitty-theme-watch.service`.
- Instala y habilita `accent-theme.service`.
- Conserva los archivos heredados en `~/.config/kitty/`.
- Genera un backup fechado de los archivos/configs tocados antes de migrar.

Rollback manual:

```bash
systemctl --user disable --now accent-theme.service
systemctl --user enable --now kitty-theme-watch.service
```

La configuración legacy permanece suficiente para ese rollback.

## Integración de Caparazón

`caparazon-shell` publica:

```text
integration/theme/quickshell-matugen.json
integration/theme/accent-theme.toml
```

Su `install.sh`:

1. Instala la shell y el puente existentes.
2. Obtiene `ezku100/accent-theme` mediante clone/pull en `~/.local/share/accent-theme/source`.
3. Ejecuta el instalador del motor y registra la plantilla de Caparazón.
4. Genera la paleta y valida que `~/.cache/caparazon/colors.json` exista y contenga todos los tokens requeridos.
5. Falla con un mensaje accionable si Matugen, `inotifywait`, `flock` o `kreadconfig6` faltan.

`MatugenPalette.qml` conserva la reserva para que la shell pueda arrancar, pero deja de ocultar errores de lectura para que una instalación rota sea diagnosticable.

## Pruebas y criterios de aceptación

- Pruebas unitarias para lectura de acento, conversión de color, parsing de la salida JSON de Matugen y agregación de descriptors.
- Pruebas de idempotencia: registrar la misma app dos veces no duplica entradas ni daña el archivo.
- Smoke test con una paleta temporal: Matugen produce un JSON válido y todos los outputs esperados existen.
- Test de migración: el servicio viejo queda deshabilitado, el nuevo habilitado/activo y el legacy conserva rollback.
- `caparazon-shell/install.sh` debe completar una instalación limpia en un `HOME` temporal sin tocar la sesión real.
- Verificación final: `systemctl --user status accent-theme.service`, `accent-theme doctor`, tests, lint, type-check y revisión de ambos repositorios.

## Riesgos

- **Matugen no soporta includes:** el motor genera un config TOML propio; nunca se edita el config personal a mano.
- **Hooks específicos:** se aíslan y reportan su estado, pero no se reescriben todos en esta migración.
- **Cambio de servicio durante Plasma:** el backup y el servicio legacy intacto hacen que la reversión sea inmediata.
- **Dependencias del sistema:** el instalador detecta dependencias ausentes y ofrece el comando apt exacto; no oculta el fallo.
