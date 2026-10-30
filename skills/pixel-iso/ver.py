"""Para **mirar** una escena: la amplía ×N con vecino más cercano (cada píxel, un cuadrado
limpio, sin suavizar) sobre un fondo oscuro, que lo transparente no se confunda con el
blanco del visor. Con dos PNG, las pone lado a lado (antes y después).

    python ver.py escena.png                    # deja escena_x3.png
    python ver.py antes.png despues.png         # deja antes_vs_despues_x3.png
    python ver.py escena.png -x 4 -o mira.png   # otra escala, otra salida
    python ver.py escena.png --recorte 100,40,260,160   # solo un trozo (x0,y0,x1,y1 en px de la original)

Imprime la ruta de lo que deja, para abrirla luego con la herramienta de leer imágenes.
"""
from __future__ import annotations

import argparse
import os
import sys

from PIL import Image

FONDO = (24, 24, 28, 255)
HUECO = 8                      # px (ya ampliados) entre las dos imágenes


def ampliar(ruta: str, escala: int, recorte=None) -> Image.Image:
    img = Image.open(ruta).convert("RGBA")
    if recorte:
        img = img.crop(recorte)
    fondo = Image.new("RGBA", img.size, FONDO)
    fondo.alpha_composite(img)
    return fondo.resize((img.width * escala, img.height * escala), Image.NEAREST)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Amplía una o dos PNG con vecino más cercano.")
    p.add_argument("png", nargs="+", help="una PNG, o dos para compararlas lado a lado")
    p.add_argument("-x", "--escala", type=int, default=3, help="cuántas veces (3 por defecto)")
    p.add_argument("-o", "--salida", help="dónde dejarla (por defecto, junto a la primera)")
    p.add_argument("--recorte", help="x0,y0,x1,y1: solo ese trozo, en píxeles de la original")
    a = p.parse_args(argv)
    if len(a.png) > 2:
        p.error("una PNG, o dos")
    recorte = tuple(int(n) for n in a.recorte.split(",")) if a.recorte else None

    imgs = [ampliar(r, a.escala, recorte) for r in a.png]
    if len(imgs) == 1:
        sale = imgs[0]
    else:
        w = imgs[0].width + HUECO + imgs[1].width
        h = max(i.height for i in imgs)
        sale = Image.new("RGBA", (w, h), (60, 60, 66, 255))
        sale.paste(imgs[0], (0, 0))
        sale.paste(imgs[1], (imgs[0].width + HUECO, 0))

    if a.salida:
        ruta = a.salida
    else:
        base, _ = os.path.splitext(a.png[0])
        if len(a.png) == 2:
            otra = os.path.splitext(os.path.basename(a.png[1]))[0]
            base = f"{base}_vs_{otra}"
        ruta = f"{base}_x{a.escala}.png"
    sale.save(ruta)
    print(os.path.abspath(ruta), sale.size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
