#!/bin/bash
# Instalador del motor global de tema accent-theme.
#
# Uso:
#   ./install.sh instalar
#   ./install.sh desinstalar
#
# El instalador nunca borra la configuración heredada: la deja intacta como
# rollback y solo migra el servicio de usuario.

set -euo pipefail

PROGRAM_NAME="install.sh"
LEGACY_UNIT="kitty-theme-watch.service"
NEW_UNIT="accent-theme.service"
BASE_APPS=(kitty ghostty konsole kate cava heroic zen steam)
INSTALL_ITEMS=(src hooks templates templates.d systemd)
REQUIRED_INSTALL_DEPS=(matugen python3 inotifywait flock kreadconfig6)
REQUIRED_UNINSTALL_DEPS=(systemctl)
APT_PACKAGES="matugen inotify-tools util-linux libkf6config-bin"

die() {
  printf '%s: %s\n' "$PROGRAM_NAME" "$1" >&2
  exit 1
}

warn() {
  printf '%s: aviso: %s\n' "$PROGRAM_NAME" "$1" >&2
}

note() {
  printf '%s: %s\n' "$PROGRAM_NAME" "$1"
}

script_root() {
  local source="${BASH_SOURCE[0]}"
  local directory
  if [[ "$source" != */* ]]; then
    directory="$PWD"
  else
    directory="${source%/*}"
  fi
  (cd -- "$directory" && pwd -P)
}

SOURCE_ROOT="$(script_root)"
HOME_DIR="${HOME:-}"
[ -n "$HOME_DIR" ] || die "HOME no está definido"

XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME_DIR/.local/share}"
XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME_DIR/.config}"
XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME_DIR/.cache}"

ENGINE_DIR="$XDG_DATA_HOME/accent-theme/source"
CONFIG_DIR="$XDG_CONFIG_HOME/accent-theme"
TEMPLATES_DIR="$CONFIG_DIR/templates"
DESCRIPTORS_DIR="$CONFIG_DIR/templates.d"
UNIT_DIR="$XDG_CONFIG_HOME/systemd/user"
UNIT_PATH="$UNIT_DIR/$NEW_UNIT"
WRAPPER_DIR="$HOME_DIR/.local/bin"
WRAPPER_PATH="$WRAPPER_DIR/accent-theme"
BACKUP_DIR="$XDG_DATA_HOME/accent-theme/backups"

usage() {
  printf 'uso: %s [instalar|desinstalar]\n' "$PROGRAM_NAME" >&2
}

require_dependencies() {
  local -a names=("$@")
  local missing=()
  local name
  for name in "${names[@]}"; do
    if ! command -v "$name" >/dev/null 2>&1; then
      missing+=("$name")
    fi
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    printf '%s: faltan dependencias: %s\n' "$PROGRAM_NAME" "${missing[*]}" >&2
    printf '%s: instálalas con: sudo apt install %s\n' "$PROGRAM_NAME" "$APT_PACKAGES" >&2
    exit 1
  fi
}

install_engine_source() {
  if [ "$SOURCE_ROOT" = "$ENGINE_DIR" ]; then
    return 0
  fi
  mkdir -p "$ENGINE_DIR"
  local item
  for item in "${INSTALL_ITEMS[@]}"; do
    if [ -e "$SOURCE_ROOT/$item" ]; then
      mkdir -p "$ENGINE_DIR/$item"
      cp -a "$SOURCE_ROOT/$item/." "$ENGINE_DIR/$item/"
    fi
  done
  for item in pyproject.toml README.md LICENSE; do
    if [ -e "$SOURCE_ROOT/$item" ]; then
      cp -a "$SOURCE_ROOT/$item" "$ENGINE_DIR/$item"
    fi
  done
}

install_wrapper() {
  mkdir -p "$WRAPPER_DIR"
  cat > "$WRAPPER_PATH" <<WRAPPER
#!/bin/sh
# Generado por $PROGRAM_NAME; no editar a mano.
ACCENT_THEME_SOURCE="$ENGINE_DIR"
if [ -n "\${PYTHONPATH:-}" ]; then
  PYTHONPATH="\$ACCENT_THEME_SOURCE/src:\$PYTHONPATH"
else
  PYTHONPATH="\$ACCENT_THEME_SOURCE/src"
fi
export PYTHONPATH
exec python3 -m accent_theme "\$@"
WRAPPER
  chmod 0755 "$WRAPPER_PATH"
}

register_base_apps() {
  local app
  local staging
  for app in "${BASE_APPS[@]}"; do
    if [ ! -f "$SOURCE_ROOT/templates.d/$app.toml" ]; then
      warn "falta el descriptor de $app; se omite"
      continue
    fi
    staging="$(mktemp -d)"
    cp -a "$SOURCE_ROOT/templates/$app/." "$staging/"
    cp -a "$SOURCE_ROOT/templates.d/$app.toml" "$staging/$app.toml"
    PYTHONPATH="$ENGINE_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
      python3 -m accent_theme register --app "$app" --descriptor "$staging/$app.toml"
    rm -rf "$staging"
  done
}

install_service_unit() {
  mkdir -p "$UNIT_DIR"
  cp -a "$SOURCE_ROOT/systemd/$NEW_UNIT" "$UNIT_PATH"
}

backup_current_state() {
  local stamp
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  local destination="$BACKUP_DIR/$stamp"
  mkdir -p "$destination"
  if [ -f "$UNIT_DIR/$LEGACY_UNIT" ]; then
    cp -a "$UNIT_DIR/$LEGACY_UNIT" "$destination/$LEGACY_UNIT"
  fi
  if [ -f "$UNIT_PATH" ]; then
    cp -a "$UNIT_PATH" "$destination/$NEW_UNIT"
  fi
  if [ -d "$CONFIG_DIR" ]; then
    cp -a "$CONFIG_DIR" "$destination/accent-theme"
  fi
  printf '%s\n' "$destination"
}

migrate_service() {
  systemctl --user daemon-reload || warn "no se pudo recargar systemd --user"
  systemctl --user disable --now "$LEGACY_UNIT" \
    || warn "no se pudo deshabilitar $LEGACY_UNIT"
  systemctl --user enable --now "$NEW_UNIT" \
    || warn "no se pudo habilitar $NEW_UNIT"
}

generate_palette() {
  "$WRAPPER_PATH" generate
}

install_engine() {
  require_dependencies "${REQUIRED_INSTALL_DEPS[@]}"
  install_engine_source
  install_wrapper
  register_base_apps
  install_service_unit
  local backup
  backup="$(backup_current_state)"
  note "backup de la migración: $backup"
  migrate_service
  generate_palette
  note "instalación completada"
}

remove_base_registrations() {
  local app
  for app in "${BASE_APPS[@]}"; do
    rm -f "$DESCRIPTORS_DIR/$app.toml"
    rm -rf "$TEMPLATES_DIR/$app"
  done
}

uninstall_engine() {
  require_dependencies "${REQUIRED_UNINSTALL_DEPS[@]}"
  systemctl --user disable --now "$NEW_UNIT" || warn "no se pudo deshabilitar $NEW_UNIT"
  systemctl --user enable --now "$LEGACY_UNIT" \
    || warn "no se pudo rehabilitar $LEGACY_UNIT"
  rm -f "$WRAPPER_PATH"
  rm -f "$UNIT_PATH"
  systemctl --user daemon-reload || warn "no se pudo recargar systemd --user"
  remove_base_registrations
  if [ -d "$ENGINE_DIR/src" ]; then
    PYTHONPATH="$ENGINE_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
      python3 -m accent_theme rebuild-config >/dev/null 2>&1 \
      || warn "no se pudo regenerar matugen.toml"
  fi
  note "desinstalación completada; el servicio heredado queda habilitado"
}

ACTION="${1:-}"
case "$ACTION" in
  instalar)
    install_engine
    ;;
  desinstalar)
    uninstall_engine
    ;;
  *)
    usage
    die "acción desconocida: '${ACTION}'; usa 'instalar' o 'desinstalar'"
    ;;
esac
