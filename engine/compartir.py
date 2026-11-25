"""Compartir: vista previa al pegar el enlace (WhatsApp, redes) y fuente RSS de los informes semanales.

- og.png: imagen de 1200x630 con el índice y el estado del día. Necesita Pillow; si no está instalado,
  el Pulso se publica igual, sin imagen (el núcleo del sistema solo usa la biblioteca estándar).
- metas Open Graph: título y descripción del día, que pulso.guardar inserta en la página.
- informes.xml: RSS 2.0 con los informes verificados (los no verificados no se publican).
"""
from __future__ import annotations

import html
import os
from datetime import datetime, timezone
from email.utils import format_datetime

from engine.motor import es, fe
from pipeline.store import RAIZ

URL_SITIO = "https://alejandrosczpf.github.io/economista-boliviano/"
SITIO = os.path.join(RAIZ, "site")
COLORES = {"calma": (12, 163, 12), "vigilancia": (250, 178, 25), "alerta": (208, 59, 59)}
FUENTES = {  # (normal, negrita): Linux (GitHub Actions) y Windows
    "linux": ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    "windows": (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
}


def metas(pul: dict) -> dict:
    """Título y descripción para la vista previa al compartir el enlace."""
    titulo = (f"Pulso · Economista Boliviano: índice {es(pul['indice'], 0)}/100, {pul['estado']} "
              f"({fe(pul['generado'])})")
    desc = (pul.get("resumen") or [""])[0]
    if len(desc) > 200:
        desc = desc[:197].rsplit(" ", 1)[0] + "…"
    return {"titulo": titulo, "descripcion": desc,
            "imagen": f"{URL_SITIO}og.png?v={pul['generado']}", "url": URL_SITIO}


def _fuente(tamano: int, negrita: bool = False):
    from PIL import ImageFont
    for normal, bold in FUENTES.values():
        ruta = bold if negrita else normal
        if os.path.exists(ruta):
            return ImageFont.truetype(ruta, tamano)
    return ImageFont.load_default(size=tamano)


def imagen_og(pul: dict, ruta: str | None = None) -> bool:
    """Dibuja og.png. Devuelve False (sin error) si Pillow no está disponible."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("  og.png: Pillow no está instalado; el Pulso se publica sin imagen de vista previa")
        return False
    ruta = ruta or os.path.join(SITIO, "og.png")
    W, H = 1200, 630
    fondo, tinta, suave = (244, 243, 239), (11, 11, 11), (82, 81, 78)
    color = COLORES[pul["estado"]]
    im = Image.new("RGB", (W, H), fondo)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 14], fill=color)
    d.text((70, 60), "PULSO · ECONOMISTA BOLIVIANO", font=_fuente(34, True), fill=suave)
    d.text((70, 108), f"Índice de riesgo macro · {fe(pul['generado'])}", font=_fuente(30), fill=suave)
    d.text((64, 165), es(pul["indice"], 0), font=_fuente(220, True), fill=tinta)
    ancho_num = d.textlength(es(pul["indice"], 0), font=_fuente(220, True))
    d.text((80 + ancho_num, 330), "/100", font=_fuente(56), fill=suave)
    # estado: rótulo con su color (y la palabra: el color nunca va solo)
    d.rounded_rectangle([70, 430, 70 + 34, 464], radius=8, fill=color)
    d.text((122, 422), pul["estado"].capitalize(), font=_fuente(48, True), fill=tinta)
    # barra 0-100 con los umbrales
    x0, x1, y = 70, W - 70, 520
    for lo, hi, c in ((0, 35, "calma"), (35, 60, "vigilancia"), (60, 100, "alerta")):
        d.rectangle([x0 + (x1 - x0) * lo / 100, y, x0 + (x1 - x0) * hi / 100, y + 18], fill=COLORES[c])
    xm = x0 + (x1 - x0) * min(pul["indice"], 100) / 100
    d.rectangle([xm - 3, y - 12, xm + 3, y + 30], fill=tinta)
    for v in (0, 35, 60, 100):
        d.text((x0 + (x1 - x0) * v / 100 - 10, y + 32), str(v), font=_fuente(24), fill=suave)
    im.save(ruta, "PNG", optimize=True)
    return True


def rss(informes: list[dict], ruta: str | None = None) -> str:
    """RSS 2.0 con los informes verificados, del más nuevo al más viejo."""
    ruta = ruta or os.path.join(SITIO, "informes.xml")
    items = []
    for inf in informes:
        if not inf["ok"]:
            continue
        fecha = datetime.fromisoformat(inf["fecha"]).replace(hour=14, tzinfo=timezone.utc)
        enlace = f"{URL_SITIO}archivo.html#informe-{inf['fecha']}"
        items.append(f"""  <item>
    <title>Informe semanal del {html.escape(fe(inf['fecha']))}</title>
    <link>{enlace}</link>
    <guid isPermaLink="true">{enlace}</guid>
    <pubDate>{format_datetime(fecha)}</pubDate>
    <description>{html.escape(inf['html'])}</description>
  </item>""")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Pulso · Economista Boliviano: informes semanales</title>
  <link>{URL_SITIO}</link>
  <description>Informe semanal sobre el riesgo macroeconómico de Bolivia. Cada cifra fue verificada contra los datos del día.</description>
  <language>es-BO</language>
{chr(10).join(items)}
</channel>
</rss>
"""
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(xml)
    return xml
