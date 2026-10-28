#!/usr/bin/env python3
"""
Puente matugen -> Noctalia: convierte la paleta Material que genera matugen
(desde el AccentColor de KDE) al formato de paleta personalizada de
Noctalia v5 (palettes/Matugen.json) y reinicia Noctalia para aplicarla.

Funciona de dos formas:
- Como hook de accent_to_matugen.py (usa MATUGEN_* del entorno).
- Solo: lee el AccentColor de KDE y corre matugen el mismo.
"""
import colorsys
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge import get_accent_rgb, hsv_to_hex, build_palette

MATUGEN = (os.environ.get("MATUGEN") or shutil.which("matugen")
           or os.path.expanduser("~/.local/bin/matugen"))
PALETTE_NAME = "Matugen"
PACMAN_ASSETS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "support",
    "generate_pacman_assets.py",
)
PALETTE_DIRS = [
    os.path.expanduser("~/.config/noctalia/palettes"),
    os.path.expanduser("~/.local/state/noctalia/palettes"),
]


def matugen_tokens(accent):
    """Corre matugen y devuelve dict token Material -> hex (modo dark).

    Usa un config propio y vacío: sin `-c`, matugen lee
    ``~/.config/matugen/config.toml`` y re-renderiza todos los templates
    globales (incluido colors.json de Caparazón), duplicando el trabajo del
    motor accent-theme y reescribiendo la paleta de forma no atómica.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as handle:
        handle.write("[config]\nversion_check = false\ncaching = false\n")
        config_path = handle.name
    try:
        proc = subprocess.run(
            [MATUGEN, "color", "hex", accent, "-c", config_path,
             "-t", "scheme-fidelity", "-m", "dark", "-j", "hex"],
            capture_output=True, text=True, timeout=60,
        )
    finally:
        os.unlink(config_path)
    if proc.returncode != 0:
        raise RuntimeError(f"matugen falló: {proc.stderr.strip()[:200]}")
    colors = json.loads(proc.stdout).get("colors", {})

    def g(key, fb):
        try:
            return colors[key]["dark"]["color"]
        except (KeyError, TypeError):
            return fb

    return g


def build_noctalia(g, accent, h, s, v):
    """Mapea tokens Material -> roles m* de Noctalia (variante dark)."""
    on_surface = g("on_surface", "#f1dede")
    surface = g("surface", "#141218")
    primary = g("primary", accent)
    on_primary = g("on_primary", "#141218")
    secondary_container = g("secondary_container", primary)
    on_secondary_container = g("on_secondary_container", on_surface)
    dark = {
        "mPrimary": primary,
        "mOnPrimary": on_primary,
        "mSecondary": g("secondary", primary),
        "mOnSecondary": g("on_secondary", on_surface),
        "mTertiary": g("tertiary", primary),
        "mOnTertiary": g("on_tertiary", on_surface),
        "mError": g("error", "#f2b8b5"),
        "mOnError": g("on_error", "#601410"),
        "mSurface": surface,
        "mOnSurface": on_surface,
        "mSurfaceVariant": g("surface_variant",
                             g("surface_container_highest", surface)),
        "mOnSurfaceVariant": g("on_surface_variant", on_surface),
        "mOutline": g("outline", "#938f99"),
        "mShadow": g("shadow", "#000000"),
        "mHover": secondary_container,
        "mOnHover": on_secondary_container,
    }
    ansi = build_palette(h, s, v)
    names = ["black", "red", "green", "yellow",
             "blue", "magenta", "cyan", "white"]
    dark["terminal"] = {
        "background": surface,
        "foreground": on_surface,
        "cursor": primary,
        "cursorText": on_primary,
        "selectionBg": secondary_container,
        "selectionFg": on_secondary_container,
        "normal": {n: ansi[i] for i, n in enumerate(names)},
        "bright": {n: ansi[i + 8] for i, n in enumerate(names)},
    }
    return {"dark": dark}


def main():
    if not os.access(MATUGEN, os.X_OK):
        print("noctalia: matugen no encontrado, salto.")
        return
    if not (shutil.which("noctalia") or os.path.isdir(os.path.expanduser("~/.config/noctalia"))):
        print("noctalia: no instalado, salto.")
        return
    env = os.environ
    accent = env.get("MATUGEN_ACCENT")
    if accent:
        # Viene de accent_to_matugen.py: reconstruye tokens con matugen
        # para tener el set Material completo, no solo los 8 del hook.
        r, g, b = get_accent_rgb()
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        tokens = matugen_tokens(accent)
    else:
        r, g, b = get_accent_rgb()
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        accent = hsv_to_hex(h, s, v)
        tokens = matugen_tokens(accent)

    payload = build_noctalia(tokens, accent, h, s, v)
    ref = os.path.join(PALETTE_DIRS[0], PALETTE_NAME + ".json")
    try:
        with open(ref) as f:
            same = json.load(f) == payload
    except (OSError, ValueError):
        same = False
    if same:
        print(f"noctalia: paleta {accent} sin cambios, no se toca nada.")
        return
    for d in PALETTE_DIRS:
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, PALETTE_NAME + ".json"), "w") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")
        print(f"noctalia: paleta {accent} -> {d}/{PALETTE_NAME}.json")

    try:
        refresh_pacman(accent)
    except Exception as e:
        print(f"pacman: no se pudo regenerar: {e}")

    # Aplicación en vivo por IPC: sin reiniciar.
    # No reiniciar nunca desde aquí: los procesos nacidos bajo el servicio
    # kitty-theme-watch quedan fuera de la sesión logind y Noctalia arranca
    # con workspace backend=none (dock sin ventanas activas). La instancia
    # del autostart sí tiene sesión; solo se le pide recargar la paleta.
    was_running = subprocess.run(
        ["pgrep", "-x", "noctalia"],
        capture_output=True).returncode == 0
    if was_running:
        live_reload()
    else:
        print("noctalia: no corre; lo inicia el autostart en el login.")


def refresh_pacman(accent):
    proc = subprocess.run(
        [sys.executable, PACMAN_ASSETS, accent],
        capture_output=True, text=True, timeout=120)
    out = (proc.stdout or "").strip().splitlines()
    print(out[-1] if out else "pacman: sin salida")
    # Sin touch ni reinicio: el widget lee assets_v del demonio y las rutas
    # nuevas invalidan la caché de imágenes solas en el siguiente tick.


def live_reload():
    r = subprocess.run(["noctalia", "msg", "color-scheme-set",
                        "custom", PALETTE_NAME],
                       capture_output=True, text=True, timeout=30)
    if r.returncode == 0:
        print(f"noctalia: paleta {PALETTE_NAME} recargada en vivo.")
    else:
        print(f"noctalia: color-scheme-set falló: "
              f"{(r.stderr or '').strip()[:200]}")
        subprocess.run(["noctalia", "msg", "config-reload"],
                       capture_output=True, timeout=30)
        print("noctalia: config-reload enviado como respaldo.")


if __name__ == "__main__":
    main()
