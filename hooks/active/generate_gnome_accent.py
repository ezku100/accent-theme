#!/usr/bin/env python3
"""
Sincroniza la clave GNOME `org.gnome.desktop.interface accent-color`
con el Accent Color de KDE.

Por qué existe: apps como Materialgram ("Color de realce del sistema")
no leen el portal de KDE sino esta clave GNOME. Y el flatpak de
Materialgram tiene su PROPIA copia dconf (no ve la del host), así que
hay que escribir en ambos lados:
  1. host (gsettings normal) -> apps GTK/libadwaita nativas
  2. sandbox del flatpak -> Materialgram

Limitación honesta: GNOME solo admite 9 nombres fijos
(blue, teal, green, yellow, orange, red, pink, purple, slate), así que
se mapea al tono más cercano por matiz. Si el accent es casi gris,
se usa 'slate'. Solo escribe cuando el valor cambia.

Para volver al default: gsettings set org.gnome.desktop.interface accent-color 'blue'
(y quitar este generador de watch_accent.sh si no querés seguimiento).
"""
import colorsys
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge import get_accent_rgb

SCHEMA = "org.gnome.desktop.interface"
KEY = "accent-color"
MATERIALGRAM_APP = "io.github.kukuruzka165.materialgram"

# Matiz aproximado (grados) de cada accent GNOME fijo.
ACCENT_HUES = {
    "blue": 214,
    "teal": 192,
    "green": 127,
    "yellow": 43,
    "orange": 22,
    "red": 352,
    "pink": 330,
    "purple": 286,
}


def nearest_accent(h_deg, s):
    if s < 0.15:
        return "slate"
    best, best_dist = None, 1e9
    for name, hue in ACCENT_HUES.items():
        d = abs((h_deg - hue + 180) % 360 - 180)
        if d < best_dist:
            best, best_dist = name, d
    return best


def gsettings_get():
    try:
        out = subprocess.run(
            ["gsettings", "get", SCHEMA, KEY],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip().strip("'")
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    return None


def gsettings_set_host(value):
    subprocess.run(["gsettings", "set", SCHEMA, KEY, value],
                   check=False, timeout=5)


def sandbox_get():
    try:
        out = subprocess.run(
            ["flatpak", "run", f"--command=gsettings", MATERIALGRAM_APP,
             "get", SCHEMA, KEY],
            capture_output=True, text=True, timeout=30,
        )
        if out.returncode == 0:
            return out.stdout.strip().strip("'")
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    return None


def sandbox_set(value):
    subprocess.run(
        ["flatpak", "run", f"--command=gsettings", MATERIALGRAM_APP,
         "set", SCHEMA, KEY, value],
        check=False, timeout=30,
    )


def materialgram_installed():
    try:
        out = subprocess.run(["flatpak", "list", "--app", "--columns=application"],
                             capture_output=True, text=True, timeout=10)
        return MATERIALGRAM_APP in out.stdout
    except (FileNotFoundError, subprocess.SubprocessError):
        return False


def main():
    _mh = os.environ.get("MATUGEN_ACCENT", "").lstrip("#")
    if len(_mh) == 6:
        try:
            r, g, b = (int(_mh[i:i + 2], 16) / 255 for i in (0, 2, 4))
        except ValueError:
            r, g, b = get_accent_rgb()
    else:
        r, g, b = get_accent_rgb()
    h, s, _ = colorsys.rgb_to_hsv(r, g, b)
    want = nearest_accent(h * 360, s)

    if shutil.which("gsettings"):
        cur = gsettings_get()
        if cur != want:
            gsettings_set_host(want)
            print(f"GNOME host: {cur} -> {want}")
        else:
            print(f"GNOME host: ya estaba en {want}")
    else:
        print("gsettings no encontrado, salto host.")

    if materialgram_installed():
        cur = sandbox_get()
        if cur != want:
            sandbox_set(want)
            print(f"Materialgram sandbox: {cur} -> {want}")
        else:
            print(f"Materialgram sandbox: ya estaba en {want}")
    else:
        print("Materialgram no instalado, salto sandbox.")


if __name__ == "__main__":
    main()
