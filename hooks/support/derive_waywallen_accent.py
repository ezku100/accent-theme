#!/usr/bin/env python3
"""
Deriva el AccentColor de KDE desde el fondo actual de Waywallen y lo fija
en kdeglobals. Existe porque Plasma solo deriva el accent de wallpapers
org.kde.image; con el plugin de Waywallen nunca lo actualiza y la cadena
fondo -> accent -> feeder -> Caelestia se rompe (termina en esquema claro).

Lee last_wallpaper de config.toml, resuelve el archivo (imagen directa o
preview de escena/video vía la DB sqlite) y muestrea el tono dominante
ponderado por saturación. Solo escribe si cambió. Lo invoca watch_accent.sh
cuando cambia el config de Waywallen; el cambio en kdeglobals dispara
después el flujo normal.
"""
import colorsys
import math
import os
import sqlite3
import subprocess
import sys

WAY_CONF = os.path.expanduser(
    "~/.var/app/org.waywallen.waywallen/config/waywallen/config.toml")
WAY_DB = os.path.expanduser(
    "~/.var/app/org.waywallen.waywallen/data/waywallen/waywallen-v2.db")
STEAM_ROOTS = [
    os.path.expanduser("~/.local/share/Steam"),
    os.path.expanduser("~/.steam/steam"),
    "/mnt/cc24f266-1b16-4e57-9a3d-a829c387f940/SteamLibrary",
]


def _toml_last(path):
    """Lee last_wallpaper global (tomllib si existe, si no parseo mínimo)."""
    try:
        import tomllib
        with open(path, "rb") as f:
            data = tomllib.load(f)
        last = (data.get("global") or {}).get("last_wallpaper")
        if last:
            return str(last)
    except (OSError, ImportError):
        pass
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            in_global, depth = False, 0
            for line in f:
                s = line.strip()
                if s.startswith("["):
                    in_global = (s == "[global]")
                    continue
                if in_global and s.startswith("last_wallpaper"):
                    return s.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return None


def _resolve(item_id):
    """Devuelve (ruta_imagen) para el wallpaper actual."""
    try:
        db = sqlite3.connect("file:%s?mode=ro" % WAY_DB, uri=True)
        row = db.execute(
            "SELECT path, preview_path, type FROM item WHERE id=?",
            (item_id,)).fetchone()
        db.close()
    except sqlite3.Error:
        return None
    if not row:
        return None
    path, preview, wtype = row
    candidates = []
    if wtype in ("image", "picture") or (path or "").lower().endswith(
            (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")):
        candidates.append(path)
    if preview:
        candidates.append(preview)
    candidates.append(path)
    for rel in candidates:
        if not rel:
            continue
        if os.path.isabs(rel) and os.path.isfile(rel):
            return rel
        for root in STEAM_ROOTS:
            for base in ("steamapps/workshop/content/431960",
                         "steamapps/workshop/content",
                         "steamapps/common/wallpaper_engine/projects"):
                full = os.path.join(root, base, rel)
                if os.path.isfile(full):
                    return full
            full = os.path.join(root, rel)
            if os.path.isfile(full):
                return full
    return None


def _sample_accent(image_path):
    """Tono dominante ponderado por saturación; devuelve hex sin #."""
    from PIL import Image
    with Image.open(image_path) as im:
        im = im.convert("RGB").resize((48, 48))
        w, h = im.size
        px = [im.getpixel((x, y)) for y in range(h) for x in range(w)]
    sx = sy = sw = 0.0
    rs = gs = bs = 0.0
    for p in px:
        if not isinstance(p, (tuple, list)) or len(p) < 3:
            continue
        r, g, b = float(p[0]) / 255, float(p[1]) / 255, float(p[2]) / 255
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        w = s * (0.3 + 0.7 * v)
        sx += math.cos(h * 2 * math.pi) * w
        sy += math.sin(h * 2 * math.pi) * w
        sw += w
        rs += r
        gs += g
        bs += b
    if sw <= 0:
        return None
    n = float(len(px))
    hue = (math.atan2(sy / sw, sx / sw) / (2 * math.pi)) % 1.0
    _, s_mean, _ = colorsys.rgb_to_hsv(rs / n, gs / n, bs / n)
    sat = max(0.45, min(0.9, s_mean))
    r, g, b = colorsys.hsv_to_rgb(hue, sat, 0.75)
    return "%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def _current_accent():
    proc = subprocess.run(
        ["kreadconfig6", "--file", "kdeglobals", "--group", "General",
         "--key", "AccentColor"],
        capture_output=True, text=True, timeout=10)
    v = (proc.stdout or "").strip()
    parts = v.split(",")
    if len(parts) == 3:
        try:
            return "%02x%02x%02x" % tuple(int(p) for p in parts)
        except ValueError:
            pass
    return None


def main():
    # Solo rellena el hueco: si ya hay accent (manual o derivado por
    # Plasma) se respeta y no se toca nada.
    if _current_accent() is not None:
        print("waywallen-accent: ya hay accent, se respeta.")
        return 0
    item_id = _toml_last(WAY_CONF)
    if not item_id:
        print("waywallen-accent: sin last_wallpaper.")
        return 0
    image = _resolve(item_id)
    if not image:
        print(f"waywallen-accent: no resolví archivo para id {item_id}.")
        return 0
    try:
        accent = _sample_accent(image)
    except Exception as e:
        print(f"waywallen-accent: no pude muestrear {image}: {e}")
        return 0
    if not accent:
        return 0
    if _current_accent() == accent:
        print(f"waywallen-accent: ya estaba en {accent}.")
        return 0
    r, g, b = (int(accent[i:i + 2], 16) for i in (0, 2, 4))
    proc = subprocess.run(
        ["kwriteconfig6", "--file", "kdeglobals", "--group", "General",
         "--key", "AccentColor", f"{r},{g},{b}"],
        capture_output=True, text=True, timeout=10)
    if proc.returncode != 0:
        print("waywallen-accent: kwriteconfig6 falló.")
        return 1
    print(f"waywallen-accent: accent -> {accent} desde {os.path.basename(image)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
