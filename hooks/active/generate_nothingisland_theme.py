#!/usr/bin/env python3
"""
Genera los colores de Nothing Dynamic Island (org.omar.nothingisland)
a partir del Accent Color de KDE.

Mapeo (respeta el estilo Nothing, pero teñido):
  colorFondo     -> fondo oscuro teñido (igual que kitty bg)
  colorTarjeta   -> tarjeta un poco más clara (kitty bg_alt)
  colorInvertida -> EL ACCENT tal cual (tarjeta activa / "encendido")
  colorTexto     -> blanco casi puro con rastro del tinte
  colorAlerta    -> no se toca (rojo crítico)

Escribe vía kwriteconfig6 con --notify para que Plasma lo aplique
en vivo sin reiniciar plasmashell. Descubre los IDs de containment/
applet dinámicamente (no van hardcodeados porque cambian si se
recrea el panel).
"""
import colorsys
import configparser
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge import get_accent_rgb, hsv_to_hex

APPLETSRC = os.path.expanduser("~/.config/plasma-org.kde.plasma.desktop-appletsrc")
PLUGIN_ID = "org.omar.nothingisland"
APPLETS_FILE = "plasma-org.kde.plasma.desktop-appletsrc"


def hex_to_kde_rgb(hx):
    hx = hx.lstrip("#")
    r, g, b = (int(hx[i:i + 2], 16) for i in (0, 2, 4))
    return f"{r},{g},{b}"


def find_island_applets():
    """Devuelve lista de (containment_id, applet_id) para Nothing Island."""
    cfg = configparser.ConfigParser(strict=False)
    cfg.read(APPLETSRC)
    found = []
    for section in cfg.sections():
        # secciones tipo: Containments][115][Applets][116
        if "Applets" not in section:
            continue
        try:
            if cfg[section].get("plugin", "").strip() != PLUGIN_ID:
                continue
        except Exception:
            continue
        # section viene sin corchete inicial: "Containments][115][Applets][116"
        parts = section.replace("[", "").replace("]", "").split("][") if False else section.split("][")
        # forma real: 'Containments][115][Applets][116' -> ['Containments', '115', 'Applets', '116']
        try:
            ci = parts[parts.index("Containments") + 1]
            ai = parts[parts.index("Applets") + 1]
            found.append((ci, ai))
        except (ValueError, IndexError):
            continue
    return found


def set_color(cid, aid, key, rgb):
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
    # --notify avisa a plasmashell para recarga en vivo
    try:
        subprocess.run(cmd_base + [rgb], check=True, timeout=5)
    except subprocess.CalledProcessError:
        subprocess.run(cmd_base[:-1] + [rgb], check=True, timeout=5)


def apply_live(cid, hex_colors):
    """Aplica en vivo vía scripting de plasmashell (sin reiniciar).

    kwriteconfig persiste en disco pero plasmashell no siempre recarga
    solo; writeConfig por evaluateScript sí actualiza los Bindings
    de main.qml al instante.

    OJO: en vivo se pasa el color en hex (#rrggbb). El formato "r,g,b"
    de KConfig en disco QML no siempre lo parsea en vivo y el texto
    caía a negro (ilegible). Con hex QML lo entiende seguro.
    """
    writes = "\n".join(
        f'w.writeConfig("{k}", "{v}");' for k, v in hex_colors.items()
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
    card = hsv_to_hex(h, min(0.35, s), 0.13)
    accent = hsv_to_hex(h, s, v)
    fg = hsv_to_hex(h, min(0.03, s), 0.97)
    bg, card = os.environ.get("MATUGEN_BG", bg), os.environ.get("MATUGEN_CARD", card)
    accent, fg = os.environ.get("MATUGEN_ACCENT", accent), os.environ.get("MATUGEN_FG", fg)

    applets = find_island_applets()
    if not applets:
        print(f"No se encontró {PLUGIN_ID} en {APPLETSRC} (¿widget instalado en el panel?).")
        return

    colors = {
        "colorFondo": hex_to_kde_rgb(bg),
        "colorTarjeta": hex_to_kde_rgb(card),
        "colorInvertida": hex_to_kde_rgb(accent),
        "colorTexto": hex_to_kde_rgb(fg),
    }
    for cid, aid in applets:
        for key, rgb in colors.items():
            set_color(cid, aid, key, rgb)
        hex_colors = {
            "colorFondo": bg,
            "colorTarjeta": card,
            "colorInvertida": accent,
            "colorTexto": fg,
        }
        live = apply_live(cid, hex_colors)
        estado = "en vivo" if live else "persistido (reinicia plasmashell para verlo)"
        print(f"NothingIsland [{cid}/{aid}]: fondo {bg}, tarjeta {card}, activa {accent} (accent KDE) — {estado}.")


if __name__ == "__main__":
    main()
