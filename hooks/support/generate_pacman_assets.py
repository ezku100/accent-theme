#!/usr/bin/env python3
"""Genera los PNGs del widget pacman tintados al AccentColor de KDE.

Estilos: pacman (acento + fantasmas), zelda-triforce (trifuerza dorada +
rupias tintadas), minimal (círculos/anillos) y neon (halo). Lo llama
generate_noctalia_theme.py en cada cambio de acento.
"""
import colorsys
import importlib.util
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge import get_accent_rgb

D = os.path.expanduser("~/.local/share/noctalia/plugins/pacman-desktops/assets")
# Maestros dibujados fuera (ej. play.svg del usuario): se copian tal cual
# en cada version para que los cambios de acento no los borren.
_HERE = os.path.dirname(os.path.abspath(__file__))
S = 64
GHOST_OFFSETS = [-0.09, -0.035, 0.05, 0.11]
DIM_ALPHA = 95
EMPTY_ALPHA = 45


def hex_to_rgb(hx):
    hx = hx.lstrip("#")
    return tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4))


def draw_pacman(rgb, mouth_half):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    cx = cy = S / 2
    R = 26
    if mouth_half <= 0:
        dr.ellipse([cx - R, cy - R, cx + R, cy + R], fill=rgb + (255,))
    else:
        pts = [(cx, cy)]
        for a in range(mouth_half, 360 - mouth_half + 1, 2):
            r = math.radians(a)
            pts.append((cx + R * math.cos(r), cy - R * math.sin(r)))
        dr.polygon(pts, fill=rgb + (255,))
    return img


def save_atomic(img, path):
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            img.save(f, format="PNG")
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def copy_master(name, path):
    """Copia un PNG maestro a path. Todo vive dentro del plugin:
    junto al script (install.sh) o en su carpeta instalada."""
    import shutil
    import tempfile
    cands = [os.path.join(_HERE, name),
             os.path.join(os.path.expanduser(
                 "~/.local/share/noctalia/plugins/pacman-desktops/assets_src"), name)]
    for cand in cands:
        if not os.path.exists(cand):
            continue
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
        try:
            os.close(fd)
            shutil.copyfile(cand, tmp)
            os.replace(tmp, path)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        return True
    return False


def draw_pellet(rgb):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    cx = cy = S / 2
    R = 7
    dr.ellipse([cx - R, cy - R, cx + R, cy + R], fill=rgb + (255,))
    return img


def draw_ghost(rgb, alpha=255):
    from PIL import Image, ImageDraw
    body = rgb + (alpha,)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    x0, x1, top, bot = 14, 50, 10, 54
    dr.pieslice([x0, top, x1, top + 36], 180, 360, fill=body)
    hem = bot - 10
    dr.rectangle([x0, top + 18, x1, hem], fill=body)
    # Bajo en zigzag: dientes hacia abajo.
    teeth, tw = 4, (x1 - x0) / 4
    for i in range(teeth):
        xa = x0 + i * tw
        dr.polygon([(xa, hem), (xa + tw / 2, bot), (xa + tw, hem)], fill=body)
    ea = max(60, alpha)
    for ex in (24, 40):
        dr.ellipse([ex - 5, 24, ex + 5, 36], fill=(255, 255, 255, ea))
        dr.ellipse([ex - 2, 28, ex + 3, 35], fill=(30, 30, 160, ea))
    return img


def draw_triforce(rgb=(255, 205, 0)):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    # Trifuerza real: 3 triangulos que forman uno grande, con el
    # central invertido vacio (se ve el fondo).
    cx, top, w, hh = S / 2, 8, 14, 24
    dr.polygon([(cx, top), (cx - w, top + hh), (cx + w, top + hh)],
               fill=rgb + (255,))
    dr.polygon([(cx - w, top + hh), (cx - 2 * w, top + 2 * hh), (cx, top + 2 * hh)],
               fill=rgb + (255,))
    dr.polygon([(cx + w, top + hh), (cx, top + 2 * hh), (cx + 2 * w, top + 2 * hh)],
               fill=rgb + (255,))
    # Brillo superior.
    dr.line([(cx - w + 3, top + hh - 2), (cx + w - 3, top + hh - 2)],
            fill=(255, 245, 200, 220), width=2)
    return img


def draw_triangle(rgb, alpha=255):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    # Pieza de trifuerza teñida al acento, apuntando arriba.
    cx = S / 2
    dr.polygon([(cx, 10), (cx - 20, 46), (cx + 20, 46)], fill=rgb + (alpha,))
    # Brillo lateral.
    dr.line([(cx - 13, 40), (cx + 13, 40)],
            fill=(255, 245, 200, min(alpha, 220)), width=2)
    return img


def draw_heart_empty(rgb):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    # Contenedor vacio estilo Minecraft: solo el borde tenido oscuro,
    # dentro transparente.
    cell = 6
    ox, oy = (S - 9 * cell) // 2, (S - 8 * cell) // 2
    full = {(x, y) for y, row in enumerate(HEART) for x, ch in enumerate(row)
            if ch == "X"}
    for (x, y) in full:
        if ((x - 1, y) not in full or (x + 1, y) not in full
                or (x, y - 1) not in full or (x, y + 1) not in full):
            dr.rectangle([ox + x * cell, oy + y * cell,
                          ox + (x + 1) * cell - 1, oy + (y + 1) * cell - 1],
                         fill=rgb + (255,))
    return img


def draw_rupee(rgb):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    cx = S / 2
    dark = tuple(int(c * 0.3) for c in rgb)
    lite = tuple(min(255, int(c + (255 - c) * 0.55)) for c in rgb)
    mid = tuple(int(c * 0.78) for c in rgb)
    # Contorno oscuro para definir la gema.
    dr.polygon([(cx, 6), (cx + 15, 28), (cx, 58), (cx - 15, 28)], fill=dark + (255,))
    # Cuerpo base.
    dr.polygon([(cx, 9), (cx + 12, 28), (cx, 55), (cx - 12, 28)], fill=rgb + (255,))
    # Faceta izquierda (sombra) y derecha (luz).
    dr.polygon([(cx, 9), (cx, 55), (cx - 12, 28)], fill=mid + (255,))
    dr.polygon([(cx, 9), (cx + 12, 28), (cx + 5, 28), (cx, 12)], fill=lite + (255,))
    # Profundidad inferior (sutil para no ennegrecer).
    dr.polygon([(cx - 7, 35), (cx + 7, 35), (cx, 55)], fill=(0, 0, 0, 30))
    # Filo de luz en el bisel inferior derecho.
    dr.line([(cx + 12, 28), (cx, 55)], fill=lite + (255,), width=2)
    # Bisel brillante superior izquierdo.
    dr.line([(cx - 9, 26), (cx - 2, 12)], fill=(255, 255, 255, 200), width=2)
    # Destello estrella.
    dr.polygon([(cx + 3, 18), (cx + 5, 23), (cx + 10, 25), (cx + 5, 27),
                (cx + 3, 32), (cx + 1, 27), (cx - 4, 25), (cx + 1, 23)],
               fill=(255, 255, 255, 235))
    return img


def draw_circle(rgb, r=20, alpha=255):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    cx = cy = S / 2
    dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rgb + (alpha,))
    return img


def draw_play_logo_fallback(rgb):
    # Reserva por si el maestro SVG falta: P simple + S plana tenida.
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    W = (242, 242, 242, 255)
    dr.rectangle([28, 4, 35, 54], fill=W)
    dr.arc([28, 4, 60, 32], 270, 90, fill=W, width=7)
    dr.rectangle([28, 2, 44, 9], fill=W)
    dr.rectangle([28, 23, 44, 30], fill=W)
    dr.ellipse([10, 46, 54, 58], fill=rgb + (255,))
    return img


PS_GLYPHS = ("circle", "cross", "square", "triangle")


def draw_ps_glyph(kind, rgb, alpha=255):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    deep = tuple(int(c * 0.3) for c in rgb) + (alpha,)

    def paint(ink, dx, dy):
        if kind == "circle":
            dr.ellipse([16 + dx, 16 + dy, 48 + dx, 48 + dy], outline=ink, width=7)
        elif kind == "cross":
            dr.line([(20 + dx, 20 + dy), (44 + dx, 44 + dy)], fill=ink, width=7)
            dr.line([(44 + dx, 20 + dy), (20 + dx, 44 + dy)], fill=ink, width=7)
        elif kind == "square":
            dr.rectangle([17 + dx, 17 + dy, 47 + dx, 47 + dy], outline=ink, width=7)
        else:
            cx = S / 2
            dr.line([(cx + dx, 14 + dy), (cx + 17 + dx, 44 + dy),
                     (cx - 17 + dx, 44 + dy), (cx + dx, 14 + dy)],
                    fill=ink, width=7, joint="curve")

    # Relieve 3D: extrusion oscura atras + cara principal + filo de luz.
    paint(deep, 2, 3)
    paint(rgb + (alpha,), 0, 0)
    hi = (255, 255, 255, min(alpha, 200))
    if kind == "circle":
        dr.arc([19, 19, 45, 45], 180, 250, fill=hi, width=3)
    elif kind == "cross":
        dr.line([(23, 23), (30, 30)], fill=hi, width=3)
    elif kind == "square":
        dr.line([(17, 17), (17, 28)], fill=hi, width=3)
        dr.line([(17, 17), (28, 17)], fill=hi, width=3)
    else:
        dr.line([(26, 22), (32, 14)], fill=hi, width=3)
    return img


def draw_pikachu():
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    Y, B = (255, 213, 0, 255), (30, 30, 30, 255)
    # Orejas amarillas con punta negra.
    dr.polygon([(13, 22), (4, 2), (25, 12)], fill=Y)
    dr.polygon([(51, 22), (60, 2), (39, 12)], fill=Y)
    dr.polygon([(4, 2), (9, 4), (14, 3), (11, 10)], fill=B)
    dr.polygon([(60, 2), (55, 4), (50, 3), (53, 10)], fill=B)
    # Cara redonda.
    dr.ellipse([10, 14, 54, 58], fill=Y)
    # Ojos con brillo.
    for ex in (22, 42):
        dr.ellipse([ex - 4, 28, ex + 4, 38], fill=B)
        dr.ellipse([ex - 1, 29, ex + 2, 33], fill=(255, 255, 255, 255))
    # Mejillas rojas.
    for mx in (14, 50):
        dr.ellipse([mx - 6, 38, mx + 6, 48], fill=(230, 30, 30, 255))
    # Nariz y boca.
    dr.ellipse([31, 40, 33, 42], fill=B)
    dr.arc([27, 41, 32, 47], 300, 60, fill=B, width=2)
    dr.arc([32, 41, 37, 47], 120, 240, fill=B, width=2)
    return img


def draw_pokeball(rgb, alpha=255):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    box = [8, 8, 56, 56]
    dark = (35, 35, 35, alpha)
    # Base blanca + mitad superior tenida.
    dr.ellipse(box, fill=(240, 240, 240, alpha))
    dr.pieslice(box, 180, 360, fill=rgb + (alpha,))
    # Banda central + boton.
    dr.rectangle([8, 28, 56, 36], fill=dark)
    dr.ellipse([25, 25, 39, 39], fill=(240, 240, 240, alpha))
    dr.ellipse([25, 25, 39, 39], outline=dark, width=2)
    dr.ellipse([29, 29, 35, 35], fill=dark)
    # Brillo superior izquierdo.
    dr.arc([14, 12, 30, 28], 180, 270, fill=(255, 255, 255, min(alpha, 220)), width=3)
    # Contorno.
    dr.ellipse(box, outline=dark, width=2)
    return img


def draw_ring(rgb, r=17, w=6, alpha=255):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    cx = cy = S / 2
    dr.ellipse([cx - r, cy - r, cx + r, cy + r],
               outline=rgb + (alpha,), width=w)
    return img


CREEPER_FACE = [
    "........",
    ".XX..XX.",
    ".XX..XX.",
    "...XX...",
    "..XXXX..",
    "..XXXX..",
    "..X..X..",
    "........",
]

HEART = [
    ".XX...XX.",
    "XXXXXXXXX",
    "XXXXXXXXX",
    "XXXXXXXXX",
    ".XXXXXXX.",
    "..XXXXX..",
    "...XXX...",
    "....X....",
]


def _paint_grid(dr, grid, ox, oy, cell, fill):
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch == "X":
                dr.rectangle([ox + x * cell, oy + y * cell,
                              ox + (x + 1) * cell - 1, oy + (y + 1) * cell - 1],
                             fill=fill)


def draw_creeper():
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    # Cabeza cuadrada verde con motas oscuras (textura).
    dr.rectangle([6, 6, S - 7, S - 7], fill=(88, 175, 74, 255))
    for i in range(6, S - 6, 4):
        for j in range(6, S - 6, 4):
            if (i * 7 + j * 13) % 5 == 0:
                dr.rectangle([i, j, i + 1, j + 1], fill=(62, 140, 52, 255))
    # Cara pixel art 8x8 escalada al centro.
    cell = 6
    _paint_grid(dr, CREEPER_FACE, (S - 8 * cell) // 2, (S - 8 * cell) // 2,
                cell, (20, 20, 20, 255))
    return img


def draw_heart(rgb, alpha=255):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    # Corazon pixel art 9x8 tenido al acento, con brillo y sombra derivados.
    hi = tuple(min(255, int(c + (255 - c) * 0.55)) for c in rgb)
    lo = tuple(int(c * 0.6) for c in rgb)
    cell = 6
    ox, oy = (S - 9 * cell) // 2, (S - 8 * cell) // 2
    _paint_grid(dr, HEART, ox, oy, cell, rgb + (alpha,))
    dr.rectangle([ox + cell, oy, ox + 2 * cell - 1, oy + cell - 1],
                 fill=hi + (alpha,))
    for y in (5, 6, 7):
        for x, ch in enumerate(HEART[y]):
            if ch == "X":
                dr.rectangle([ox + x * cell, oy + y * cell,
                              ox + (x + 1) * cell - 1, oy + (y + 1) * cell - 1],
                             fill=lo + (alpha,))
    return img


def draw_neon(base, halo_alpha=70):
    from PIL import Image, ImageChops
    halo = base.copy()
    # Halo: duplica el alfa tenue debajo (sin blur para no meter scipy).
    px = halo.load()
    for y in range(S):
        for x in range(S):
            rr, gg, bb, aa = px[x, y]
            if aa:
                px[x, y] = (rr, gg, bb, halo_alpha)
    halo = halo.resize((S, S))
    return Image.alpha_composite(halo, base)


def pillow_available():
    return importlib.util.find_spec("PIL") is not None


def main(accent=None):
    if not pillow_available():
        print("pacman: Pillow no disponible; se omite la regeneracion de assets.")
        return
    if accent:
        r, g, b = (int(accent.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    else:
        r, g, b = get_accent_rgb()
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    acc = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v))
    cur = current_version()
    nxt = cur + 1
    out = os.path.join(D, f"v{nxt}")
    os.makedirs(out, exist_ok=True)
    PAC_YELLOW = (255, 225, 0)
    save_atomic(draw_pacman(PAC_YELLOW, 32), f"{out}/pacman_open.png")
    save_atomic(draw_pacman(PAC_YELLOW, 10), f"{out}/pacman_closed.png")
    for i, off in enumerate(GHOST_OFFSETS):
        gh = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(
            (h + off) % 1.0, max(0.45, s), min(1.0, v + 0.05)))
        save_atomic(draw_ghost(gh), f"{out}/ghost_{i}.png")
        save_atomic(draw_ghost(gh, DIM_ALPHA), f"{out}/ghost_{i}_dim.png")
    pellet = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(h, min(s, 0.25), 0.85))
    save_atomic(draw_pellet(pellet), f"{out}/pellet.png")
    # Zelda: trifuerza dorada (activo) + 4 rupias tenidas al acento
    # (inactivos ocupados) y 4 triangulos tenues (inactivos vacios).
    save_atomic(draw_triforce(), f"{out}/triforce.png")
    for i, off in enumerate(GHOST_OFFSETS):
        tr = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(
            (h + off) % 1.0, min(1.0, max(0.55, s)), min(1.0, v + 0.08)))
        save_atomic(draw_rupee(tr), f"{out}/rupee_{i}.png")
        save_atomic(draw_triangle(tr, EMPTY_ALPHA), f"{out}/triangle_{i}_dim.png")
    # Minecraft: cabeza de creeper (activo) + 4 corazones tenidos al
    # acento (inactivos ocupados) y contenedor vacio tenido oscuro
    # (inactivos vacios).
    save_atomic(draw_creeper(), f"{out}/creeper.png")
    for i, off in enumerate(GHOST_OFFSETS):
        hr = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(
            (h + off) % 1.0, min(1.0, max(0.55, s)), min(1.0, v + 0.08)))
        save_atomic(draw_heart(hr), f"{out}/heart_{i}.png")
    dark = tuple(int(c * 0.4) for c in acc)
    save_atomic(draw_heart_empty(dark), f"{out}/heart_empty.png")
    # Pokemon: cara de pikachu (activo) + 4 pokebolas tenidas al
    # acento (inactivos ocupados) y sus tenues (inactivos vacios).
    save_atomic(draw_pikachu(), f"{out}/pikachu.png")
    for i, off in enumerate(GHOST_OFFSETS):
        pb = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(
            (h + off) % 1.0, min(1.0, max(0.55, s)), min(1.0, v + 0.08)))
        save_atomic(draw_pokeball(pb), f"{out}/pokeball_{i}.png")
        save_atomic(draw_pokeball(pb, EMPTY_ALPHA), f"{out}/pokeball_{i}_dim.png")
    # PlayStation: logo (activo) + 4 simbolos tenidos al acento
    # (inactivos ocupados) y sus tenues (inactivos vacios).
    # PlayStation: logo maestro del usuario (SVG rasterizado) o reserva.
    if not copy_master("play_logo.png", f"{out}/play_logo.png"):
        save_atomic(draw_play_logo_fallback(acc), f"{out}/play_logo.png")
    for i, (off, kind) in enumerate(zip(GHOST_OFFSETS, PS_GLYPHS)):
        ps = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(
            (h + off) % 1.0, min(1.0, max(0.55, s)), min(1.0, v + 0.08)))
        save_atomic(draw_ps_glyph(kind, ps), f"{out}/ps_{kind}.png")
        save_atomic(draw_ps_glyph(kind, ps, EMPTY_ALPHA), f"{out}/ps_{kind}_dim.png")
    # Minimal: formas geometricas tintadas.
    save_atomic(draw_circle(acc, 20), f"{out}/minimal_active.png")
    save_atomic(draw_ring(acc, 17, 6), f"{out}/minimal_busy.png")
    save_atomic(draw_circle(pellet, 6), f"{out}/minimal_empty.png")
    # Neon: mismos moldes pacman con halo + colores a tope.
    neon_acc = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(h, 1.0, 1.0))
    save_atomic(draw_neon(draw_pacman(neon_acc, 32)), f"{out}/neon_open.png")
    save_atomic(draw_neon(draw_pacman(neon_acc, 10)), f"{out}/neon_closed.png")
    for i, off in enumerate(GHOST_OFFSETS):
        ng = tuple(int(x * 255) for x in colorsys.hsv_to_rgb((h + off) % 1.0, 1.0, 1.0))
        save_atomic(draw_neon(draw_ghost(ng)), f"{out}/neon_ghost_{i}.png")
    save_atomic(draw_neon(draw_pellet(neon_acc)), f"{out}/neon_dot.png")
    prune(nxt)
    ah = f"#{acc[0]:02x}{acc[1]:02x}{acc[2]:02x}"
    print(f"pacman: PNGs v{nxt} en {ah} (pacman x2 + fantasmas x8 + zelda x9 + minecraft x6 + pokemon x9 + play x9 + minimal x3 + neon x7).")


def current_version():
    best = 0
    try:
        for name in os.listdir(D):
            if name.startswith("v") and name[1:].isdigit():
                best = max(best, int(name[1:]))
    except OSError:
        pass
    return best


def prune(keep_newest, keep=2):
    try:
        versions = sorted(int(n[1:]) for n in os.listdir(D)
                          if n.startswith("v") and n[1:].isdigit())
    except OSError:
        return
    for v in versions:
        if v <= keep_newest - keep:
            import shutil
            shutil.rmtree(os.path.join(D, f"v{v}"), ignore_errors=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
