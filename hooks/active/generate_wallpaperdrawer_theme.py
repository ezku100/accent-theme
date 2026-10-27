#!/usr/bin/env python3
"""
Genera los colores de Wallpaper Drawer (com.atopion.gamedrawer)
a partir del Accent Color de KDE.

Mapeo (igual que NothingIsland / kitty para ir a juego):
  bgColor     -> fondo oscuro teñido con el hue del accent
  accentColor -> EL ACCENT tal cual (bordes de tarjetas + marco)
  textColor   -> blanco casi puro con rastro del tinte
  bgOpacity / cornerRadius no se tocan (estilo fijado en config)

Escribe vía kwriteconfig6 con --notify + evaluateScript en vivo,
igual que generate_nothingisland_theme.py. Las claves son String
con hex (#rrggbb), así QML las entiende tanto en disco como en vivo.
"""
import colorsys
import configparser
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge import get_accent_rgb, hsv_to_hex

APPLETSRC = os.path.expanduser("~/.config/plasma-org.kde.plasma.desktop-appletsrc")
PLUGIN_ID = "com.ezku.wallpaperdrawer"
APPLETS_FILE = "plasma-org.kde.plasma.desktop-appletsrc"


def find_drawer_applets():
    cfg = configparser.ConfigParser(strict=False)
    cfg.read(APPLETSRC)
    found = []
    for section in cfg.sections():
        if "Applets" not in section:
            continue
        try:
            if cfg[section].get("plugin", "").strip() != PLUGIN_ID:
                continue
        except Exception:
            continue
        parts = section.split("][")
        try:
            ci = parts[parts.index("Containments") + 1]
            ai = parts[parts.index("Applets") + 1]
            found.append((ci, ai))
        except (ValueError, IndexError):
            continue
    return found


def set_value(cid, aid, key, value):
    cmd_base = [
        "kwriteconfig6",
        "--file", APPLETS_FILE,
        "--group", "Containments",
        "--group", cid,
        "--group", "Applets",
        "--group", aid,
        "--group", "Configuration",
        "--group", "General",
        "--key", key,
        "--notify",
    ]
    try:
        subprocess.run(cmd_base + [value], check=True, timeout=5)
    except subprocess.CalledProcessError:
        subprocess.run(cmd_base[:-1] + [value], check=True, timeout=5)


def apply_live(cid, values):
    writes = "\n".join(
        f'w.writeConfig("{k}", "{v}");' for k, v in values.items()
    )
    js = (
        f'var p = panelById({cid});\n'
        f'var ws = p.widgets("{PLUGIN_ID}");\n'
        f'for (var i = 0; i < ws.length; i++) {{\n'
        f'  var w = ws[i];\n'
        f'  w.currentConfigGroup = ["General"];\n'
        f'{writes}\n'
        f'}}'
    )
    try:
        subprocess.run(
            ["qdbus6", "org.kde.plasmashell", "/PlasmaShell",
             "org.kde.PlasmaShell.evaluateScript", js],
            check=True, timeout=10,
            capture_output=True,
        )
        return True
    except Exception as e:
        print(f"Aviso: no se pudo aplicar en vivo ({e}), quedará al reiniciar plasmashell.")
        return False


def main():
    r, g, b = get_accent_rgb()
    h, s, v = colorsys.rgb_to_hsv(r, g, b)

    bg = hsv_to_hex(h, min(0.35, s), 0.09)
    accent = hsv_to_hex(h, s, v)
    fg = hsv_to_hex(h, min(0.03, s), 0.97)
    bg = os.environ.get("MATUGEN_BG", bg)
    accent, fg = os.environ.get("MATUGEN_ACCENT", accent), os.environ.get("MATUGEN_FG", fg)

    applets = find_drawer_applets()
    if not applets:
        print(f"No se encontró {PLUGIN_ID} en {APPLETSRC} (¿widget instalado en el panel?).")
        return

    values = {
        "bgColor": bg,
        "accentColor": accent,
        "textColor": fg,
    }
    for cid, aid in applets:
        for key, val in values.items():
            set_value(cid, aid, key, val)
        live = apply_live(cid, values)
        estado = "en vivo" if live else "persistido (reinicia plasmashell para verlo)"
        print(f"GameDrawer-Wallpaper [{cid}/{aid}]: fondo {bg}, acento {accent}, texto {fg} — {estado}.")


if __name__ == "__main__":
    main()
