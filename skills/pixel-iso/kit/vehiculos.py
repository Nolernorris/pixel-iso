"""**Los vehículos**: furgonetas y camiones de cabina y caja, la tractora con su remolque y
su contenedor, en las ocho direcciones. Los turismos están en `coches.py`, que se apoya en
este; para meterlos en una escena, `camion_en`, `furgo_en` y `coche_en` de `kit.py`.

Sacado del generador de sprites de Guremu City, **copiado tal cual pinta**: lo que se ha
quitado es lo propio de la ciudad (la noche y sus registros de luces, los destellos de los
rotativos, las colas y las campas, las libreas con marca). Se importa como
`import vehiculos as v`.

Dos maneras de pintar un vehículo, y las dos salen aquí:

  1. **Dibujado en el lienzo** (`vehiculo()`: el camión de caja, la furgoneta, la
     ambulancia…): cajas isométricas a polígonos, cabina y caja, en las cuatro direcciones
     de la retícula con dos dibujos y un espejo, y en las cuatro intermedias (`recto=True`)
     con la vista recta.
  2. **Modelado en 3D de raster** (`tractora()`, `remolque()`, los turismos): caras planas
     en un `Raster` con su profundidad, giradas con un `_Rumbo` a cualquiera de los ocho
     `RUMBOS`. Un solo modelo da las ocho direcciones.

Todas las piezas llevan el ancla en el centro de su planta (`img.info["ancla"]`) y se meten
en una escena con `E.sprite(pieza, u, v, 0)`.
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

# El lápiz: la paleta, las rampas y el contorno son los del resto del kit.
from dibujo import (  # noqa: E402
    CRISTAL, NADA, NEGRO, Z_REDONDO, _tono_tubo, con_ancla, contorno, cr, material_de, punto,
    vecino,
)


# ------------------------------------------------------------------ colores sueltos
ROJO = (214, 62, 52, 255)
AMARILLO_OBRA = (236, 190, 48, 255)
BLANCO_PATRULLA = (196, 194, 188)
AMARILLO_TAXI = (226, 178, 48)
ROJO_BOMBEROS = (198, 58, 44)      # el rojo de un parque, no el teja de un tejado
# Los faros y los pilotos del de cabina y caja; bajo el piloto, un píxel oscuro.
FARO_CAJA = (255, 238, 180, 255)
PILOTO_CAJA = (236, 86, 68, 255)
HUECO_PILOTO = (26, 18, 17, 255)

# **Los rotativos, apagados**: la carcasa de cada tipo. Un color de luz no es material: no
# pasa por la rampa. El destello no está: aquí van siempre apagados.
LUCES = {
    "azul":  {"carcasa": (52, 86, 150, 255)},
    "rojo":  {"carcasa": (142, 46, 40, 255)},
    "ambar": {"carcasa": (146, 104, 26, 255)},
}

# **Un rotativo por servicio**: qué carcasas lleva. Los bomberos, en ámbar: son rojos, y
# rojo sobre rojo no se ve.
DESTELLOS = {
    "azul":    {"carcasa": ["azul"]},
    "rojo":    {"carcasa": ["rojo"]},
    "ambar":   {"carcasa": ["ambar"]},
    "policia": {"carcasa": ["azul", "rojo"]},
}


def barra_luces(d, x0, y0, x1, y1, tipo):
    """La carcasa de un rotativo, **apagada**. Media y media si lleva dos colores."""
    cols = DESTELLOS[tipo]["carcasa"]
    if len(cols) == 1:
        d.rectangle([x0, y0, x1, y1], fill=LUCES[cols[0]]["carcasa"])
        return
    medio = (x0 + x1) // 2
    d.rectangle([x0, y0, medio, y1], fill=LUCES[cols[0]]["carcasa"])
    d.rectangle([medio + 1, y0, x1, y1], fill=LUCES[cols[1]]["carcasa"])


# ------------------------------------------------------------------ lo que la pieza declara
def con_ruedas(img: Image.Image) -> Image.Image:
    """Marca que la pieza es **un vehículo de carretera**, de los que el editor deja aparcar."""
    img.info["rueda"] = True
    return img


def con_papel(img: Image.Image, papel: str = "efecto") -> Image.Image:
    """Marca para qué sirve la pieza cuando **no es para colocarla en el plano**: hoy,
    `efecto` (el humo, las llamas, los halos…)."""
    img.info["papel"] = papel
    return img


def con_canon(img: Image.Image, x, y) -> Image.Image:
    """Marca **por dónde sale el agua**: la punta del monitor, respecto al ancla. El chorro
    lo monta quien pinta."""
    ax, ay = img.info["ancla"]
    img.info["canon"] = (int(x - ax), int(y - ay))
    return img


# Lo que viaja respecto al ancla con un desplazamiento en x: `espejo()` lo voltea con ella.
INFO_CON_DX = ("bocas", "luces")


def espejo(img: Image.Image) -> Image.Image:
    """Voltea una pieza y **lleva el ancla al otro lado**, que si no se desfasa al revés."""
    fuera = img.transpose(Image.FLIP_LEFT_RIGHT)
    if "ancla" in img.info:
        ax, ay = img.info["ancla"]
        fuera.info["ancla"] = (img.size[0] - 1 - ax, ay)
    for clave in INFO_CON_DX:
        if clave in img.info:
            fuera.info[clave] = [(-p[0], *p[1:]) for p in img.info[clave]]
    if "canon" in img.info:
        cx, cy = img.info["canon"]
        fuera.info["canon"] = (-cx, cy)
    return fuera


# ------------------------------------------------------------------ las cajas de los vehículos
def caja_iso(img, wx, wy, a, b, h, mat, techo=None):
    """Caja isométrica de planta a×b y altura h, apoyada con su esquina oeste en (wx, wy). A
    polígonos (píxel a píxel quedan agujeros) y sin tramado (sale esponja)."""
    d = ImageDraw.Draw(img)
    W = (wx, wy)
    S = (wx + 2 * a, wy + a)
    E = (wx + 2 * a + 2 * b, wy + a - b)
    N = (wx + 2 * b, wy - b)
    sube = lambda p: (p[0], p[1] - h)                              # noqa: E731
    def banda(a, b, d1, d2, color):
        """Franja horizontal de la cara que va de a a b, entre dos profundidades."""
        d.polygon([(a[0], a[1] - h + d1), (b[0], b[1] - h + d1),
                   (b[0], b[1] - h + d2), (a[0], a[1] - h + d2)], fill=color)

    # Cada costado, en tres bandas: hombro a la luz, cuerpo y bajo en sombra.
    hombro = max(1, h // 4)
    bajo = max(1, h // 5)
    banda(W, S, 0, hombro, cr(mat, 4))                             # cara izquierda
    banda(W, S, hombro, h - bajo, cr(mat, 3))
    banda(W, S, h - bajo, h + 1, cr(mat, 2))
    banda(S, E, 0, hombro, cr(mat, 2))                             # cara derecha
    banda(S, E, hombro, h - bajo, cr(mat, 1))
    banda(S, E, h - bajo, h + 1, cr(mat, 0))

    # El techo, un paso **por debajo** del costado claro y con las esquinas matadas, o
    # parece una tapa apoyada encima.
    tw, ts, te, tn = sube(W), sube(S), sube(E), sube(N)
    d.polygon([(tw[0] + 1, tw[1]), ts, (te[0] - 1, te[1]), tn],
              fill=cr(techo or mat, 4))
    d.line([(tw[0] + 1, tw[1]), tn], fill=cr(techo or mat, 5))     # canto iluminado
    d.line([ts, te], fill=cr(techo or mat, 3))                     # canto en sombra
    d.line([tw, ts], fill=cr(mat, 5))                              # brillo del hombro
    d.line([sube(W), W], fill=cr(mat, 4))                          # arista de delante
    return {"W": W, "S": S, "E": E, "N": N, "alto": h}


def franja(img, caja, desde, grosor, color, lados=(0, 1)):
    """Franja horizontal que da la vuelta a una caja isométrica, a `desde` px del techo: lo
    que convierte un ladrillo de color en un vehículo."""
    d = ImageDraw.Draw(img)
    W, S, E = caja["W"], caja["S"], caja["E"]
    h = caja["alto"]
    for lado in lados:
        a, b = (W, S) if lado == 0 else (S, E)
        d.polygon([(a[0], a[1] - h + desde), (b[0], b[1] - h + desde),
                   (b[0], b[1] - h + desde + grosor), (a[0], a[1] - h + desde + grosor)],
                  fill=color)


def con_marcas(img, marcas, luz):
    """Pasa a la pieza lo que se apuntó mientras se dibujaba: la punta del monitor. Va
    **después del ancla**, que va respecto a ella."""
    if "canon" in marcas:
        con_canon(img, *marcas["canon"])
    return img


def monitor(img, bx, by, largo, ancho, alto, marcas, hacia=1, mat="acero"):
    """El **cañón de agua** sobre el techo de un camión de bomberos, y su punta: un bloque y
    una boca gruesa, no una torreta con detalle."""
    # **A la cola, no en medio**: ahí recorta contra el cielo; en medio no se lee.
    a0, b0 = (1 if hacia > 0 else largo - 2), (ancho - 1) / 2
    mx = bx + 2 * a0 + 2 * b0
    my = (by - alto) + a0 - b0
    # Pedestal **pequeño y oscuro**, boca **clara**: del mismo tono se funden en un amasijo.
    caja_iso(img, mx, my, 1, 1, 3, mat)
    cxm, cym = mx + 2, my - 3
    tx, ty = cxm + 4 * hacia, cym + 2 * hacia - 2
    ImageDraw.Draw(img).line([(cxm, cym - 1), (tx, ty)], fill=cr(mat, 5))
    marcas["canon"] = (tx, ty)


HOLGURA = 3        # separación del suelo de cualquier vehículo con ruedas


def sombra_suelo(img, wx, wy, largo, ancho, dy=2):
    """Sombra del vehículo: **su huella en planta**, bajada un par de píxeles. Una raya por su
    eje parecía suciedad."""
    ImageDraw.Draw(img).polygon(
        [(wx, wy + dy), (wx + 2 * largo, wy + largo + dy),
         (wx + 2 * largo + 2 * ancho, wy + largo - ancho + dy),
         (wx + 2 * ancho, wy - ancho + dy)], fill=(0, 0, 0, 55))


def bajos(img, wx, wy, largo, ancho, ruedas=(), holgura=HOLGURA):
    """Bajos del vehículo: el hueco oscuro bajo la carrocería, que **no toca el suelo**, con
    las ruedas dentro. `wy` es el suelo; la carrocería va `holgura` px más arriba."""
    d = ImageDraw.Draw(img)
    px = img.load()
    W = (wx, wy)
    S = (wx + 2 * largo, wy + largo)
    E = (S[0] + 2 * ancho, S[1] - ancho)
    # Chasis en sombra, y **las ruedas como bloques sueltos**: como mancha, lo mata.
    for a, b in ((W, S), (S, E)):
        d.polygon([(a[0], a[1] - holgura), (b[0], b[1] - holgura),
                   (b[0], b[1] - 1), (a[0], a[1] - 1)], fill=(52, 50, 48, 255))
    for r in ruedas:
        x = wx + r
        base = wy + (x - wx) // 2
        d.rectangle([x, base - holgura, x + 1, base], fill=(22, 21, 20, 255))
        punto(px, img, x + 1, base - holgura, (86, 84, 82, 255))
    d.line([(wx, wy + 1), (wx + 2 * (largo + ancho), wy + largo - ancho + 1)],
           fill=(0, 0, 0, 70))


def medidas_rectas(ancho_u, fondo_u):
    """Unidades de planta a píxeles, para algo puesto en diagonal de la retícula: `ancho_u` a
    lo ancho de la pantalla y `fondo_u` hacia dentro."""
    return max(1, round(4 * ancho_u / RAIZ2)), max(1, round(2 * fondo_u / RAIZ2))


def caja_recta(img, x, y, an, fondo, h, mat, techo=None):
    """Caja vista de frente: cara de delante de `an` x `h` y techo de `an` x `fondo`, con
    `(x, y)` abajo a la izquierda de la cara."""
    d = ImageDraw.Draw(img)
    hombro, bajo = max(1, h // 4), max(1, h // 5)
    d.rectangle([x, y - h + 1, x + an - 1, y - h + hombro], fill=cr(mat, 3))
    d.rectangle([x, y - h + hombro + 1, x + an - 1, y - bajo], fill=cr(mat, 2))
    d.rectangle([x, y - bajo + 1, x + an - 1, y], fill=cr(mat, 1))
    d.rectangle([x, y - h - fondo + 1, x + an - 1, y - h], fill=cr(techo or mat, 4))
    d.line([(x, y - h - fondo + 1), (x + an - 1, y - h - fondo + 1)],
           fill=cr(techo or mat, 5))                    # canto del techo, a la luz
    d.line([(x, y - h - fondo + 1), (x, y)], fill=cr(mat, 4))          # canto izquierdo
    d.line([(x + an - 1, y - h - fondo + 1), (x + an - 1, y)], fill=cr(mat, 0))
    return {"x": x, "y": y, "an": an, "fondo": fondo, "alto": h}


def franja_recta(img, caja, desde, grosor, color):
    """La franja que da la vuelta, en la vista recta: solo se ve en la cara de delante."""
    c = caja
    ImageDraw.Draw(img).rectangle(
        [c["x"] + 1, c["y"] - c["alto"] + desde, c["x"] + c["an"] - 2,
         c["y"] - c["alto"] + desde + grosor - 1], fill=color)


def bajos_rectos(img, x, y, an, fondo, ruedas=(), holgura=HOLGURA):
    """Los bajos y las ruedas de un vehículo en diagonal: las del costado que mira a la
    cámara, en fila y con hueco."""
    d = ImageDraw.Draw(img)
    px = img.load()
    d.rectangle([x, y - holgura + 1, x + an - 1, y], fill=(52, 50, 48, 255))
    for r in ruedas:
        d.rectangle([x + r, y - holgura + 1, x + r + 1, y], fill=(22, 21, 20, 255))
        punto(px, img, x + r + 1, y - holgura + 1, (86, 84, 82, 255))
    d.line([(x, y + 1), (x + an - 1, y + 1)], fill=(0, 0, 0, 70))


def sombra_recta(img, x, y, an, fondo, dy=2):
    """La sombra: su planta, que aquí es un rectángulo recto."""
    ImageDraw.Draw(img).rectangle([x, y - fondo + dy, x + an - 1, y + dy],
                                  fill=(0, 0, 0, 55))


# ------------------------------------------------------------------ los de cabina y caja
def monitor_recto(img, caja, marcas, perfil, atras, mat="acero"):
    """El cañón de agua en las cuatro direcciones rectas; de frente, la boca no se ve."""
    d = ImageDraw.Draw(img)
    if perfil:
        an_m = 4
        mx = caja["x"] + 2
        my = caja["y"] - caja["alto"] - max(1, caja["fondo"] // 2)
        # Tres de alto y no dos: con dos, `caja_recta` no tiene cuerpo que repartir.
        caja_recta(img, mx, my, an_m, 2, 3, mat)
        # Mirando a la derecha, que el espejo va al final.
        tx, ty = mx + an_m + 3, my - 5
        d.line([(mx + an_m - 1, my - 4), (tx, ty)], fill=cr(mat, 4), width=2)
    else:
        # El pedestal de canto, y no una caja: como caja salía una chimenea.
        an_m = max(3, caja["an"] // 3)
        mx = caja["x"] + (caja["an"] - an_m) // 2
        my = caja["y"] - caja["alto"] - max(1, caja["fondo"] // 2)
        d.rectangle([mx, my - 2, mx + an_m - 1, my], fill=cr(mat, 2))
        d.line([(mx, my - 2), (mx + an_m - 1, my - 2)], fill=cr(mat, 4))
        tx, ty = mx + an_m // 2, my - 2
        d.point((tx, ty), fill=cr(mat, 5))
    marcas["canon"] = (tx, ty)


def vehiculo(mat_caja="camion", mat_cabina="cabina", largo=7, alto=8, ancho=3,
             luz=None, hacia_der=True, rotulo_col=None, atras=False,
             recto=False, perfil=False, alto_cabina=None, canon=False) -> Image.Image:
    """Vehículo de cabina y caja, con falda y filetes: el cuerpo no es una sola caja.

    Las cuatro direcciones isométricas salen de dos dibujos (`atras`) y un espejo."""
    if recto:                                          # una de las cuatro intermedias
        return vehiculo_recto(mat_caja, mat_cabina, largo, alto, ancho, luz,
                              rotulo_col, atras, perfil, hacia_der,
                              alto_cabina, canon)
    h_cab = alto_cabina or alto
    ancho_px = 2 * (largo + ancho) + 24
    img = Image.new("RGBA", (ancho_px, 30), NADA)
    d = ImageDraw.Draw(img)
    wx, wy = 4, 19
    marcas = {}                                        # dónde quedan el rotativo y el monitor

    sombra_suelo(img, wx, wy, largo + 3, ancho)
    bajos(img, wx, wy, largo + 3, ancho,
          ruedas=(2, 2 * largo - 5, 2 * largo + 1))
    wy -= HOLGURA

    if atras:
        cx, cyv = wx, wy                               # cabina al fondo
        bx, by = wx + 6, wy + 3
    else:
        bx, by = wx, wy
        cx, cyv = wx + 2 * largo - 2, wy + largo - 1   # cabina delante

    def pinta_cabina():
        cab = caja_iso(img, cx, cyv, 3, ancho, h_cab, mat_cabina)
        franja(img, cab, 2, 2, CRISTAL)                # ventanillas, dan la vuelta
        if luz:                                        # rotativo sobre la cabina
            barra_luces(d, cx + 2, cyv - h_cab - 2, cx + 6, cyv - h_cab - 1, luz)
            marcas["luz"] = (cx + 4, cyv - h_cab - 2)

    def pinta_caja():
        caja = caja_iso(img, bx, by, largo, ancho, alto, mat_caja, techo=mat_caja)
        if rotulo_col:
            franja(img, caja, 3, 1, rotulo_col)        # filete alto
        d.line([(cx, cyv - h_cab), (cx, cyv)], fill=cr(mat_caja, 0))  # junta capó-cabina
        if canon:
            monitor(img, bx, by, largo, ancho, alto, marcas, -1 if atras else 1)

    # Ancla: (W + E) / 2 sobre la huella que usa `bajos()`.
    ancla = (wx + (largo + 3) + ancho, 19 + ((largo + 3) - ancho) / 2)
    faros, pilotos = luces_de_vehiculo(largo, ancho)
    # En isométrica manda la profundidad: lo que está más adelante se pinta después. Los
    # faros y los pilotos, **de donde están en la planta** (`luces_de_vehiculo()`): puestos a
    # ojo, el segundo piloto caía fuera de la trasera y en el blindado no casaban.
    if atras:
        pinta_cabina()
        pinta_caja()
        for p in pilotos:                              # pilotos, en la trasera
            pintar_luz(img, ancla, "i-", p, PILOTO_CAJA, hueco=True)
    else:
        pinta_caja()
        pinta_cabina()
        for p in faros:                                # faros, en el morro
            pintar_luz(img, ancla, "i+", p, FARO_CAJA)
    img = con_ancla(contorno(img), *ancla)
    img = con_marcas(img, marcas, luz)
    return img if hacia_der else espejo(img)


def luces_de_vehiculo(largo, ancho):
    """**Los faros y los pilotos del de cabina y caja**, `[delante, lado, alto]` desde el
    centro de su planta: la de `bajos()`, de `largo + 3` por `ancho`. El frente de la cabina
    queda a una unidad de la punta de los bajos, y la trasera en la punta; cada luz, a media
    unidad del canto y píxel y medio por encima de la holgura."""
    lado, alto = ancho / 2 - 0.5, HOLGURA + 1.5
    faros = [[(largo + 1) / 2, s * lado, alto] for s in (-1, 1)]
    pilotos = [[-(largo + 3) / 2, s * lado, alto] for s in (-1, 1)]
    return faros, pilotos


def en_pantalla(rumbo, delante, lado, alto):
    """**Un punto de la planta de un vehículo, en la pantalla**: `(dx, dy)` en píxeles desde
    su ancla, mirando a `rumbo`. `delante` y `lado` en unidades (`lado` a su derecha) y
    `alto` en píxeles."""
    a = math.radians(RUMBOS[rumbo])
    c_, s_ = math.cos(a), math.sin(a)
    u, v = delante * c_ + lado * s_, delante * s_ - lado * c_
    return 2 * u + 2 * v, u - v - alto


def pintar_luz(img, ancla, rumbo, punto_, col, hueco=False):
    """**Un faro o un piloto, pintado donde cae**: `punto_` es su `[delante, lado, alto]`,
    `ancla` el centro de la planta en píxeles (sin redondear) y `rumbo` hacia dónde mira el
    dibujo. Con `hueco`, el píxel oscuro debajo: rojo sobre rojo no existe."""
    dx, dy = en_pantalla(rumbo, *punto_)
    x, y = int(ancla[0] + dx + 0.5), int(ancla[1] + dy + 0.5)
    px = img.load()
    if hueco:
        punto(px, img, x, y + 1, HUECO_PILOTO)
    punto(px, img, x, y, col)


def vehiculo_recto(mat_caja="camion", mat_cabina="cabina", largo=7, alto=8, ancho=3,
                   luz=None, rotulo_col=None, atras=False, perfil=False,
                   hacia_der=True, alto_cabina=None, canon=False) -> Image.Image:
    """El mismo vehículo por una de las cuatro intermedias: `perfil`, de lado; sin él, de
    frente o de espaldas."""
    D = largo + 2                                      # de punta a punta, en unidades
    an, fondo = (medidas_rectas(D, ancho) if perfil else medidas_rectas(ancho, D))
    img = Image.new("RGBA", (an + 8, alto + fondo + HOLGURA + 10), NADA)
    d = ImageDraw.Draw(img)
    x0, y0 = 4, img.size[1] - 5                        # suelo, esquina izquierda

    sombra_recta(img, x0, y0, an, fondo)
    if perfil:
        bajos_rectos(img, x0, y0, an, fondo,
                     ruedas=(2, an - 8, an - 4))
    else:
        bajos_rectos(img, x0, y0, an, fondo, ruedas=(1, an - 3))
    y0 -= HOLGURA

    px_u = 2 / RAIZ2                                   # px de fondo por unidad
    def trozo(desde, cuantas, mat, techo=None, h=None):
        """Un cuerpo de `desde` a `desde + cuantas` unidades desde la punta de la cámara.

        Siempre mirando a la derecha: espejarlo aquí también lo anula."""
        if perfil:
            a = max(2, round(4 * cuantas / RAIZ2))
            x = x0 + an - round(4 * (desde + cuantas) / RAIZ2)
            return caja_recta(img, x, y0, a, fondo, h or alto, mat, techo)
        return caja_recta(img, x0, y0 - round(px_u * desde), an,
                          max(1, round(px_u * cuantas)), h or alto, mat, techo)

    # La cabina, un píxel más baja que la caja: aquí el escalón no sale solo.
    h_cab = alto_cabina or (alto - 1)
    if atras:
        cab = trozo(largo - 2, 3, mat_cabina, h=h_cab)      # al fondo: solo asoma arriba
        caja = trozo(0, largo, mat_caja, techo=mat_caja)
    else:
        caja = trozo(2, largo, mat_caja, techo=mat_caja)
        cab = trozo(0, 3, mat_cabina, h=h_cab)

    if rotulo_col:
        franja_recta(img, caja, 3, 1, rotulo_col)
    if not atras or perfil:                            # cabina al fondo: sin ventanillas
        franja_recta(img, cab, 2, 2, CRISTAL)
    marcas = {}
    if luz:
        lx0 = cab["x"] + max(1, cab["an"] // 3)
        lx1 = cab["x"] + cab["an"] - 1 - max(1, cab["an"] // 3)
        ly = cab["y"] - h_cab - cab["fondo"] - 1
        barra_luces(d, lx0, ly, lx1, ly + 1, luz)
        marcas["luz"] = ((lx0 + lx1) // 2, ly)
    if canon:
        monitor_recto(img, caja, marcas, perfil, atras)

    # Faros o pilotos, en la punta que mira a la cámara; los pilotos, con un píxel negro
    # debajo.
    punta = cab if not atras else caja
    ojos = (punta["x"] + 1, punta["x"] + punta["an"] - 2)
    for ox in ojos:
        if atras:
            d.point((ox, punta["y"] - 1), fill=HUECO_PILOTO)
            d.point((ox, punta["y"] - 2), fill=PILOTO_CAJA)
        else:
            d.point((ox, punta["y"] - 2), fill=FARO_CAJA)

    img = con_ancla(contorno(img), x0 + an / 2, img.size[1] - 5 - fondo / 2)
    img = con_marcas(img, marcas, luz)
    return img if hacia_der else espejo(img)


# A un tercio de casilla, como en el juego: cuenta el contraste, no el detalle fino.
def camion(**kw):
    return vehiculo("camion", "cabina", 5, 6, 2, rotulo_col=cr("cabina", 5), **kw)


def furgoneta(**kw):
    return vehiculo("cobre", "cobre", 4, 5, 2, **kw)


def furgoneta_obra(**kw):
    """La furgoneta del estado **reformas**: se distingue por el amarillo de obra, sin baca."""
    kw.setdefault("rotulo_col", AMARILLO_OBRA)
    return vehiculo(material_de(AMARILLO_OBRA[:3], "amarillo_obra"), "blanco",
                    4, 5, 2, **kw)


def blindado(**kw):
    """**El furgón de las copias**: cabina y caja, la caja cerrada y sin ventanas."""
    return vehiculo("acero", "acero", 4, 5, 3,
                    rotulo_col=(188, 196, 208, 255), **kw)


def ambulancia(**kw):
    return vehiculo("blanco", "blanco", 4, 5, 2, luz="rojo", rotulo_col=ROJO, **kw)


def bombero(**kw):
    """El camión de bomberos, que no es un camión rojo: rojo de parque, monitor, cabina
    baja, rotativo ámbar y franja blanca."""
    return vehiculo(material_de(ROJO_BOMBEROS, "bomberos"),
                    material_de(ROJO_BOMBEROS, "bomberos"),
                    6, 6, 2, luz="ambar", rotulo_col=cr("blanco", 5),
                    alto_cabina=5, canon=True, **kw)


# ------------------------------------------------------------------ el 3D de raster
# **Se pintan caras, no puntos**: con puntos sueltos, a este tamaño sale moteado.

RAIZ2 = 2 ** 0.5


def _tono_vec(n):
    """El tono de una superficie según hacia dónde mire, con la luz de siempre."""
    return _tono_tubo(n[0], n[1], n[2])


# --------------------------- las herramientas del camión articulado
# **Se pintan caras, no puntos**: con puntos sueltos, a este tamaño sale moteado.

CROMO = material_de((190, 194, 200), "cromo")
NEUMATICO = material_de((44, 42, 42), "neumatico")
# Los ocho rumbos: 0 grados es i+, y se gira contra el reloj vista desde arriba (de u
# hacia v, hacia j-).
RUMBOS = {"i+": 0, "der": 45, "j-": 90, "arriba": 135, "i-": 180, "izq": 225,
          "j+": 270, "abajo": 315}


class Raster:
    """Caras planas en el espacio, rasterizadas píxel a píxel con su profundidad. Una cara es
    `O + a E1 + b E2`, y se pinta con `col(a, b)` donde cae dentro."""

    def __init__(self, wx, wy):
        self.wx, self.wy = wx, wy
        self.buf = {}

    @staticmethod
    def S(p):
        u, v, z = p
        return 2 * u + 2 * v, u - v - z

    def poner(self, x, y, prof, col):
        antes = self.buf.get((x, y))
        if antes is None or prof > antes[0]:
            self.buf[(x, y)] = (prof, col)

    def cara(self, O, E1, E2, col, disco=False, tri=False):
        """`tri`: solo la mitad con a + b <= 1, el triángulo O, O + E1, O + E2."""
        sx, sy = self.S(O)
        e1x, e1y = self.S(E1)
        e2x, e2y = self.S(E2)
        det = e1x * e2y - e2x * e1y
        if abs(det) < 1e-6:
            return                                     # de canto: no se ve
        rango = (-1, 1) if disco else (0, 1)
        esq = [(sx + a * e1x + b * e2x, sy + a * e1y + b * e2y)
               for a in rango for b in rango]
        for X in range(math.floor(self.wx + min(p[0] for p in esq)) - 1,
                       math.ceil(self.wx + max(p[0] for p in esq)) + 2):
            for Y in range(math.floor(self.wy + min(p[1] for p in esq)) - 1,
                           math.ceil(self.wy + max(p[1] for p in esq)) + 2):
                dx, dy = X - self.wx - sx, Y - self.wy - sy
                a = (dx * e2y - e2x * dy) / det
                b = (e1x * dy - dx * e1y) / det
                if disco:
                    if a * a + b * b > 1.0001:
                        continue
                elif not (-1e-9 <= a <= 1 + 1e-9 and -1e-9 <= b <= 1 + 1e-9):
                    continue
                elif tri and a + b > 1 + 1e-9:
                    continue
                c = col(a, b) if callable(col) else col
                if c is not None:
                    u, v, z = (O[k] + a * E1[k] + b * E2[k] for k in range(3))
                    self.poner(X, Y, u - v + z / Z_REDONDO, c)

    def linea(self, p0, p1, col):
        """Una barra de un píxel, un pelo por delante de lo que tenga detrás."""
        for k in range(41):
            p = [p0[i] + (p1[i] - p0[i]) * k / 40 for i in range(3)]
            x, y = self.S(p)
            self.poner(int(round(self.wx + x)), int(round(self.wy + y)),
                       p[0] - p[1] + p[2] / Z_REDONDO + 0.01, col)

    def punto(self, p, col):
        x, y = self.S(p)
        self.poner(int(round(self.wx + x)), int(round(self.wy + y)), 99, col)

    def imagen(self, w, h):
        img = Image.new("RGBA", (w, h), NADA)
        px = img.load()
        for (x, y), (_p, c) in self.buf.items():
            if 0 <= x < w and 0 <= y < h:
                px[x, y] = c
        return img


class _Rumbo:
    """El sistema de un vehículo —x adelante, y a su izquierda, z arriba— girado a un
    rumbo en grados (`RUMBOS`), sobre un `Raster`."""

    def __init__(self, r, grados):
        self.r = r
        a = math.radians(grados)
        self.c, self.s = math.cos(a), math.sin(a)

    def P(self, x, y, z):
        return (x * self.c - y * self.s, x * self.s + y * self.c, z)

    V = P                                              # sin desplazamiento: lo mismo

    def luz(self, x, y, z, col, punta=1):
        """**Un faro** (o un piloto, con `punta=-1`): un píxel en `(x, y, z)`, solo si esa
        punta del vehículo mira a la cámara, y con la profundidad de donde está, medio punto
        por delante (gana a la cara y a su canto): lo que asome más lo tapa. Es lo que no sale
        pintando la cara: un faro de medio píxel cae entre dos centros y no se ve."""
        if punta * (self.c - self.s) <= 0.1:
            return
        p = self.P(x, y, z)
        sx, sy = self.r.S(p)
        self.r.poner(int(round(self.r.wx + sx)), int(round(self.r.wy + sy)),
                     p[0] - p[1] + z / Z_REDONDO + 0.5, col)

    def luces(self, faros, pilotos, faro, piloto):
        """Los faros y los pilotos, `[delante, lado, alto]` con `lado` a la derecha, cada uno
        en su punta y de su color."""
        for d, lado, z in faros:
            self.luz(d, -lado, z, faro)
        for d, lado, z in pilotos:
            self.luz(d, -lado, z, piloto, punta=-1)

    def tono(self, nx, ny, nz, mas=0.0):
        n = self.V(nx, ny, 0)                         # una dirección: no se corre
        return max(0, min(5, round(_tono_vec((n[0], n[1], nz)) + mas)))

    def caja(self, x0, x1, y0, y1, z0, z1, mat, mas=0.0, det=None):
        """Una caja. `det[cara](a, b, tono)` pinta detalle en una cara —'frente',
        'atras', 'izq', 'der' o 'techo'— y devuelve None donde no hay."""
        det = det or {}
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0

        def pinta(nombre, n):
            t = self.tono(*n, mas)
            base, f = cr(mat, t), det.get(nombre)
            return (lambda a, b: f(a, b, t) or base) if f else base
        self.r.cara(self.P(x1, y0, z0), self.V(0, dy, 0), self.V(0, 0, dz),
                    pinta("frente", (1, 0, 0)))
        self.r.cara(self.P(x0, y1, z0), self.V(0, -dy, 0), self.V(0, 0, dz),
                    pinta("atras", (-1, 0, 0)))
        self.r.cara(self.P(x1, y1, z0), self.V(-dx, 0, 0), self.V(0, 0, dz),
                    pinta("izq", (0, 1, 0)))
        self.r.cara(self.P(x0, y0, z0), self.V(dx, 0, 0), self.V(0, 0, dz),
                    pinta("der", (0, -1, 0)))
        self.r.cara(self.P(x0, y0, z1), self.V(dx, 0, 0), self.V(0, dy, 0),
                    pinta("techo", (0, 0, 1)))

    def rueda(self, x, y0, y1, z, r=0.9):
        """Una rueda con el eje a lo ancho, de `y0` a `y1`: la banda en tramos, sombreada
        como un tubo, y en las dos caras el neumático oscuro con **el cubo claro**."""
        rz, n = 2 * r * 0.85, 14
        for k in range(n):
            t0, t1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
            tm = (t0 + t1) / 2
            self.r.cara(self.P(x + r * math.cos(t0), y0, z + rz * math.sin(t0)),
                        self.V(r * (math.cos(t1) - math.cos(t0)), 0,
                               rz * (math.sin(t1) - math.sin(t0))),
                        self.V(0, y1 - y0, 0),
                        cr(NEUMATICO, self.tono(math.cos(tm), 0, math.sin(tm))))
        for yb, claro in ((y0, 2), (y1, 3)):
            self.r.cara(self.P(x, yb, z), self.V(r, 0, 0), self.V(0, 0, rz),
                        lambda a, b, claro=claro:
                        cr(CROMO, claro) if a * a + b * b < 0.2 else cr(NEUMATICO, 0),
                        disco=True)

    def doble(self, x, s, z=1.7):
        """Las ruedas dobles de un lado (`s` = ±1): de 0,45 a 1,45 del eje."""
        self.rueda(x, *sorted((s * 0.45, s * 1.45)), z)

    def tubo(self, x, y, z0, z1, mat):
        """Un tubo fino de pie, en dos tonos: el escape."""
        self.r.linea(self.P(x, y, z0), self.P(x, y, z1), cr(mat, 4))
        self.r.linea(self.P(x + 0.18, y - 0.18, z0), self.P(x + 0.18, y - 0.18, z1),
                     cr(mat, 2))

    def deposito(self, x0, x1, y, z, r, mat):
        """Un depósito tumbado a lo largo."""
        n = 10
        for k in range(n):
            t0, t1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
            tm = (t0 + t1) / 2
            self.r.cara(self.P(x0, y + r * math.cos(t0), z + 2 * r * math.sin(t0)),
                        self.V(0, r * (math.cos(t1) - math.cos(t0)),
                               2 * r * (math.sin(t1) - math.sin(t0))),
                        self.V(x1 - x0, 0, 0),
                        cr(mat, self.tono(0, math.cos(tm), math.sin(tm), 0.3)))


# ------------------------------------------------------------------ el contenedor
def perfilar(img, caja, color=(24, 23, 22, 255)):
    """Dibuja el contorno de una caja isométrica sobre sí misma, para que dos cajas pegadas
    no se fundan."""
    d = ImageDraw.Draw(img)
    W, S, E, N, h = caja["W"], caja["S"], caja["E"], caja["N"], caja["alto"]

    def sube(p):
        return (p[0], p[1] - h)

    d.line([sube(W), sube(N)], fill=color)             # tapa
    d.line([sube(N), sube(E)], fill=color)
    d.line([sube(E), sube(S)], fill=color)
    d.line([sube(S), sube(W)], fill=color)
    for p in (W, S, E):                                # cantos verticales
        d.line([p, sube(p)], fill=color)
    d.line([W, S], fill=color)                         # base
    d.line([S, E], fill=color)


# Lo que mide un contenedor, largo x ancho x alto, en unidades de planta y píxeles de alto.
CONTENEDOR_40 = (8, 3, 8)


def a_su_silueta(img, cajas):
    """Borra lo que se haya pintado fuera de la silueta de unas cajas isométricas. Solo para
    un lienzo con las cajas solas: lo que haya debajo se borra también."""
    mascara = Image.new("L", img.size, 0)
    dm = ImageDraw.Draw(mascara)
    for c in cajas:
        h = c["alto"]
        borde = [c["W"], c["S"], c["E"], (c["E"][0], c["E"][1] - h),
                 (c["N"][0], c["N"][1] - h), (c["W"][0], c["W"][1] - h)]
        dm.polygon(borde, fill=255)
        # Las rayas del perfil, las mismas y en el mismo sentido que en `perfilar()`, o se
        # lleva medio perfil.
        W, S, E, N = c["W"], c["S"], c["E"], c["N"]
        sube = lambda p: (p[0], p[1] - h)              # noqa: E731
        for p, q in ((sube(W), sube(N)), (sube(N), sube(E)), (sube(E), sube(S)),
                     (sube(S), sube(W)), (W, sube(W)), (S, sube(S)), (E, sube(E)),
                     (W, S), (S, E)):
            dm.line([p, q], fill=255)
    vacio = Image.new("RGBA", img.size, NADA)
    img.paste(vacio, (0, 0), Image.eval(mascara, lambda v: 255 - v))
    return img


def _cantoneras(d, caja, h, col):
    """Las tres cantoneras de la tapa, en claro, **dentro del perfil**: un píxel por encima
    de las esquinas de los lados cae fuera."""
    W, S, E = caja["W"], caja["S"], caja["E"]
    for x, y in ((W[0] + 2, W[1] - h), (S[0], S[1] - h - 1), (E[0] - 2, E[1] - h)):
        d.point((x, y), fill=cr(col, 5))


def caja_contenedor_eje(img, cx, cy, col, eje="i"):
    """Un 40 pies con su centro de planta en `(cx, cy)`, a lo largo de `eje`, con las
    puertas en el testero que se ve."""
    largo, ancho, h = CONTENEDOR_40
    a, b = (largo, ancho) if eje == "i" else (ancho, largo)
    wx, wy = cx - a - b, cy - (a - b) // 2
    d = ImageDraw.Draw(img)
    caja = caja_iso(img, wx, wy, a, b, h, col)
    for k in range(1, a):                              # el corrugado de la cara izquierda
        x0, y0 = wx + 2 * k, wy + k
        d.line([(x0, y0 - h + 1), (x0, y0 - 1)], fill=cr(col, 2))
    for k in range(1, b):                              # y el de la derecha
        x0, y0 = wx + 2 * a + 2 * k, wy + a - k
        d.line([(x0, y0 - h + 1), (x0, y0 - 1)], fill=cr(col, 0))
    # Las barras de las puertas: a la derecha con el eje i, a la izquierda con el j.
    if eje == "i":
        for k in (1, b - 1):
            x0, y0 = wx + 2 * a + 2 * k, wy + a - k
            d.line([(x0, y0 - h + 1), (x0, y0 - 1)], fill=cr(col, 4))
    else:
        for k in (1, a - 1):
            x0, y0 = wx + 2 * k, wy + k
            d.line([(x0, y0 - h + 1), (x0, y0 - 1)], fill=cr(col, 5))
    perfilar(img, caja)
    _cantoneras(d, caja, h, col)
    return caja


def contenedor_patio(col, eje="i") -> Image.Image:
    """Un contenedor suelto, a lo largo de `eje` («i» o «j»), para apilar: el piso `k` va
    `k * 9` px más arriba."""
    img = Image.new("RGBA", (44, 32), NADA)
    a_su_silueta(img, [caja_contenedor_eje(img, 22, 22, col, eje)])
    return con_papel(con_ancla(img, 22, 22))


# ------------------------------------------------------------------ el camión articulado
CHASIS = material_de((62, 60, 62), "chasis")
BASTIDOR = material_de((112, 112, 118), "bastidor remolque")
VIDRIO = material_de((52, 66, 88), "vidrio cabina")
GALIBO = (244, 176, 60, 255)                        # las luces ámbar sobre el parabrisas
# Los faros y los pilotos.
FARO = (255, 242, 196, 255)
PILOTO = (232, 66, 52, 255)
# **Encendidas o apagadas** (`luces_encendidas()`): cada color de luz con su apagado. El faro
# apagado es cristal gris; el piloto, un rojo oscuro; el gálibo, un ámbar sucio. Encendidas por
# defecto, como en la ciudad.
_LUCES = {
    "FARO": (FARO, (168, 170, 164, 255)),
    "PILOTO": (PILOTO, (128, 44, 38, 255)),
    "GALIBO": (GALIBO, (150, 112, 54, 255)),
    "FARO_CAJA": (FARO_CAJA, (168, 170, 164, 255)),
    "PILOTO_CAJA": (PILOTO_CAJA, (128, 44, 38, 255)),
}


def luces_encendidas(si=True):
    """**Los faros, los pilotos y las luces de gálibo, encendidos o apagados**, para todo lo que
    se pinte después, también los turismos de `coches.py`. Encendidos (por defecto) son píxeles
    de luz que destacan; apagados, el cristal de un vehículo aparcado o de día."""
    globals().update({k: v[0 if si else 1] for k, v in _LUCES.items()})
    coches = sys.modules.get("coches")
    if coches is not None:
        coches.FARO, coches.PILOTO = FARO, PILOTO
TRACTORA_COLORES = {"roja": material_de((178, 52, 40), "tractora roja"),
                    "azul": material_de((44, 86, 150), "tractora azul"),
                    "blanca": material_de((214, 212, 204), "tractora blanca")}
TRACTORA_DETALLES = {}
REMOLQUE_COLORES = {}
# En unidades desde el ancla de cada pieza.
TRACTORA_LARGO = (-3.15, 3.2)
REMOLQUE_LARGO = (-4.65, 4.5)
QUINTA = -2.0                       # la quinta rueda, en la tractora
# **Los faros y los pilotos de la tractora**, de sus medidas: los faros en medio de la cara de
# delante de cada aleta (`ALETA`: x, y y z de la de la izquierda), y los pilotos en lo alto de
# las faldillas, en la punta de atrás.
ALETA = (1.2, 2.95, 0.8, 1.4, 3.0, 3.6)
TRACTORA_FAROS = [[ALETA[1], s * (ALETA[2] + ALETA[3]) / 2, (ALETA[4] + ALETA[5]) / 2] for s in (-1, 1)]
TRACTORA_PILOTOS = [[TRACTORA_LARGO[0], s * 1.2, 2.6] for s in (-1, 1)]
PIVOTE = 3.5                        # el pivote, en el remolque
REMOLQUE_PILOTOS = [[REMOLQUE_LARGO[0], s * 1.2, 2.0] for s in (-1, 1)]
CAMA_Z = 4                          # px: el contenedor apoyado en los cierres
CAMION_LIENZO, CAMION_ANCLA = (64, 48), (32, 34)


def contorno_fuera(img: Image.Image) -> Image.Image:
    """El perfil negro **solo por fuera**: con `contorno()` los huecos del chasis salían
    negros."""
    px = img.load()
    a = np.asarray(img.getchannel("A"))
    libre = a == 0
    # Lo de fuera: lo transparente que se alcanza desde el canto. Con numpy, creciendo de
    # vecino en vecino hasta que no cambia.
    fuera = np.zeros_like(libre)
    fuera[0, :], fuera[-1, :] = libre[0, :], libre[-1, :]
    fuera[:, 0] |= libre[:, 0]
    fuera[:, -1] |= libre[:, -1]
    while True:
        mas = (fuera | vecino(fuera)) & libre
        if np.array_equal(mas, fuera):
            break
        fuera = mas
    # Los huecos de dentro, **uno a uno y en orden**, como siempre: uno ya relleno cuenta
    # como vecino del siguiente. Son pocos.
    huecos = libre & ~fuera
    huecos[0, :] = huecos[-1, :] = huecos[:, 0] = huecos[:, -1] = False
    cruz = ((1, 0), (-1, 0), (0, 1), (0, -1))
    for y, x in zip(*np.nonzero(huecos)):
        x, y = int(x), int(y)
        vec = [px[x + dx, y + dy] for dx, dy in cruz if px[x + dx, y + dy][3]]
        if len(vec) >= 3:
            px[x, y] = vec[0]
    for y, x in zip(*np.nonzero(fuera & vecino(a > 128))):
        px[int(x), int(y)] = NEGRO
    return img


def _tractora(rm, mat, detalle=CROMO):
    # El bastidor y la quinta rueda.
    for y in (-0.55, 0.55):
        rm.caja(-3.0, 2.9, y - 0.25, y + 0.25, 1.2, 2.4, CHASIS, -0.5)
    rm.caja(QUINTA - 0.7, QUINTA + 0.7, -1.0, 1.0, 2.4, 2.9, CHASIS, 0.3)
    # El tándem motriz con ruedas dobles, y la de dirección, sencilla.
    for x in (-2.5, -1.35):
        for s in (-1, 1):
            rm.doble(x, s)
    for s in (-1, 1):
        rm.rueda(2.0, *sorted((s * 0.95, s * 1.4)), 1.7)
    # Las faldillas y el guardabarros corrido sobre el tándem.
    for s in (-1, 1):
        rm.caja(-3.15, -3.0, *sorted((s * 0.85, s * 1.5)), 0.4, 3.0, NEUMATICO)
        rm.caja(-3.1, -0.9, *sorted((s * 0.85, s * 1.5)), 3.3, 3.6, CHASIS)
    # Los depósitos de gasoil, cromados, bajo la puerta.
    for s in (-1, 1):
        rm.deposito(-0.4, 0.8, s * 1.15, 2.1, 0.33, detalle)

    # El morro largo, en una sola caja: con dos salían rayas oscuras.
    def parrilla(a, b, t):
        if 0.18 < a < 0.82 and b < 0.82:
            return cr(detalle, 4 if int(a * 12) % 2 else 2)
    rm.caja(0.9, 3.0, -0.8, 0.8, 2.3, 5.4, mat, det={"frente": parrilla})
    x0, x1, y0, y1, z0, z1 = ALETA
    for s in (-1, 1):                                  # las aletas, con su faro
        rm.caja(x0, x1, *sorted((s * y0, s * y1)), z0, z1, mat,
                det={"frente": lambda a, b, t: FARO if 0.3 < a < 0.7 else None})
    rm.caja(3.0, 3.2, -1.45, 1.45, 1.6, 2.4, detalle, -0.5)          # el parachoques

    # La cabina, con el parabrisas partido y la ventanilla en la puerta.
    def parabrisas(a, b, t):
        if 0.62 < b < 0.92 and 0.08 < a < 0.92 and abs(a - 0.5) > 0.04:
            return cr(VIDRIO, 4 if b > 0.82 else 2)

    def ventanilla(a, b, t):
        if 0.6 < b < 0.9 and 0.15 < a < 0.85:
            return cr(VIDRIO, 3 if b > 0.8 else 1)
    rm.caja(-0.3, 0.9, -1.35, 1.35, 2.3, 7.8, mat,
            det={"frente": parabrisas, "izq": ventanilla, "der": ventanilla})

    # La litera, un punto más alta, con su ventanuco.
    def ventanuco(a, b, t):
        if 0.62 < b < 0.76 and 0.35 < a < 0.65:
            return cr(VIDRIO, 1)
    rm.caja(-1.4, -0.3, -1.35, 1.35, 2.5, 8.4, mat, 0.2,
            det={"izq": ventanuco, "der": ventanuco})
    # Las luces de gálibo y los escapes de pie.
    for y in (-0.7, 0.0, 0.7):
        rm.r.punto(rm.P(0.85, y, 8.0), GALIBO)
    for s in (-1, 1):
        rm.tubo(-0.35, s * 1.5, 3.0, 11.0, detalle)
    # **Los faros, en punto**: la cara de la aleta mide medio píxel y solo salían mirando de
    # frente. Y los pilotos, en lo alto de las faldillas.
    rm.luces(TRACTORA_FAROS, TRACTORA_PILOTOS, FARO, PILOTO)


def _remolque(rm, bastidor=BASTIDOR, cierres=CROMO):
    # **Un chasis de escalera**, en gris: casi negro salía una losa.
    for y in (-0.8, 0.8):
        rm.caja(-4.4, 4.4, y - 0.15, y + 0.15, 2.1, 3.0, bastidor, -0.5)
    # Los travesaños de las puntas, **bajo las esquinas del contenedor**.
    largo = CONTENEDOR_40[0] / 2
    for x0, x1 in ((largo - 0.45, largo + 0.1), (-largo - 0.1, -largo + 0.45)):
        rm.caja(x0, x1, -1.55, 1.55, 2.3, CAMA_Z - 0.4, bastidor, 0.2)
        for s in (-1, 1):                              # en la esquina misma, hasta la cama
            rm.caja(x0 + 0.05, x1 - 0.05, *sorted((s * 1.15, s * 1.55)), CAMA_Z - 0.4,
                    CAMA_Z, cierres, -2)
    # Los de en medio, a todo lo ancho, y un larguero por borde: sin ellos asoma el suelo.
    for x in (2.2, 1.0, -0.25, -1.5):
        rm.caja(x - 0.15, x + 0.15, -1.5, 1.5, 2.5, 2.9, bastidor, -0.8)
    for y in (-1.45, 1.45):
        rm.caja(-largo, largo, y - 0.08, y + 0.08, 2.5, 2.9, bastidor, -0.8)
    # El tándem, con sus faldillas, y la barra de pilotos.
    for x in (-3.35, -2.25):
        for s in (-1, 1):
            rm.doble(x, s)
    for s in (-1, 1):
        rm.caja(-4.1, -3.95, *sorted((s * 0.9, s * 1.5)), 0.4, 2.6, NEUMATICO)
    rm.caja(-4.65, -4.5, -1.5, 1.5, 1.5, 2.3, CHASIS,
            det={"atras": lambda a, b, t: PILOTO if (a < 0.2 or a > 0.8) and b > 0.3
                 else None})
    rm.luces((), REMOLQUE_PILOTOS, None, PILOTO)       # y en punto, que de espaldas no salían
    # Las patas de apoyo, con su pie y el eje de la manivela.
    for s in (-1, 1):
        rm.caja(2.55, 2.85, s * 1.0 - 0.15, s * 1.0 + 0.15, 0.4, 2.1, CHASIS, 0.4)
        rm.caja(2.45, 2.95, s * 1.0 - 0.3, s * 1.0 + 0.3, 0.0, 0.4, CHASIS, -0.3)


def _contenedor_raster(rm, mat, dibujo=None):
    """El 40 pies en las diagonales, que el de los ejes (`contenedor_patio`) no tiene. Con `dibujo`
    (`_dibujo_diagonal()`), el de su librea donde se vea."""
    largo, ancho, alto = CONTENEDOR_40

    def costado(a, b, t):
        if 0.05 < b < 0.95 and int(a * 2 * largo) % 2:
            return cr(mat, max(0, t - 1))

    def puertas(a, b, t):
        if 0.1 < b < 0.92 and min(abs(a - k) for k in (0.18, 0.4, 0.6, 0.82)) < 0.05:
            return cr(mat, min(5, t + 2))
    det = {"izq": costado, "der": costado, "atras": puertas}
    if dibujo:
        det.update(_dibujo_diagonal(rm, mat, det, *dibujo))
    rm.caja(-largo / 2, largo / 2, -ancho / 2, ancho / 2, 0, alto, mat, det=det)


# **El dibujo en las diagonales**, solo donde el costado largo sale derecho en pantalla.
DIAGONALES_COSTADO = ("der", "izq")


def _mapa_dibujo(dibujo, colores, derechas=()):
    """El dibujo y sus trozos derechos (`_dibujo_cara()`) en un mapa `(columna, fila)` →
    color, con la columna 0 en la primera del dibujo."""
    ancho = len(dibujo[0])
    mapa = {(c, f): colores[k] for f, fila in enumerate(dibujo) for c, k in enumerate(fila)
            if k in colores}
    for dc, df, trozo in derechas:
        c0 = ancho // 2 + dc - len(trozo[0]) // 2
        mapa.update({(c0 + c, df + f): colores[k] for f, fila in enumerate(trozo)
                     for c, k in enumerate(fila) if k in colores})
    return mapa, ancho, len(dibujo)


def _dibujo_diagonal(rm, mat, det, rumbo, mapa, ancho, alto, liso):
    """Los `det` de `_Rumbo.caja()` que ponen el dibujo en el costado que se ve, en `der` e
    `izq`; en los otros rumbos, ninguno."""
    largo, ancho_c, alto_c = CONTENEDOR_40
    x0, x1 = -largo / 2, largo / 2
    if rumbo not in DIAGONALES_COSTADO:
        return {}
    caras = {"izq": ((x0 - x1, 0, 0), (0, 0, alto_c)), "der": ((x1 - x0, 0, 0), (0, 0, alto_c))}
    fuera = {}
    for nombre, (e1, e2) in caras.items():
        s1, s2 = Raster.S(rm.V(*e1)), Raster.S(rm.V(*e2))
        xs = (0, s1[0], s2[0], s1[0] + s2[0])
        ys = (0, s1[1], s2[1], s1[1] + s2[1])
        cx = (min(xs) + max(xs)) / 2
        f0 = min(ys) + 1                    # desde la fila de debajo del canto, como en los ejes
        base = det.get(nombre)

        def pinta(a, b, t, s1=s1, s2=s2, cx=cx, f0=f0, base=base):
            c = math.floor(a * s1[0] + b * s2[0] - cx + ancho / 2)
            f = math.floor(a * s1[1] + b * s2[1] - f0)
            if (c, f) in mapa:
                return mapa[(c, f)]
            if liso and -1 <= c <= ancho and 0 <= f < alto:
                return cr(mat, t)
            return base(a, b, t) if base else None
        fuera[nombre] = pinta
    return fuera


def _pieza_camion(dibujo, rumbo, largo, *args, sombra=True):
    """Una pieza del camión a un rumbo, con sombra y perfil, recortada y anclada al centro."""
    W, H = CAMION_LIENZO
    r = Raster(*CAMION_ANCLA)
    dibujo(_Rumbo(r, RUMBOS[rumbo]), *args)
    img = contorno_fuera(r.imagen(W, H))
    if sombra:
        s = Raster(CAMION_ANCLA[0] + 2, CAMION_ANCLA[1] + 1)
        rs = _Rumbo(s, RUMBOS[rumbo])
        s.cara(rs.P(largo[0], -1.4, 0), rs.V(largo[1] - largo[0], 0, 0),
               rs.V(0, 2.8, 0), (0, 0, 0, 60))
        fondo = s.imagen(W, H)
        fondo.alpha_composite(img)
        img = fondo
    x0, y0, x1, y1 = img.getbbox()
    caja = (x0 - 1, y0 - 1, x1 + 1, y1 + 1)              # un píxel de aire, como todas
    img = img.crop(caja)
    return con_ancla(img, CAMION_ANCLA[0] - caja[0], CAMION_ANCLA[1] - caja[1])


def tractora(color="roja", rumbo="i+") -> Image.Image:
    """La tractora a un rumbo. Declara su quinta rueda y su morro, en unidades."""
    img = _pieza_camion(_tractora, rumbo, TRACTORA_LARGO, TRACTORA_COLORES[color],
                        TRACTORA_DETALLES.get(color, CROMO))
    img.info["quinta"] = QUINTA
    img.info["morro"] = TRACTORA_LARGO[1]
    return con_ruedas(img)


# **La tractora de terminal**: cabina adelantada y la quinta rueda donde la de siempre.
TERMINAL = material_de((226, 176, 38), "tractora terminal")
TECHO_TERMINAL = material_de((34, 33, 34), "techo terminal")
TERMINAL_LARGO = (-3.0, 2.4)
# Sus faros, en las puntas del parachoques, y los pilotos en la cara de atrás de los
# guardabarros.
TERMINAL_FAROS = [[2.45, s * 1.16, 2.7] for s in (-1, 1)]
TERMINAL_PILOTOS = [[-2.9, s * 1.2, 3.45] for s in (-1, 1)]


def _tractora_terminal(rm, mat=None):
    mat = mat or TERMINAL
    # El bastidor corto y la quinta rueda, en oscuro: en gris se leía como un bloque.
    for y in (-0.55, 0.55):
        rm.caja(-2.9, 2.0, y - 0.25, y + 0.25, 1.2, 2.4, CHASIS, -0.8)
    rm.caja(QUINTA - 0.7, QUINTA + 0.7, -1.0, 1.0, 2.4, 2.9, CHASIS, -0.6)
    # Un eje detrás, con ruedas dobles y su guardabarros negro, y el de dirección.
    for s in (-1, 1):
        rm.doble(-2.0, s)
        rm.caja(-2.9, -1.1, *sorted((s * 0.85, s * 1.5)), 3.3, 3.6, NEUMATICO)
        rm.rueda(1.25, *sorted((s * 0.95, s * 1.4)), 1.7)
    # El escape de pie tras la cabina.
    rm.tubo(-0.25, -1.1, 3.0, 9.4, CHASIS)

    # La cabina, con el parabrisas de una sola banda: partido salía un damero.
    def frente(a, b, t):
        if 0.55 < b < 0.92 and 0.08 < a < 0.92:
            return cr(VIDRIO, 4 if b > 0.82 else 2)

    def puerta(a, b, t):
        if 0.55 < b < 0.88 and 0.15 < a < 0.6:
            return cr(VIDRIO, 2)
    rm.caja(-0.1, 2.3, -1.4, 1.4, 2.3, 8.2, mat,
            det={"frente": frente, "izq": puerta, "der": puerta})
    # El techo, con su propio negro (con el de las ruedas salía gris), y sin alerón.
    rm.caja(0.0, 2.2, -1.32, 1.32, 8.2, 8.6, TECHO_TERMINAL, -1)
    # El parachoques, negro y a todo lo ancho, con los dos faros en las puntas; y en punto,
    # que en las diagonales no salían. Los pilotos, en la trasera de los guardabarros.
    rm.caja(2.3, 2.45, -1.45, 1.45, 1.5, 3.1, NEUMATICO, -0.3,
            det={"frente": lambda a, b, t: FARO if b > 0.45 and (a < 0.2 or a > 0.8)
                 else None})
    rm.luces(TERMINAL_FAROS, TERMINAL_PILOTOS, FARO, PILOTO)
    # Los espejos, sueltos en las esquinas de delante, por fuera de la cabina.
    for s in (-1, 1):
        rm.caja(2.05, 2.2, *sorted((s * 1.42, s * 1.65)), 5.6, 7.0, NEUMATICO)


def tractora_terminal(rumbo="i+", mat=None) -> Image.Image:
    """La tractora de terminal (la de mover remolques en un puerto o un almacén) a un rumbo,
    con lo mismo que declara la de siempre. Con `mat`, la cabina de otro color."""
    img = _pieza_camion(_tractora_terminal, rumbo, TERMINAL_LARGO, mat)
    img.info["quinta"] = QUINTA
    img.info["morro"] = TERMINAL_LARGO[1]
    return con_ruedas(img)


def remolque(rumbo="i+", color=None) -> Image.Image:
    """El remolque, vacío. Declara su cama (px) y su pivote (unidades). Con `color`, uno de
    `REMOLQUE_COLORES` (vacío: todos con el bastidor gris)."""
    img = _pieza_camion(_remolque, rumbo, REMOLQUE_LARGO,
                        *REMOLQUE_COLORES.get(color, (BASTIDOR, CROMO)))
    img.info["cama"] = (0, -CAMA_Z)
    img.info["pivote"] = PIVOTE
    return con_ruedas(img)


def contenedor_rumbo(col, rumbo="der") -> Image.Image:
    """El contenedor del remolque, de un material (`"azul"`, `"teja"`, `"verde"`…) o de una
    librea (`LIBREAS`): en los ejes, el dibujado en el lienzo (`contenedor_patio`); en las
    diagonales, en 3D de raster."""
    dibujo = None
    if col in LIBREAS:
        if rumbo in ("i+", "i-", "j+", "j-"):
            return contenedor_librea(col, rumbo[0])
        L = LIBREAS[col]
        col = L["cuerpo"]
        dibujo = (rumbo, *_mapa_dibujo(L["dibujo"], L["colores"], L.get("derechas", ())), True)
    if rumbo in ("i+", "i-", "j+", "j-"):
        return contenedor_patio(col, rumbo[0])
    return con_papel(_pieza_camion(_contenedor_raster, rumbo, None, col, dibujo, sombra=False))


# **Dos libreas de adorno**: no cuentan nada.
LIBREAS = {
    "tentaculo": {
        "cuerpo": material_de((146, 54, 172), "contenedor tentaculo"),
        # Las ventosas, derechas: pegadas a la caída se leen como un «3».
        "dibujo": (".....",
                   "kk.kk",
                   ".....",
                   ".....",
                   ".....",
                   ".....",
                   "....."),
        "derechas": ((0, 2, (".l.",
                             "ldl")),
                     (0, 4, (".ll.",
                             "lddl",
                             ".ll."))),
        "colores": {"k": NEGRO, "l": (122, 222, 62, 255), "d": (30, 118, 44, 255)},
    },
    "sonrisa": {
        "cuerpo": material_de((222, 218, 210), "contenedor sonrisa"),
        # La boca, una fila sobre el pie, o se pierde.
        "dibujo": ("...........",
                   "..m.....m..",
                   "..m..n..m..",
                   "m.........m",
                   "mm.m.m.m.mm",
                   ".mmmmmmmmm.",
                   "..........."),
        "colores": {"m": (52, 30, 62, 255), "n": (232, 112, 76, 255)},
    },
}


def _dibujo_cara(img, caja, eje, dibujo, colores, derechas=()):
    """Un dibujo en el centro del costado largo, **siguiendo la cara**, como `_g_git()`, y
    encima `derechas`, sin seguir la caída."""
    W, S, E, h = caja["W"], caja["S"], caja["E"], caja["alto"]
    A, paso, par = (W, 1, 0) if eje == "i" else (S, -1, 1)
    centro = ((W[0] + S[0]) if eje == "i" else (S[0] + E[0])) // 2
    px = img.load()
    ancho = len(dibujo[0])
    # Debajo, la chapa lisa.
    sitio = []
    for c in range(-1, ancho + 1):
        x = centro - ancho // 2 + c
        pie = A[1] + paso * ((x - A[0] + par) // 2)
        sitio += [(x, pie - h + 1 + f) for f in range(len(dibujo))]
    tonos = [px[q] for q in sitio if px[q][3]]
    dos = sorted(set(tonos), key=tonos.count, reverse=True)[:2]
    liso = max(dos, key=lambda c: sum(c[:3]))
    for q in sitio:
        if px[q][3]:
            px[q] = liso
    for c in range(ancho):
        x = centro - ancho // 2 + c
        pie = A[1] + paso * ((x - A[0] + par) // 2)
        for f, fila in enumerate(dibujo):
            if fila[c] in colores:
                px[x, pie - h + 1 + f] = colores[fila[c]]
    for dc, df, trozo in derechas:
        x0 = centro + dc - len(trozo[0]) // 2
        xm = centro + dc
        pie = A[1] + paso * ((xm - A[0] + par) // 2)
        for f, fila in enumerate(trozo):
            for c, k in enumerate(fila):
                if k in colores:
                    px[x0 + c, pie - h + 1 + df + f] = colores[k]


def contenedor_librea(clave, eje="i") -> Image.Image:
    """Un contenedor de adorno con librea (`LIBREAS`), como `contenedor_patio()`."""
    L = LIBREAS[clave]
    img = Image.new("RGBA", (44, 32), NADA)
    caja = caja_contenedor_eje(img, 22, 22, L["cuerpo"], eje)
    _dibujo_cara(img, caja, eje, L["dibujo"], L["colores"], L.get("derechas", ()))
    a_su_silueta(img, [caja])
    return con_papel(con_ancla(img, 22, 22))
