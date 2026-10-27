#!/usr/bin/env python3
"""
Genera el tema `Dinamico.obt` para OBS Studio a partir del Accent de KDE.

Formato OBS 30+: el tema es un `.obt` (texto) con bloques
`@OBSThemeMeta` (name/id) + `@OBSThemeVars` (variables CSS) + QSS que
usa `var(--...)`. Un `.qss` pelado NO aparece en la lista — por eso el
intento anterior no funcionaba.

Estrategia: se usa el tema Venom instalado como base (QSS profesional
completo + iconos `Vm/`), y solo se sustituye la escala del accent
(`--orange1..5`, que alimenta a `--primary*` y de ahí a botones, tabs,
sliders, barras). Los grises/semánticos de Venom se conservan.

Salidas:
  ~/.var/app/com.obsproject.Studio/config/obs-studio/themes/Dinamico.obt
  (más ~/.config/obs-studio/themes/ si usás OBS nativo algún día)

Flujo: elegir "Dinamico" una vez en Ajustes -> Apariencia -> Tema
(requiere reiniciar OBS para que aparezca en la lista). Limitación de
OBS: no recarga el tema en vivo; tras cada cambio de accent, cambiar a
otro tema y volver a Dinamico (sin reiniciar) para aplicar.
"""
import colorsys
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge import get_accent_rgb, hsv_to_hex

BASE_OBT = os.path.expanduser(
    "~/.var/app/com.obsproject.Studio/config/obs-studio/themes/Venom.obt")
DESTINOS = [
    os.path.join(os.path.dirname(BASE_OBT), "Dinamico.obt"),
    os.path.expanduser("~/.config/obs-studio/themes/Dinamico.obt"),
]
# Restos del intento anterior (.qss sin meta): OBS no los lista, se eliminan
# para no confundir.
LEGACY_QSS = [
    os.path.join(os.path.dirname(BASE_OBT), "Dinamico.qss"),
    os.path.expanduser("~/.config/obs-studio/themes/Dinamico.qss"),
]


def accent_scale(h, s, v):
    o1 = hsv_to_hex(h, max(0.10, s - 0.25), min(1.0, v + 0.12))
    o2 = hsv_to_hex(h, max(0.10, s - 0.12), min(1.0, v + 0.06))
    o3 = hsv_to_hex(h, s, v)
    o4 = hsv_to_hex(h, min(1.0, s + 0.05), max(0.15, v - 0.15))
    o5 = hsv_to_hex(h, min(1.0, s + 0.08), max(0.10, v - 0.30))
    return o1, o2, o3, o4, o5


def main():
    if not os.path.exists(BASE_OBT):
        print(f"No se encontró la base {BASE_OBT}, no se genera nada.")
        return

    _mh = os.environ.get("MATUGEN_ACCENT", "").lstrip("#")
    if len(_mh) == 6:
        try:
            r, g, b = (int(_mh[i:i + 2], 16) / 255 for i in (0, 2, 4))
        except ValueError:
            r, g, b = get_accent_rgb()
    else:
        r, g, b = get_accent_rgb()
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    shades = accent_scale(h, s, v)

    with open(BASE_OBT, encoding="utf-8") as f:
        content = f.read()

    content = content.replace("name: 'Venom';", "name: 'Dinamico';", 1)
    content = content.replace("id: 'com.obsproject.Venom';",
                              "id: 'com.ezku.Dinamico';", 1)
    content = content.replace(
        "author: 'FM.VENOM';",
        "author: 'Dinamico (accent KDE, base Venom de FM.VENOM)';", 1)

    for i, shade in enumerate(shades, start=1):
        content, n = re.subn(rf"(--orange{i}:\s*)#[0-9a-fA-F]+",
                             rf"\g<1>{shade}", content)
        if not n:
            print(f"Aviso: no se encontró --orange{i} en la base.")

    # Naranjas hardcodeados en el cuerpo del QSS (el autor no los pasó por
    # variables): textos de menú, handles de sliders, bordes del mezclador,
    # radios y etiquetas dB. Los verdes/rojos/amarillos de los medidores
    # (VolumeMeter, #ff6b6b, stops #ffb74d) son semánticos y se conservan.
    literales = {
        "#ff7f50": "var(--primary)",
        "#ff955b": "var(--primary)",
        "#ffb08a": "var(--primary_lighter)",
        "#ffb26b": "var(--primary)",
        "#ffc49d": "var(--white1)",
        "#fffae5": "var(--white1)",
        "#ffb74d !important": "var(--white1) !important",
    }
    for old, new in literales.items():
        content = content.replace(old, new)

    wrote = False
    for dest in DESTINOS:
        if "flatpak" not in dest and not os.path.isdir(
                os.path.dirname(os.path.dirname(dest))):
            continue
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8", newline="") as f:
                f.write(content)
            print(f"OBS: tema escrito en {dest} (accent {shades[2]}).")
            wrote = True
        except OSError as e:
            print(f"OBS: no se pudo escribir {dest}: {e}")

    for legacy in LEGACY_QSS:
        try:
            if os.path.exists(legacy):
                os.remove(legacy)
                print(f"OBS: eliminado resto obsoleto {legacy}.")
        except OSError:
            pass

    if not wrote:
        print("OBS: ningún destino válido.")
        return

    notify_obs()


def notify_obs():
    """Aviso de escritorio (best-effort) si OBS está corriendo: como OBS
    no recarga el tema solo, esto evita tener que acordarse de alternar
    el tema. Nunca hace fallar el script. Para desactivar, borrar la
    llamada de arriba."""
    try:
        ps = subprocess.run(["pgrep", "-f", "com.obsproject.Studio"],
                            capture_output=True, timeout=5)
        if ps.returncode != 0:
            return  # OBS cerrado: nada que avisar
        if not shutil.which("notify-send"):
            return
        subprocess.run(
            ["notify-send", "-a", "Dinamico", "Tema OBS actualizado",
             "Pasá a otro tema y volvé a Dinamico para aplicar el accent."],
            check=False, timeout=5)
    except Exception:
        pass


if __name__ == "__main__":
    main()
