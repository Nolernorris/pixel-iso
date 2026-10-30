"""**El lápiz**: la paleta, las rampas, el tramado, el contorno y las piezas sueltas de
dibujo (suelos, calle, árboles, farola) en las que se apoya `kit.py`.

Sacado del generador de sprites de Guremu City, **copiado tal cual pinta**: lo que se ha
quitado es lo propio de la ciudad (las fichas de donde salían los colores de sus edificios,
la noche y sus registros de luces, los rotativos). Los vehículos están aparte, en
`vehiculos.py` y `coches.py`. Se usa como
`import dibujo as g`, igual que allí.

La técnica, que es lo que da el aire de tycoon clásico:

  1. **Rampas largas.** Cada material son seis tonos, no tres, con las sombras tirando a
     azul frío y las luces a crema cálida (`rampa_de`, `cr(mat, 0..5)`).
  2. **Tramado.** Entre dos tonos no hay un corte limpio sino un damero Bayer 4x4
     (`tono_tramado(mat, 3.4, x, y)`): un tono con decimales.
  3. **Textura de material.** Hiladas, tablas, nervios, paneles (`_tex`, `TEXTURA`).
  4. **Contorno oscuro de 1 px**, una sola vez y al final (`contorno`).

Luz siempre del mismo lado: cara izquierda clara, derecha en sombra, tejado el más claro.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw


# ------------------------------------------------------------------ el apagón
# Un interruptor y no un parámetro: `g.SIN_LUZ = True` y las ventanas y farolas salen apagadas.
SIN_LUZ = False


def hay_luz(encendida=True) -> bool:
    """¿Se enciende esto? Con el apagón en pie, nada se enciende. **Todo** lo que da luz pasa
    por aquí, o no se apagará."""
    return bool(encendida) and not SIN_LUZ


# ------------------------------------------------------------------ medidas y paleta
ANCHO, ALTO = 64, 32
MX, MY = ANCHO // 2, ALTO // 2

NADA = (0, 0, 0, 0)
NEGRO = (26, 24, 22, 255)

# Hacia dónde tiran las sombras (azul noche, no negro) y las luces; el techo, bajo.
SOMBRA = (26, 30, 52)
LUZ = (238, 230, 202)

VENTANA_ON = (255, 226, 122, 255)
VENTANA_OFF = (56, 66, 88, 255)
CRISTAL = (92, 112, 140, 255)

# Material: color base y qué textura lleva la pared.
MAT = {
    "hierba":   ((98, 142, 68), "mota"),
    "tierra":   ((146, 112, 76), "mota"),
    "asfalto":  ((138, 134, 126), "mota"),
    "arena":    ((184, 166, 122), "mota"),
    "agua":     ((78, 128, 184), "liso"),
    "hormigon": ((150, 146, 138), "panel"),
    "ladrillo": ((156, 98, 72), "hiladas"),
    "madera":   ((140, 106, 70), "tablas"),
    "teja":     ((150, 74, 62), "hiladas"),
    "metal":    ((124, 142, 164), "nervio"),
    "acero":    ((102, 110, 122), "nervio"),
    "pizarra":  ((82, 90, 104), "hiladas"),
    "camion":   ((182, 72, 54), "liso"),
    "cabina":   ((184, 180, 172), "liso"),
    "blanco":   ((188, 184, 176), "panel"),
    "verde":    ((100, 146, 88), "panel"),
    "azul":     ((88, 126, 176), "panel"),
    "cobre":    ((172, 126, 78), "panel"),
    "bronce":   ((150, 112, 62), "panel"),
    # Malla de obra, lisa a propósito.
    "lona":     ((176, 182, 170), "liso"),
    # Balizamiento: más naranja que una teja, o no se distingue de un depósito a franjas.
    "senal":    ((196, 76, 50), "liso"),
    # Madera oscura y casi negro: negro puro se come el contorno.
    "nogal":    ((104, 70, 48), "tablas"),
    "carbon":   ((44, 40, 40), "hiladas"),
}

PAL: dict[str, tuple] = {}
SUCIO: dict[str, tuple] = {}

# Con qué se ensucia cada material y cada cuánto: colores distintos, no dos tonos del mismo.
CONTAMINA = {
    "ladrillo": ((96, 92, 92), 11),
    "teja":     ((86, 84, 88), 9),
    "hormigon": ((126, 112, 92), 13),
    "blanco":   ((132, 126, 116), 17),
    "arena":    ((124, 116, 98), 13),
    "madera":   ((98, 92, 84), 11),
    "metal":    ((116, 112, 104), 13),
    "acero":    ((98, 100, 108), 13),
    "pizarra":  ((92, 88, 84), 11),
    "verde":    ((104, 104, 92), 13),
    "lona":     ((150, 156, 146), 19),
    "azul":     ((104, 108, 112), 13),
    "cobre":    ((112, 102, 88), 13),
    "bronce":   ((108, 98, 82), 13),
    "tierra":   ((112, 104, 88), 9),
    "hierba":   ((124, 116, 72), 11),
}


def _mezclar(a, b, k):
    return tuple(int(round(a[i] + (b[i] - a[i]) * k)) for i in range(3))


def rampa_de(rgb, n=6) -> tuple:
    """Seis tonos de un material: de sombra fría a luz cálida."""
    tonos = []
    for i in range(n):
        t = i / (n - 1)
        if t < 0.5:
            col = _mezclar(rgb, SOMBRA, (0.5 - t) * 2 * 0.74)
        else:
            col = _mezclar(rgb, LUZ, (t - 0.5) * 2 * 0.36)
        tonos.append(col)
    return tuple(tonos)


for _nombre, (_base, _tex) in MAT.items():
    PAL[_nombre] = rampa_de(_base)
    if _nombre in CONTAMINA:
        SUCIO[_nombre] = rampa_de(_mezclar(_base, CONTAMINA[_nombre][0], 0.55))

TEXTURA = {k: v[1] for k, v in MAT.items()}

# Índices de la rampa para cada cara. Así se escribe c(mat, 0/1/2) como siempre.
IZQ, TECHO, DER = 3, 5, 1

# Cuánto se hunde una fachada de arriba abajo, en pasos de la rampa.
FONDO = 1.2


def cr(mat: str, i: int) -> tuple:
    """Tono i (0 el más oscuro, 5 el más claro) de la rampa del material."""
    r, g, b = PAL[mat][max(0, min(len(PAL[mat]) - 1, i))]
    return (r, g, b, 255)


def c(mat: str, cara: int) -> tuple:
    return cr(mat, (IZQ, TECHO, DER)[cara])


def _azar(x: int, y: int) -> int:
    """Ruido fijo por posición: el mismo (x, y) da siempre el mismo número."""
    h = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return (h >> 8) & 0xFFFF


def mancha(mat: str, tono: int, x: int, y: int, dosis: float = 1.0):
    """Mancha de otro color en (x, y), o None si ahí no toca. Por ruido: una cuenta de
    módulo la deja en diagonales. `dosis` sube o baja la frecuencia."""
    paso = CONTAMINA.get(mat, (None, 0))[1]
    if not paso or mat not in SUCIO:
        return None
    if _azar(x, y) % max(2, round(paso / dosis)) != 0:
        return None
    r2, g2, b2 = SUCIO[mat][max(0, min(5, tono))]
    return (r2, g2, b2, 255)


# ------------------------------------------------------------------ tramado
BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


def tramado(x: int, y: int, k: float) -> bool:
    """True si en (x, y) toca el tono claro. k de 0 a 1."""
    return BAYER[y & 3][x & 3] < k * 16


# --------------------------------------------------------------- geometría
def fila(y: int, w: int = ANCHO) -> tuple:
    alto = w // 2
    mitad = alto // 2
    ww = 4 * (y + 1) if y < mitad else 4 * (alto - y)
    return MX - ww // 2, ww


def y_izq(x: int, cy: int, w: int = ANCHO) -> int:
    return cy + (x - (MX - w // 2)) // 2


def y_der(x: int, cy: int, w: int = ANCHO) -> int:
    return cy + (w // 4 - 1) - (x - MX) // 2


def y_base(x: int, cy: int, w: int = ANCHO) -> int:
    return y_izq(x, cy, w) if x < MX else y_der(x, cy, w)


def y_fondo(x: int, cy: int, w: int = ANCHO) -> int:
    """Borde de atrás (W a N a E). El de delante baja hacia la esquina sur y cualquier
    muro apoyado en él sale en forma de uve."""
    if x < MX:
        return cy - (x - (MX - w // 2)) // 2
    return cy - (w // 4 - 1) + (x - MX) // 2


def rango(w: int = ANCHO) -> range:
    return range(MX - w // 2, MX + w // 2)


def lienzo(extra: int = 0) -> Image.Image:
    return Image.new("RGBA", (ANCHO, ALTO + extra), NADA)


def punto(px, img, x, y, col):
    if 0 <= x < img.size[0] and 0 <= y < img.size[1]:
        px[x, y] = col


def _tex(mat, x, y, dentro):
    """Desplazamiento de tono por la textura del material. Juntas espaciadas a propósito:
    una cada 2 px se lee como ruido."""
    t = TEXTURA.get(mat, "liso")
    if t == "hiladas":
        if dentro % 5 == 0:                            # tendel
            return -1
        if (dentro // 5 % 2 == 0) and (x % 9 == 0):    # llaga, trabada
            return -1
    elif t == "tablas":
        if x % 6 == 0:
            return -1
    elif t == "nervio":
        if x % 4 == 0:
            return 1
    elif t == "panel":
        if dentro % 11 == 0 or x % 13 == 0:
            return -1
    return 0


def con_ancla(img: Image.Image, ax, ay) -> Image.Image:
    """Marca en la pieza **dónde se apoya**: el centro de su planta, en píxeles. Un vehículo
    no se apoya en el ancla genérica."""
    img.info["ancla"] = (int(ax), int(ay))
    return img


def vecino(m):
    """Qué píxeles tienen **alguno de sus cuatro vecinos** en la máscara `m` (sin salirse del
    lienzo): lo que los contornos miraban píxel a píxel, de una vez con numpy."""
    v = np.zeros_like(m)
    v[:, :-1] |= m[:, 1:]
    v[:, 1:] |= m[:, :-1]
    v[:-1, :] |= m[1:, :]
    v[1:, :] |= m[:-1, :]
    return v


def contorno(img: Image.Image) -> Image.Image:
    """El perfil negro: cada píxel transparente junto a uno opaco. Pinta en la misma imagen."""
    a = np.asarray(img.getchannel("A"))
    px = img.load()
    for y, x in zip(*np.nonzero((a == 0) & vecino(a > 128))):
        px[int(x), int(y)] = NEGRO
    return img


def tono_tramado(mat: str, t: float, x: int, y: int) -> tuple:
    """Color del tono decimal `t`: los dos tonos vecinos de la rampa, tramados píxel a píxel."""
    bajo = int(max(0.0, t) // 1)
    return cr(mat, bajo + (1 if tramado(x, y, t - bajo) else 0))


def _tono_tubo(nu, nv, nz):
    """Tono de un punto de un cilindro tumbado, según hacia dónde mire su superficie: la luz
    de siempre, en fórmula y no en tres bandas."""
    return max(0.0, min(5.0, 3.1 + 1.9 * nz - 1.6 * nu - 0.6 * nv))


def material_de(rgb, clave=None) -> str:
    """Registra un color suelto como material, con su rampa de seis tonos, y
    devuelve su nombre."""
    clave = clave or "tmp_%02x%02x%02x" % tuple(rgb[:3])
    if clave not in PAL:
        PAL[clave] = rampa_de(tuple(rgb[:3]))
        TEXTURA[clave] = "liso"
    return clave


# **Una unidad de planta son dos píxeles de alto** en todo lo redondo: con la altura estirada
# de los edificios, un plato sale huevo.
Z_REDONDO = 2


def _norm(a):
    n = math.sqrt(sum(c * c for c in a)) or 1.0
    return tuple(c / n for c in a)


# ------------------------------------------------------------------ suelos y calle
def suelo(mat: str, semilla: int = 0) -> Image.Image:
    """Suelo con matas de dos o tres píxeles, no con moteado suelto: liso, deja el resto
    flotando."""
    img = lienzo()
    px = img.load()
    for y in range(ALTO):
        x0, ww = fila(y)
        for x in range(x0, x0 + ww):
            px[x, y] = cr(mat, 3)
    for n in range(26):                                # matas claras y oscuras
        h = (n * 37 + semilla * 101) % 1021
        cx = 6 + h % (ANCHO - 12)
        cy = 4 + (h // 7) % (ALTO - 8)
        if abs(cx - MX) * 0.5 + abs(cy - MY) > MY - 2:  # dentro del rombo
            continue
        tono = 4 if n % 3 else 2
        for dx, dy in ((0, 0), (1, 0), (0, 1), (2, 0), (1, 1)):
            if (n + dx + dy) % 5 != 4:
                punto(px, img, cx + dx, cy + dy, cr(mat, tono))
    return img


# La línea del eje dentro de una casilla: el i cruza de NO a SE, el j de NE a SO.
def _linea_eje(x, eje):
    return x // 2 if eje == "i" else (ANCHO - x) // 2


# **Media calzada**, en unidades de planta: sale de por dónde circulan, y con cuatro los
# coches pisarían la hierba.
CALZADA = 5
# La pintura de la calzada: una sola para el borde, el eje y las plazas.
PINTURA = (232, 224, 194, 255)


def _plan(x, y):
    """De píxel de la casilla a unidades de planta desde su centro (`punto_plan` al revés)."""
    a, b = (x - MX) / 2, y - MY
    return (a + b) / 2, (b - a) / 2


def _en_calzada(u, v, lados):
    """Calzada es **lo que está a menos de media anchura del eje de alguna salida**: de ahí
    salen las quince, con los codos redondeados."""
    return any(math.hypot(max(0.0, u) if p == "i-" else -min(0.0, u) if p == "i+" else u,
                          max(0.0, v) if p == "j-" else -min(0.0, v) if p == "j+" else v)
               <= CALZADA for p in lados)


def calle(lados=("i-", "i+")) -> Image.Image:
    """Casilla de calzada, **una capa encima del suelo**. `lados` dice **por qué lados sigue
    la calle**."""
    lados = tuple(lados)
    img = lienzo()
    px = img.load()
    # Primero qué es calzada, por píxel: la línea del borde necesita saber quién tiene al lado.
    calzada = {}
    for y in range(ALTO):
        x0, ww = fila(y)
        for x in range(x0, x0 + ww):
            calzada[(x, y)] = _en_calzada(*_plan(x, y), lados)
    for (x, y), si in calzada.items():
        if not si:
            continue
        # Línea donde **la casilla sigue y la calzada no**; contra el borde, no.
        canto = any(calzada.get(v) is False
                    for v in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
        px[x, y] = (PINTURA if canto
                    else cr("asfalto", 2 if (x * 13 + y * 7) % 19 else 3))

    # Recta es tener **dos puertas y opuestas**; en una intersección, el eje se corta.
    recta = len(lados) == 2 and lados[0][0] == lados[1][0]
    for p in lados:
        eje = p[0]
        # En el eje i la `-` es la mitad izquierda; en el j, al revés (`j-` sube a la derecha).
        izquierda = (p == "i-") if eje == "i" else (p == "j+")
        desde, hasta = (MX // 2, MX) if izquierda else (MX, ANCHO - MX // 2)
        for x in range(desde, hasta):
            if not recta and abs(x - MX) < 7:
                continue                               # el centro de una intersección
            if (x // 4) % 2 == 0:
                punto(px, img, x, _linea_eje(x, eje), PINTURA)
    return img


# ------------------------------------------------------------------ parcelas de varias casillas
PASO = 16


def parcela(cols: int, filas: int, extra: int = 0):
    """Lienzo para una parcela de cols x filas casillas. Devuelve (imagen, ox, oy)."""
    W = (cols + filas) * MX
    H = (cols + filas) * MY + extra
    return Image.new("RGBA", (W, H), NADA), filas * MX, extra + MY


def celda(ox, oy, i, j):
    """Centro en pantalla de la casilla (i, j) de una parcela."""
    return ox + (i - j) * MX, oy + (i + j) * MY


def ancla_parcela(img, ox, oy, cols, filas) -> Image.Image:
    """Contornea la pieza y le marca el ancla: el centro de su **casilla de delante**, no la
    mitad de su ancho, que en una parcela no cuadrada la desplaza media casilla."""
    return con_ancla(contorno(img), *celda(ox, oy, cols - 1, filas - 1))


def suelo_parcela(img, ox, oy, cols, filas, mat="hormigon", borde=False):
    for i in range(cols):
        for j in range(filas):
            x, y = celda(ox, oy, i, j)
            img.alpha_composite(suelo(mat, i * 3 + j), (x - MX, y - MY))
    if borde:
        # Nada de valla: queda detrás de los volúmenes y no se ve. En su lugar, el
        # pavimento con su borde, que sí asoma alrededor y ata las piezas a la parcela.
        px = img.load()
        for i in range(cols):
            x, y = celda(ox, oy, i, filas - 1)
            for k in range(MX):
                punto(px, img, x - MX + k, y + MY - k // 2, cr(mat, 4))
        for j in range(filas):
            x, y = celda(ox, oy, cols - 1, j)
            for k in range(MX):
                punto(px, img, x + k, y + k // 2, cr(mat, 1))


# ------------------------------------------------------------------ mobiliario
def farola(px, img, x, suelo_y, alt=22):
    for y in range(suelo_y - alt, suelo_y):
        punto(px, img, x, y, cr("acero", 3))
        punto(px, img, x + 1, y, cr("acero", 1))
    for dx in range(-2, 4):
        punto(px, img, x + dx, suelo_y - alt - 1, cr("acero", 2))
        punto(px, img, x + dx, suelo_y - alt, VENTANA_ON if hay_luz() else VENTANA_OFF)


def arbol(px, img, x, suelo_y, alto=12):
    """Copa redonda y alta, no aplastada: una elipse ancha se lee como sombrilla."""
    for y in range(suelo_y - alto, suelo_y):
        punto(px, img, x, y, cr("madera", 1))
        punto(px, img, x + 1, y, cr("madera", 0))
    cx, cyy = x, suelo_y - alto - 3
    for dy in range(-7, 5):
        for dx in range(-6, 8):
            d = dx * dx * 1.25 + dy * dy
            if d <= 34:
                tono = 4 if (dx < 1 and dy < 0) else 2
                if 22 < d <= 34:
                    tono = 1                           # borde de la copa, en sombra
                elif tramado(cx + dx, cyy + dy, 0.45):
                    tono = 3
                punto(px, img, cx + dx, cyy + dy, cr("verde", tono))


def banco(px, img, x0, suelo_y, an=12):
    for i, x in enumerate(range(x0, x0 + an)):
        y = suelo_y - i // 2
        for d in range(3):
            punto(px, img, x, y - 5 + d, cr("madera", 4 - d))
        punto(px, img, x, y - 1, cr("madera", 1))


def papelera(px, img, x, suelo_y):
    for xx in range(x, x + 5):
        for y in range(suelo_y - 7, suelo_y):
            punto(px, img, xx, y, cr("verde", 3 if xx < x + 3 else 1))
    for xx in range(x - 1, x + 6):
        punto(px, img, xx, suelo_y - 8, cr("verde", 5))


def seto(px, img, x0, suelo_y, an=14):
    for i, x in enumerate(range(x0, x0 + an)):
        y = suelo_y - i // 2
        for d in range(6):
            tono = 4 if tramado(x, y - d, 0.45) else 2
            punto(px, img, x, y - d, cr("verde", tono))


# ------------------------------------------------------------------ vegetación
HOJA = {"pino": (56, 94, 60), "hoja": (112, 152, 80), "olivo": (128, 146, 104),
        "lavanda": (112, 128, 104)}
FLORES = ((236, 232, 220), (238, 200, 74), (156, 120, 196), (214, 98, 86))
LAVANDA_FLOR = ((150, 118, 196), (122, 92, 168))


def _copa(px, img, cx, cy, rx, ry, mat, semilla=0, luz=0.0):
    """Una masa de hojas, a manchas de dos píxeles: lisa se lee como un globo."""
    for dy in range(-int(ry) - 1, int(ry) + 2):
        for dx in range(-int(rx) - 1, int(rx) + 2):
            # El borde, mordido por las hojas: no es una elipse limpia.
            mordisco = (_azar(cx + dx + semilla, cy + dy) % 100) / 100 * 0.35
            d = (dx / rx) ** 2 + (dy / ry) ** 2
            if d > 1.0 - mordisco * (d > 0.6):
                continue
            t = 2.9 + luz - 1.5 * dx / rx - 1.3 * dy / ry - 1.0 * d
            grano = (_azar((cx + dx) // 2 + semilla, (cy + dy) // 2) % 100) / 100
            t += (grano - 0.5) * 1.4
            punto(px, img, cx + dx, cy + dy, cr(mat, max(0, min(5, round(t)))))


def _tronco(px, img, x, suelo_y, alto, ancho=2):
    for y in range(suelo_y - alto, suelo_y + 1):
        punto(px, img, x, y, cr("madera", 2))
        if ancho > 1:
            punto(px, img, x + 1, y, cr("madera", 0))
    punto(px, img, x - 1, suelo_y, cr("madera", 1))
    punto(px, img, x + ancho, suelo_y, cr("madera", 0))


# A True, los árboles salen sin su sombra en la hierba.
_SIN_SOMBRA = False


def _sombra_arbol(img, x, suelo_y, r):
    """La sombra en la hierba, hacia la derecha. Se compone, no se pinta: con `ImageDraw`
    deja un agujero negro."""
    if _SIN_SOMBRA:
        return
    capa = Image.new("RGBA", img.size, NADA)
    ImageDraw.Draw(capa).ellipse([x - r + 2, suelo_y - r // 3, x + r + 3,
                                  suelo_y + r // 3], fill=(0, 0, 0, 60))
    img.alpha_composite(capa)


def pino(px, img, x, suelo_y, alto=16, semilla=0):
    """Un pino joven: tronco corto y copa espesa y oscura, más ancha abajo, a pisos."""
    mat = material_de(HOJA["pino"], "pino")
    _sombra_arbol(img, x, suelo_y, 5)
    _tronco(px, img, x, suelo_y, 4)
    pisos = 3
    for k in range(pisos):
        f = 1 - k / pisos
        cy = suelo_y - 5 - k * (alto - 6) // pisos
        _copa(px, img, x + 1, cy, 2 + 4 * f, 2 + 2 * f, mat, semilla + k, luz=0.3 * k)
    _copa(px, img, x + 1, suelo_y - alto + 1, 2, 2, mat, semilla + 9, luz=0.8)


def arbol_hoja(px, img, x, suelo_y, alto=22, semilla=0, mat_hoja="hoja"):
    """Un árbol de hoja alto: tronco con horquilla y copa abierta, de masas sueltas."""
    mat = material_de(HOJA[mat_hoja], mat_hoja)
    _sombra_arbol(img, x, suelo_y, 7)
    _tronco(px, img, x, suelo_y, alto - 6)
    cima = suelo_y - alto
    for k, sx in enumerate((-1, 1)):                       # la horquilla
        for t in range(5):
            punto(px, img, x + sx * (t // 2) + (1 if sx > 0 else 0),
                  suelo_y - alto + 9 - t, cr("madera", 2 - k))
    masas = ((-4, 5, 5, 4, -0.6), (5, 4, 5, 4, -0.5), (0, 0, 6, 5, 0.0),
             (-5, -1, 4, 3, 0.3), (4, -2, 4, 4, 0.4), (0, -5, 4, 3, 0.8))
    for n, (dx, dy, rx, ry, luz) in enumerate(masas):
        if (semilla + n) % 5 == 4 and n in (3, 4):
            continue                                       # que no salgan todos iguales
        _copa(px, img, x + dx, cima + 6 + dy, rx, ry, mat, semilla + n * 7, luz)


def mata(px, img, x, y, lavanda=False, semilla=0):
    """Una mata baja; con `lavanda`, las espigas moradas por encima."""
    mat = material_de(HOJA["lavanda" if lavanda else "pino"], "lavanda" if lavanda
                      else "pino")
    _copa(px, img, x, y - 2, 3, 2, mat, semilla, luz=0.4)
    if lavanda:
        for k in range(-2, 4, 2):
            if (_azar(x + k, y + semilla) % 3) == 0:
                continue
            punto(px, img, x + k, y - 4, LAVANDA_FLOR[0])
            punto(px, img, x + k, y - 3, LAVANDA_FLOR[1])


# ----------------------------------------------- más árboles

HOJA.update({"roble": (72, 108, 56), "arce": (206, 112, 52), "arce rojo": (182, 72, 48)})
ESPECIES = ("roble", "pino", "arce", "olivo")


def roble(px, img, x, suelo_y, alto=20, semilla=0):
    """Un roble: tronco grueso y corto, y una copa más ancha que alta, de masas oscuras."""
    mat = material_de(HOJA["roble"], "roble")
    _sombra_arbol(img, x, suelo_y, 9)
    _tronco(px, img, x, suelo_y, alto - 8)
    _tronco(px, img, x - 1, suelo_y, alto - 10, ancho=1)      # el tronco, más grueso
    cima = suelo_y - alto
    masas = ((-7, 5, 5, 3, -0.6), (7, 5, 5, 3, -0.5), (0, 4, 7, 4, -0.1),
             (-5, 0, 5, 4, 0.3), (5, 0, 5, 4, 0.3), (0, -2, 6, 3, 0.8))
    for n, (dx, dy, rx, ry, luz) in enumerate(masas):
        _copa(px, img, x + dx, cima + 6 + dy, rx, ry, mat, semilla + n * 7, luz)


def arce(px, img, x, suelo_y, alto=20, semilla=0):
    """Un arce en otoño: tronco esbelto y copa redonda en naranja, con alguna masa roja."""
    mat = material_de(HOJA["arce"], "arce")
    rojo = material_de(HOJA["arce rojo"], "arce rojo")
    _sombra_arbol(img, x, suelo_y, 7)
    _tronco(px, img, x, suelo_y, alto - 7)
    cima = suelo_y - alto
    masas = ((-4, 4, 5, 4, -0.5, rojo), (4, 4, 5, 4, -0.4, mat), (0, 1, 6, 5, 0.1, mat),
             (-2, -3, 4, 3, 0.6, mat), (3, -2, 3, 3, 0.5, rojo), (0, -5, 3, 2, 0.9, mat))
    for n, (dx, dy, rx, ry, luz, m) in enumerate(masas):
        if (semilla + n) % 3 == 2 and m == rojo:
            m = mat                                       # no todos con el mismo rojo
        _copa(px, img, x + dx, cima + 7 + dy, rx, ry, m, semilla + n * 7, luz)


def _olivo(px, img, x, suelo_y, alto=16, semilla=0):
    arbol_hoja(px, img, x, suelo_y, alto, semilla, mat_hoja="olivo")
