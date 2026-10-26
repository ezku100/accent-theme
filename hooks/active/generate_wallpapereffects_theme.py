#!/usr/bin/env python3
"""
Fondo de Wallpaper Effects (luisbocanegra.desktop.wallpaper.effects)
dinámico con transparencia, a partir del Accent de KDE.

El widget no ofrece alfa en su interfaz (showAlphaChannel: false),
pero su QML hace `color: main.borderColor` y acepta hex de 8 dígitos
#AARRGGBB sin problema. Así que se fuerza:
  borderColorMode = 0 (Custom, en vez de System)
  borderColor     = #AA + fondo teñido (igual que kitty/island)

OPACIDAD: 1.0 = opaco, 0.0 = invisible. 0.7 queda "algo transparente".
Cámbialo acá arriba y listo (el watcher lo reaplica solo).
"""
import colorsys
import configparser
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge import get_accent_rgb, hsv_to_hex

OPACIDAD = 0.97

APPLETSRC = os.path.expanduser("~/.config/plasma-org.kde.plasma.desktop-appletsrc")
PLUGIN_ID = "luisbocanegra.desktop.wallpaper.effects"
APPLETS_FILE = "plasma-org.kde.plasma.desktop-appletsrc"


def find_effect_applets():
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


def persist(cid, aid, key, value):
    subprocess.run(
        ["kwriteconfig6",
         "--file", APPLETS_FILE,
         "--group", "Containments", "--group", cid,
         "--group", "Applets", "--group", aid,
         "--group", "Configuration", "--group", "General",
         "--key", key, "--notify", value],
        check=True, timeout=5,
    )


def apply_live(cid, mode, color):
    js = (
        f'var ws = [];\n'
        f'try {{\n'
        f'  var ds = desktops();\n'
        f'  for (var d = 0; d < ds.length; d++) {{\n'
        f'    var dw = ds[d].widgets("{PLUGIN_ID}");\n'
        f'    for (var k = 0; k < dw.length; k++) ws.push(dw[k]);\n'
        f'  }}\n'
        f'}} catch(e) {{ print("desktop err "+e); }}\n'
        f'try {{\n'
        f'  for (var i = 0; i < panelIds.length; i++) {{\n'
        f'    var pw = panelById(panelIds[i]).widgets("{PLUGIN_ID}");\n'
        f'    for (var k = 0; k < pw.length; k++) ws.push(pw[k]);\n'
        f'  }}\n'
        f'}} catch(e) {{ print("panel err "+e); }}\n'
        f'for (var i = 0; i < ws.length; i++) {{\n'
        f'  ws[i].currentConfigGroup = ["General"];\n'
        f'  ws[i].writeConfig("borderColorMode", {mode});\n'
        f'  ws[i].writeConfig("borderColor", "{color}");\n'
        f'}}\n'
        f'print("aplicados: "+ws.length);'
    )
    try:
        subprocess.run(
            ["qdbus6", "org.kde.plasmashell", "/PlasmaShell",
             "org.kde.PlasmaShell.evaluateScript", js],
            check=True, timeout=10, capture_output=True,
        )
        return True
    except Exception as e:
        print(f"Aviso: no se pudo aplicar en vivo ({e}).")
        return False


def main():
    r, g, b = get_accent_rgb()
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    bg = hsv_to_hex(h, min(0.35, s), 0.09)
    bg = os.environ.get("MATUGEN_BG", bg)
    alpha = int(round(max(0.0, min(1.0, OPACIDAD)) * 255))
    argb = f"#{alpha:02X}{bg.lstrip('#')}"

    applets = find_effect_applets()
    if not applets:
        print(f"No se encontró {PLUGIN_ID} (¿widget en el escritorio?).")
        return
    for cid, aid in applets:
        persist(cid, aid, "borderColorMode", "0")
        persist(cid, aid, "borderColor", argb)
        live = apply_live(cid, 0, argb)
        estado = "en vivo" if live else "persistido"
        print(f"WallpaperEffects [{cid}/{aid}]: fondo {argb} (opacidad {OPACIDAD}) — {estado}.")


if __name__ == "__main__":
    main()
