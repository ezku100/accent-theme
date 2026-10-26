#!/usr/bin/env python3
"""
Enlaza el AccentColor de KDE con Caelestia por su pipeline nativo (matugen).

Flujo: watch_accent.sh -> accent_to_matugen.py (feeder) -> este hook.
También corre suelto (lee el accent directo de kdeglobals).

Mecanismo: genera un PNG sólido con el accent y lo fija como wallpaper
interno de Caelestia (`caelestia wallpaper -f ... -N`). Caelestia deriva el
esquema dinámico completo con su propio matugen (fidelity total, fan-out a
GTK/Qt/terminales incluido). El escritorio Plasma NO cambia porque el sync
de fondo está desactivado en Wallpapers.qml (Waywallen es el dueño).
Se pinea modo dark + variante tonalspot con -N (sin smart que podría
elegir light ante un accent brillante).
"""
import colorsys
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge import get_accent_rgb, hsv_to_hex

CACHE_DIR = os.path.expanduser("~/.cache/caelestia-accent")


def _clean(v):
    if not v:
        return None
    v = v.strip().lstrip("#")
    return v if len(v) == 6 else None


def _key_accent():
    """AccentColor real de kdeglobals, sin fallbacks. None si no hay."""
    try:
        import configparser
        cfg = configparser.ConfigParser(strict=False)
        cfg.read(os.path.expanduser("~/.config/kdeglobals"))
        r, g, b = (int(x) for x in cfg["General"]["AccentColor"].split(","))
        return "%02x%02x%02x" % (r, g, b)
    except (KeyError, ValueError, OSError):
        return None


def main():
    caelestia = shutil.which("caelestia")
    if caelestia is None:
        print("caelestia: no instalado, salto.")
        return 0
    # Seguro anti-blanqueo: si no hay AccentColor real (ej. Plasma aún no
    # deriva al arrancar), el accent del entorno es un fallback y derivar
    # de él blanquearía el esquema. Se omite y se conserva el anterior.
    if _key_accent() is None:
        print("caelestia: sin AccentColor real, se conserva el esquema.")
        return 0
    accent = _clean(os.environ.get("MATUGEN_ACCENT"))
    if not accent:
        r, g, b = get_accent_rgb()
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        accent = _clean(hsv_to_hex(h, s, v))
    if not accent:
        print("caelestia: no pude leer el accent.")
        return 1

    os.makedirs(CACHE_DIR, exist_ok=True)
    png = os.path.join(CACHE_DIR, f"accent-{accent}.png")
    if not os.path.exists(png):
        try:
            from PIL import Image
        except ImportError:
            print("caelestia: falta Pillow, salto.")
            return 0
        Image.new("RGB", (256, 256),
                  tuple(int(accent[i:i + 2], 16) for i in (0, 2, 4))).save(png)

    proc = subprocess.run(
        [caelestia, "wallpaper", "-f", png, "-N"],
        capture_output=True, text=True, timeout=180)
    out = (proc.stdout or "").strip().replace("\n", " | ")[:200]
    err = (proc.stderr or "").strip().replace("\n", " | ")[:300]
    print(f"caelestia: accent {accent} -> wallpaper interno. exit={proc.returncode} {out} {err}")

    if proc.returncode == 0:
        info = subprocess.run(
            [caelestia, "scheme", "get", "-n", "-m"],
            capture_output=True, text=True, timeout=30)
        print(f"caelestia: esquema ahora: {(info.stdout or '').strip()[:120]}")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
