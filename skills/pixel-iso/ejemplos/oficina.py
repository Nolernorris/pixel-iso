"""Una oficina por salas, hecha con el kit: el ejemplo resuelto de la skill.

Una casa de muñecas en corte: paredes altas solo en los dos lados del fondo (u = 0, la de
atrás-izquierda, y v = V, la de atrás-derecha), murete bajo delante y medias paredes bajas
entre salas. 16 unidades por casilla; `E.S(u, v, z)`: x = 2u + 2v, y = u - v - z.

Se lanza desde cualquier sitio (`python ruta/a/oficina.py`) y deja `oficina.png` y
`oficina_x3.png` en la carpeta desde donde se lanza.
"""
import math
import os
import sys

# El kit vive en `../kit/`, al lado de esta carpeta: se importa desde ahí, se lance de donde se lance.
KIT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kit")
sys.path.insert(0, KIT)
sys.dont_write_bytecode = True

from PIL import Image  # noqa: E402

import dibujo as g  # noqa: E402
import kit as k  # noqa: E402

AQUI = os.getcwd()                       # la PNG, donde se lance

U, V = 144, 96          # 9 x 6 casillas de casa; la hierba, una casilla de margen
H = 26                  # las paredes del fondo, en px
FRANJA = 60             # la fila de salas del fondo derecho empieza en v = 60
IZQ = 30                # la de salas del fondo izquierdo acaba en u = 30


def M(rgb, nombre):
    return g.material_de(rgb, "oficina " + nombre)


def tt(mat, t, X, Y):
    return g.tono_tramado(mat, t, X, Y)


# ---------------------------------------------------------------- materiales
OSCURO = M((62, 58, 64), "murete")             # muretes, tabiques y el canto de las paredes
CANTO = M((84, 78, 84), "canto")
NUBES = M((128, 146, 172), "pared nubes")
AZULEJO = M((176, 180, 184), "azulejo")
MELOCOTON = M((226, 168, 128), "melocoton")
CREMA = M((206, 196, 150), "crema")
BEIGE = M((214, 194, 156), "rayas beige")
MARRON_R = M((150, 108, 76), "rayas marron")
MARCO_V = M((70, 140, 72), "marco verde")
CRISTAL = M((150, 196, 226), "cristal")

S_GRIS = M((176, 176, 180), "suelo gris")
S_BALDOSA = M((196, 198, 200), "baldosa")
S_DAMERO = M((104, 70, 48), "damero")
S_MADERA = M((150, 104, 64), "madera comedor")
S_BLANCO = M((222, 220, 214), "suelo blanco")
S_ESPIGA = M((214, 190, 146), "espiga")
LOSA = M((150, 150, 148), "losa")

MESA = M((142, 92, 54), "mesa")
MESA_OSC = M((96, 62, 40), "mesa oscura")
GRIS_CRT = M((170, 168, 160), "crt")
TURQUESA = M((52, 178, 172), "turquesa")
AZUL_CLARO = M((140, 196, 228), "silla azul")
MORADO = M((122, 64, 156), "manta")
BLANCO = M((236, 234, 228), "blanco")
ROSA = M((240, 140, 170), "rosa")
NARANJA = M((222, 118, 44), "alfombra")
AZUL_ALF = M((58, 104, 176), "alfombra azul")
SOFA = M((128, 130, 136), "sofa")
ACERO = "acero"
AMARILLO = M((232, 190, 52), "maceta amarilla")
BARRO = M((176, 98, 64), "barro")
HOJA = M((70, 130, 66), "hoja")
HOJA2 = M((54, 110, 72), "hoja oscura")

PANTALLA = (110, 206, 214, 255)
PANTALLA_OSC = (40, 120, 140, 255)
FLOR_NAR = ((246, 130, 40, 255), (255, 176, 70, 255))
FLOR_AZUL = ((70, 110, 220, 255), (130, 170, 250, 255))


# ---------------------------------------------------------------- piezas sueltas
def caja(E, u, v, a, b, z0, h, mat, techo=None, sube=0.0, tope=4.6):
    tm = techo or mat
    E.caja(u, v, a, b, z0, h, k.liso(mat, sube),
           techo=lambda uu, vv, X, Y: tt(tm, tope, X, Y))


def pinta_lista(filas, colores, ancla):
    img = Image.new("RGBA", (max(len(f) for f in filas), len(filas)), g.NADA)
    px = img.load()
    for y, f in enumerate(filas):
        for x, ch in enumerate(f):
            if ch in colores:
                px[x, y] = colores[ch]
    img.info["ancla"] = ancla
    return img


PIEL = [(232, 190, 152, 255), (196, 140, 100, 255), (132, 88, 60, 255), (240, 204, 170, 255)]


def oscurece(c, f=0.72):
    return tuple(int(x * f) for x in c[:3]) + (255,)


FRENTE = {
    0: ["..hhhhh..", ".hhhhhhh.", ".hfffffh.", "..fefef..", "..fffff..",
        ".sssssss.", "fsssssssf", "fsSsssSsf", ".sssssss.", ".sssssss."],
    1: ["..hhhhh..", ".hhhhhhh.", ".hfffffh.", ".hfefefh.", ".hfffffh.",
        ".hsssssh.", "fsssssssf", "fsSsssSsf", ".sssssss.", ".sssssss."],
    2: [".hhhhhhh.", "hhhhhhhhh", "hhfffffhh", ".hfefefh.", "..fffff..",
        ".sssssss.", "fsssssssf", "fsSsssSsf", ".sssssss.", ".sssssss."],
    3: ["...hhh...", "..hhhhh..", "..hfffh..", "..fefef..", "..fffff..",
        ".sssssss.", "fsssssssf", "fsSsssSsf", ".sssssss.", ".sssssss."],
}
ESPALDA = {
    0: ["...hhh...", "..hhhhh..", "..hhhhh..", "...hhh...", ".sssssss.",
        "sssssssss", "SsssssssS", "SsssssssS", ".sssssss.", ".sssssss."],
    1: ["...hhh...", "..hhhhh..", "..hhhhh..", "..hhhhh..", ".shhhhhs.",
        "sssshssss", "SsssssssS", "SsssssssS", ".sssssss.", ".sssssss."],
    2: ["..hhhhh..", ".hhhhhhh.", ".hhhhhhh.", "..hhhhh..", ".sssssss.",
        "sssssssss", "SsssssssS", "SsssssssS", ".sssssss.", ".sssssss."],
    3: ["....h....", "...hhh...", "..hhhhh..", "..hhhhh..", "...fff...",
        "sssssssss", "SsssssssS", "SsssssssS", ".sssssss.", ".sssssss."],
    4: ["...hhh...", "..hhhhh..", "..hhhhh..", "...fff...", ".sssssss.",
        "sssssssss", "SsssssssS", "SsssssssS", ".sssssss.", ".sssssss."],
}


def persona(pelo, ropa, piel, de_frente, estilo=0):
    """Sentada, 9 x 10: de espaldas (mirando su
    pantalla) o de frente, con la mesa tapándole las piernas."""
    filas = (FRENTE if de_frente else ESPALDA)[estilo]
    return pinta_lista(filas, {"h": pelo, "f": piel, "s": ropa, "S": oscurece(ropa),
                               "e": (40, 28, 26, 255)}, (4, len(filas) - 1))


def silla(E, u, v, mat, respaldo):
    """Asiento de 3 x 3 a z 3,5; `respaldo` en qué canto: 'v-', 'v+', 'u-', 'u+'."""
    for du, dv in ((0.3, 0.3), (2.2, 0.3), (0.3, 2.2), (2.2, 2.2)):
        caja(E, u + du, v + dv, 0.5, 0.5, 0, 3, ACERO)
    caja(E, u, v, 3, 3, 3, 1, mat)
    r = {"v-": (u, v, 3, 0.7), "v+": (u, v + 2.3, 3, 0.7),
         "u-": (u, v, 0.7, 3), "u+": (u + 2.3, v, 0.7, 3)}[respaldo]
    # De espaldas a nosotros (v-), el respaldo más bajo: si no, tapa a quien se sienta.
    caja(E, r[0], r[1], r[2], r[3], 4, 3 if respaldo == "v-" else 4.5, mat)


def mesa(E, u, v, a, b, mat=MESA, z=6, patas=True):
    caja(E, u, v, a, b, z - 1.2, 1.2, mat, sube=-0.4, tope=4.3)
    if patas:
        for du, dv in ((0.4, 0.4), (a - 1.2, 0.4), (0.4, b - 1.2), (a - 1.2, b - 1.2)):
            caja(E, u + du, v + dv, 0.8, 0.8, 0, z - 1.2, mat, sube=-0.8)


def pantalla_en(E, cara):
    """La cara de la pantalla del CRT: marco gris, cristal con su raya de barrido."""
    quiere = {"-v": (0, -1), "+u": (1, 0)}[cara]

    def f(s, z, t, X, Y):
        es = abs(E.normal[0] - quiere[0]) < 0.1 and abs(E.normal[1] - quiere[1]) < 0.1
        if es and 0.6 <= s <= 3.0 and 1 <= z < 4.5:
            return PANTALLA_OSC if int(z) == 1 or s < 1.0 else PANTALLA
        return k.pinta(GRIS_CRT, t, X, Y, z)
    return f


def crt(E, u, v, z, mira):
    """Un monitor de tubo de 3,6 de ancho: `mira` -v (pantalla a la izquierda de pantalla),
    +u (a la derecha) o +v (se le ve la culera)."""
    if mira == "-v":
        E.caja(u, v + 1.4, 2.6, 2.2, z + 0.5, 4, k.liso(GRIS_CRT, -0.4), techo=lambda *a: tt(GRIS_CRT, 4, a[2], a[3]))
        E.caja(u - 0.5, v, 3.6, 1.6, z, 5.5, pantalla_en(E, "-v"), techo=lambda *a: tt(GRIS_CRT, 4.6, a[2], a[3]))
        E.rect(u - 0.3, v - 2.6, 3.2, 1.4, z + 0.05, lambda *a: tt(BLANCO, 3.4, a[2], a[3]))   # teclado
    elif mira == "+u":
        E.caja(u, v, 2.2, 2.6, z + 0.5, 4, k.liso(GRIS_CRT, -0.4), techo=lambda *a: tt(GRIS_CRT, 4, a[2], a[3]))
        E.caja(u + 2.0, v - 0.5, 1.6, 3.6, z, 5.5, pantalla_en(E, "+u"), techo=lambda *a: tt(GRIS_CRT, 4.6, a[2], a[3]))
        E.rect(u + 4.6, v - 0.3, 1.4, 3.2, z + 0.05, lambda *a: tt(BLANCO, 3.4, a[2], a[3]))
    else:                                                # de espaldas: la culera hacia aquí
        E.caja(u, v, 3.6, 1.6, z, 5.5, k.liso(GRIS_CRT), techo=lambda *a: tt(GRIS_CRT, 4.6, a[2], a[3]))
        E.caja(u + 0.5, v - 2.0, 2.6, 2.0, z + 0.5, 4, k.liso(GRIS_CRT, -0.3), techo=lambda *a: tt(GRIS_CRT, 4, a[2], a[3]))


def planta(alto=12, semilla=0, ancho=5):
    def dib(px, img, x, y):
        tallo = (60, 92, 50, 255)
        for d in range(alto - 4):
            g.punto(px, img, x, y - d, tallo)
        n = 3 + alto // 6
        for q in range(n):
            f = q / max(1, n - 1)
            dx = int(round((ancho - 1) * math.sin(q * 2.3 + semilla)))
            cy = y - 3 - int(f * (alto - 5))
            g._copa(px, img, x + dx, cy, 2.6 + (1 - f) * 0.8, 2.0, HOJA if q % 2 else HOJA2, semilla + q * 5, luz=0.3 + f)
    return k.suelto(dib, w=30, h=alto + 14)


def maceta(E, u, v, r, h, mat, alto=12, semilla=0, ancho=4):
    E.cilindro(u, v, r, 0, h, k.liso(mat, 0.3), techo=lambda *a: tt("tierra", 1.5, a[2], a[3]), lados=14)
    vv = u - round(u - v)
    E.sprite(planta(alto, semilla, ancho), u, vv, h)


def flores(E, u, v, colores, maceta_mat=AMARILLO, r=1.8, h=3.0, semilla=0):
    E.cilindro(u, v, r, 0, h, k.liso(maceta_mat, 0.5), techo=lambda *a: tt("tierra", 1.5, a[2], a[3]), lados=14)
    vv = u - round(u - v)
    E.sprite(k.suelto(lambda px, img, x, y: g._copa(px, img, x, y - 2, 3.4, 2.2, HOJA, semilla, 0.6)), u, vv, h)
    for q in range(9):
        a = q * 2.4 + semilla
        rr = 0.4 + (q % 3) * 0.55
        E.punto(u + rr * math.cos(a), v + rr * math.sin(a), h + 3.2 + (q % 2), colores[q % 2], delante=0.4)


# ---------------------------------------------------------------- las paredes
def cartel(s0, z_arriba, filas, colores):
    """Un dibujo de caracteres en una pared: cada carácter media unidad (un píxel de
    ancho) y un píxel de alto, la fila 0 arriba."""
    def f(s, z):
        cx, cy = int((s - s0) * 2), int(z_arriba - z)
        if s >= s0 and z <= z_arriba and 0 <= cy < len(filas) and 0 <= cx < len(filas[cy]):
            ch = filas[cy][cx]
            return colores.get(ch)
        return None
    return f


PINGUINO = cartel(27, 21, ["mmmmmmmm", "mcckkccm", "mckwwkcm", "mckkokcm", "mkkwwkkm", "mkwwwwkm",
                           "mckwwkcm", "mckwwkcm", "mcoccocm", "mmmmmmmm"],
                  {"m": (240, 240, 236, 255), "c": (150, 206, 236, 255), "k": (30, 32, 40, 255),
                   "w": (250, 250, 250, 255), "o": (246, 150, 40, 255)})
MAPA = cartel(60, 20, ["mmmmmmmmmmmmmmmmmmmm", "mbbbbbbbbbbbbbbbbbbm", "mbbggbbbbbbbyyybbbbm",
                       "mbgggbbbbbbyyyyybbbm", "mbbgggbbbbbbyyybbbbm", "mbbbggbbbbbbbybbbbbm",
                       "mbbbbgbbbbbbbbbbggbm", "mbbbbbbbbggbbbbbgbbm", "mbbbbbbbbbggbbbbbbbm",
                       "mmmmmmmmmmmmmmmmmmmm"],
              {"m": (96, 62, 40, 255), "b": (64, 128, 200, 255), "g": (120, 176, 96, 255),
               "y": (222, 204, 150, 255)})
POSTER = cartel(123, 21, ["pppppppp", "pPPPPPPp", "pPPyyPPp", "pPyyyyPp", "pPPyyPPp", "pPPPPPPp",
                          "pPwwwwPp", "pPPPPPPp", "pppppppp"],
                {"p": (84, 40, 120, 255), "P": (140, 76, 190, 255), "y": (250, 214, 90, 255),
                 "w": (226, 210, 240, 255)})
NUBE = [".ww.www..", "wwwwwwwww", ".wwwwwww."]


def ventana(s0, an, z0=12, al=9):
    """Ventana alta: marco verde, cruz, cristal con su reflejo y alféizar claro."""
    def f(s, z, t, X, Y):
        if not (s0 <= s < s0 + an and z0 - 1 <= z < z0 + al):
            return None
        if z < z0:
            return tt(BLANCO, 4.2, X, Y)                            # el alféizar
        if s < s0 + 0.6 or s >= s0 + an - 0.6 or z >= z0 + al - 1 or z < z0 + 1:
            return tt(MARCO_V, t + 0.6, X, Y)
        if abs(s - (s0 + an / 2)) < 0.3 or int(z) == z0 + al // 2:
            return tt(MARCO_V, t + 0.2, X, Y)
        brillo = 1.0 if (X + Y) % 9 < 2 else 0.0
        return tt(CRISTAL, 3.2 + brillo + (z - z0) / al * 0.8, X, Y)
    return f


def pared_izquierda(s, z, t, X, Y):
    """La de atrás-izquierda (u = 0), por dentro: `s` es v. Mira a +u, la de sombra: se
    aclara un paso para que la casa no quede en penumbra."""
    t += 1.1
    for w in (ventana(9, 10), ventana(42, 9), ventana(86, 8)):
        c = w(s, z, t, X, Y)
        if c:
            return c
    if s < 34:
        c = PINGUINO(s, z)
        if c:
            return c
        for (n_s, n_z) in ((2, 22), (21, 23), (5, 9), (24, 11), (31, 25), (15, 6)):
            cx, cy = int((s - n_s) * 2), int(n_z - z)
            if 0 <= cy < 3 and 0 <= cx < 9 and NUBE[cy][cx] == "w":
                return tt(BLANCO, 4.4, X, Y)
        return tt(NUBES, t, X, Y)
    if s < FRANJA:
        if int(s * 2) % 6 == 0 or int(z) % 3 == 0:
            return tt(AZULEJO, t - 0.8, X, Y)
        return tt(AZULEJO, t + 0.3, X, Y)
    return tt(MELOCOTON, t, X, Y)


def pared_derecha(s, z, t, X, Y):
    """La de atrás-derecha (v = V), por dentro: `s` es u. Mira a -v, la iluminada."""
    t -= 0.2
    for w in (ventana(10, 10), ventana(46, 9), ventana(86, 9), ventana(131, 9)):
        c = w(s, z, t, X, Y)
        if c:
            return c
    for c_ in (MAPA, POSTER):
        c = c_(s, z)
        if c:
            return c
    if s < 44:
        return tt(MELOCOTON, t, X, Y)
    if s < 100:
        if 6 <= z < 7:
            return tt(MESA_OSC, t + 0.5, X, Y)                     # el friso de madera
        if z < 6:
            return tt(MESA, t - 0.3, X, Y)
        return tt(CREMA, t, X, Y)
    return tt(MARRON_R if int(s) % 3 == 0 else BEIGE, t, X, Y)


def paredes(E):
    # Por dentro, con su dibujo; el canto de arriba y las cabezas, en oscuro: el corte.
    E.pared((0, 0), (0, V), 0, H, pared_izquierda, normal=(1, 0, 0))
    E.pared((0, V), (U, V), 0, H, pared_derecha, normal=(0, -1, 0))
    corte = lambda uu, vv, X, Y: tt(CANTO, 3.4, X, Y)
    E.rect(-2, -1.5, 2, V + 3.5, H, corte)
    E.rect(-2, V, U + 3.5, 2, H, corte)
    E.pared((-2, -1.5), (0, -1.5), 0, H, k.liso(CANTO, 0.3), normal=(0, -1, 0))
    E.pared((U + 1.5, V), (U + 1.5, V + 2), 0, H, k.liso(CANTO, -0.2), normal=(1, 0, 0))


def tabique(E, u, v, a, b, alto, huecos=()):
    """Media pared baja y oscura; `huecos` en la dirección larga, (desde, hasta)."""
    largo_u = a > b
    ini, fin = (u, u + a) if largo_u else (v, v + b)
    cortes, x = [], ini
    for h0, h1 in sorted(huecos):
        cortes.append((x, h0))
        x = h1
    cortes.append((x, fin))
    for c0, c1 in cortes:
        if c1 - c0 <= 0:
            continue
        if largo_u:
            caja(E, c0, v, c1 - c0, b, 0, alto, OSCURO, sube=0.4, tope=3.6)
        else:
            caja(E, u, c0, a, c1 - c0, 0, alto, OSCURO, sube=0.4, tope=3.6)


# ---------------------------------------------------------------- los suelos
def suelos(E):
    d = -0.05

    def gris(u, v, X, Y):
        return tt(S_GRIS, 3.6, X, Y)

    def baldosa(u, v, X, Y):
        if (u % 5) < 0.55 or (v % 5) < 0.55:
            return tt(S_BALDOSA, 2.4, X, Y)
        return tt(S_BALDOSA, 3.9, X, Y)

    def damero(u, v, X, Y):
        par = (int(u // 8) + int((v - FRANJA) // 8)) % 2
        return tt(S_DAMERO, 3.4 if par else 2.2, X, Y)

    def madera(u, v, X, Y):
        fila = int(v // 2.5)
        if (v % 2.5) < 0.45 or ((u + fila * 7) % 13) < 0.5:
            return tt(S_MADERA, 1.8, X, Y)
        return tt(S_MADERA, 3.4 + 0.3 * (fila % 2), X, Y)

    def blanco(u, v, X, Y):
        return tt(S_BLANCO, 4.0, X, Y)

    def espiga(u, v, X, Y):
        # Tablas de 6 x 2 a soga, cada hilada corrida media tabla.
        fila = int(v // 2)
        ru = (u + (3 if fila % 2 else 0)) % 6
        if (v % 2) < 0.45 or ru < 0.5:
            return tt(S_ESPIGA, 2.6, X, Y)
        return tt(S_ESPIGA, 3.9 + (0.4 if (int((u + (3 if fila % 2 else 0)) // 6) * 5 + fila) % 3 == 0 else 0), X, Y)

    E.rect(0, 0, IZQ, 34, 0, gris, d)
    E.rect(0, 34, IZQ, FRANJA - 34, 0, baldosa, d)
    E.rect(0, FRANJA, 44, V - FRANJA, 0, damero, d)
    E.rect(44, FRANJA, 56, V - FRANJA, 0, madera, d)
    E.rect(100, FRANJA, U - 100, V - FRANJA, 0, blanco, d)
    E.rect(IZQ, 0, U - IZQ, FRANJA, 0, espiga, d)


def hierba_y_camino(E):
    k.entorno(E, calles=())

    def losa(u, v, X, Y):
        if (u - 71) % 5 < 0.6 or (v + 16) % 4 < 0.6:
            return tt(LOSA, 2.2, X, Y)
        return tt(LOSA, 3.6 + (0.5 if int((u - 71) // 5 + (v + 16) // 4) % 3 == 0 else 0), X, Y)
    E.rect(71, -16, 10, 16, 0.02, losa)


# ---------------------------------------------------------------- las salas
def dormitorio(E):
    for n, v0 in enumerate((2, 14, 26)):
        caja(E, 0, v0, 1.2, 7, 0, 8, MESA_OSC, sube=0.3)                          # cabecero
        caja(E, 1.2, v0, 12, 7, 0, 2.5, MESA, sube=-0.2)
        caja(E, 1.4, v0 + 0.2, 11.6, 6.6, 2.5, 1.5, BLANCO, tope=4.4)               # colchón
        caja(E, 1.8, v0 + 0.8, 3, 5.4, 4, 1.2, BLANCO, tope=5)                      # almohada
        caja(E, 5, v0 + 0.1, 8.2, 6.8, 2.6, 2.2, MORADO, tope=3.6)                   # manta
        E.linea((5.2, v0 + 0.15, 4.85), (5.2, v0 + 6.85, 4.85), g.cr(MORADO, 5), 0.05)  # el embozo
    for v0 in (10, 22):
        caja(E, 0.5, v0 + 0.5, 3.5, 3, 0, 4.5, MESA)
        E.linea((2.2, v0 + 2, 4.5), (2.2, v0 + 2, 6.5), (80, 70, 60, 255), 0.05)
        E.cilindro(2.2, v0 + 2, 1.3, 6.5, 2.5, k.liso(ROSA, 0.6), techo=lambda *a: tt(ROSA, 4.8, a[2], a[3]), lados=12)


def ordenadores(E):
    for (u0, v0) in ((1, 37), (1, 48), (15, 37), (15, 48)):
        mesa(E, u0, v0, 8, 9, MESA)
        crt(E, u0 + 0.6, v0 + 1.6, 6, "+u")
        caja(E, u0 + 0.6, v0 + 6.2, 3, 2, 6, 5, GRIS_CRT, sube=-0.3)               # la torre
        E.punto(u0 + 3.6, v0 + 7, 6 + 3.5, (120, 230, 120, 255), 0.05)
        silla(E, u0 + 9.5, v0 + 3, TURQUESA, "u+")


def despacho(E):
    # La alfombra naranja, con su cenefa.
    def alf(u, v, X, Y):
        borde = u < 13 or u > 33 or v < 66 or v > 86
        return tt(NARANJA, 2.6 if borde else 3.6 + (0.6 if (int(u) + int(v)) % 4 == 0 else 0), X, Y)
    E.rect(12, 65, 22, 22, 0.05, alf)
    # La estantería alta contra la pared de la izquierda, llena de libros de colores.
    LIBROS = [(196, 60, 52), (60, 110, 186), (230, 186, 60), (70, 150, 90), (150, 80, 160), (226, 226, 214),
              (226, 120, 60)]

    def libros(s, z, t, X, Y):
        if E.normal[0] < 0.5:
            return k.pinta(MESA_OSC, t + 0.3, X, Y, z)
        if int(z) % 6 == 0 or z < 1 or s < 0.5 or s > 13.5:
            return tt(MESA_OSC, t + 0.4, X, Y)
        balda = int(z // 6)
        q = int(s * 2 + balda * 3)
        if (q * 7 + balda) % 9 == 0 and int(z) % 6 >= 4:
            return tt(MESA_OSC, t - 1, X, Y)                       # un hueco
        col = LIBROS[(q * 5 + balda * 3) % len(LIBROS)]
        return col + (255,) if int(z) % 6 != 1 else oscurece(col + (255,), 0.75)
    E.caja(0.2, 64, 4, 14, 0, 24, libros, techo=lambda *a: tt(MESA_OSC, 3.6, a[2], a[3]))
    # El reloj de pie, contra la pared del fondo.

    def reloj(s, z, t, X, Y):
        de_cara = E.normal[1] < -0.5
        esfera = math.hypot((s - 1.7) * 2, z - 18.5)
        if de_cara and esfera < 2.6:
            if esfera < 0.8 or (abs(s - 1.7) < 0.3 and 18.5 <= z < 20.5) or (z == 18 and s > 1.7):
                return (40, 30, 26, 255)
            return (244, 236, 210, 255) if esfera < 2.0 else (220, 182, 70, 255)
        if not de_cara:
            return k.pinta("nogal", t + 0.3, X, Y, z)
        if 5 <= z < 13 and 0.9 < s < 2.5:
            return (226, 186, 70, 255) if z < 7 and abs(s - 1.7) < 0.5 else tt(MESA_OSC, t - 1.2, X, Y)
        return k.pinta("nogal", t + 0.3, X, Y, z)
    E.caja(24, 93, 3.4, 2.6, 0, 23, reloj, techo=lambda *a: tt("nogal", 4, a[2], a[3]))
    caja(E, 23.6, 92.7, 4.2, 3.0, 23, 1.5, "nogal", tope=4)
    # La mesa con su monitor, quien trabaja y la silla azul de visitas.
    mesa(E, 15, 76, 13, 6, MESA_OSC)
    crt(E, 16, 79.2, 6, "+v")
    E.rect(22, 76.6, 3, 1.4, 6.05, lambda *a: (240, 240, 232, 255))              # unos papeles
    silla(E, 21.5, 82, MESA_OSC, "v+")
    E.sprite(persona((70, 50, 40, 255), (210, 210, 200, 255), PIEL[0], True, 3), 23, 83, 4.2)
    silla(E, 30, 73, AZUL_CLARO, "u+")
    maceta(E, 38.5, 91, 2.4, 4, BLANCO, alto=17, semilla=3, ancho=4)
    maceta(E, 39, 84.5, 2.0, 3.5, BARRO, alto=12, semilla=9, ancho=3)


def comedor(E):
    mesa(E, 50, 75, 32, 8, MESA)
    for i in range(4):
        u0 = 52 + i * 8
        silla(E, u0, 71.2, MESA_OSC, "v-")
        silla(E, u0, 84, MESA_OSC, "v+")
    E.cilindro(66, 79, 1.1, 6, 3, k.liso(BLANCO, 0.4), techo=lambda *a: tt(BLANCO, 4, a[2], a[3]), lados=12)
    for q in range(3):                                                           # los tallos
        E.linea((66, 79, 8.5), (66 + 0.6 * (q - 1), 79, 11.5), (70, 120, 60, 255), 0.3)
    for q in range(14):
        a = q * 2.1
        rr = 0.5 + (q % 3) * 0.5
        E.punto(66 + rr * math.cos(a), 79 + rr * math.sin(a), 11 + (q % 4) * 0.8, FLOR_AZUL[q % 2], 0.5)
    # La pizarra en su caballete, de cara a la mesa.

    def pizarra(s, z, t, X, Y):
        if s < 0.5 or s > 8.5 or z < 0.8 or z > 8.2:
            return tt(ACERO, t + 0.8, X, Y)
        if 3 < z < 4 and 1.5 < s < 6:
            return (60, 110, 190, 255)
        if 5.5 < z < 6.5 and 1.5 < s < 7:
            return (200, 60, 60, 255)
        return tt(BLANCO, 4.4, X, Y)
    for du in (0.8, 7.6):
        E.linea((86 + du, 88, 0), (86 + du, 88.3, 14), g.cr(ACERO, 2), 0.02)
    E.linea((90.2, 91, 0), (90.2, 88.8, 12), g.cr(ACERO, 1), 0.02)
    E.caja(86, 87.6, 9, 0.6, 5, 9, pizarra, techo=lambda *a: tt(ACERO, 4, a[2], a[3]))
    flores(E, 47.5, 64, FLOR_NAR, semilla=2)


def salita(E):
    # La encimera con la cafetera, contra el fondo.
    caja(E, 103, 90, 16, 5.6, 0, 7, BLANCO, sube=-0.2, tope=4.2)
    caja(E, 102.6, 89.6, 16.8, 6.4, 7, 0.8, MESA_OSC, tope=3.6)
    caja(E, 105, 91.2, 3, 3, 7.8, 4.5, M((44, 44, 50), "cafetera"), tope=3)
    E.punto(106.5, 91.1, 9.3, (240, 60, 50, 255), 0.05)
    E.cilindro(110, 92, 0.9, 7.8, 1.6, k.liso(BLANCO, 0.6), techo=lambda *a: tt(BLANCO, 4, a[2], a[3]), lados=10)
    # El sofá gris contra el tabique de la izquierda, mirando a +u.
    caja(E, 101, 66, 7, 16, 0, 3.5, SOFA, sube=-0.3)
    caja(E, 101, 66, 2.4, 16, 3.5, 5, SOFA, sube=0.2, tope=4)                      # respaldo
    caja(E, 103.4, 66, 4.6, 2.2, 3.5, 2.5, SOFA, sube=0.3)                          # brazos
    caja(E, 103.4, 79.8, 4.6, 2.2, 3.5, 2.5, SOFA, sube=0.3)
    for q in range(2):
        caja(E, 103.6, 68.4 + q * 5.8, 4.2, 5.4, 3.5, 0.9, SOFA, tope=4.2)          # cojines
    # La alfombra redonda azul, la mesa baja con su brillo.
    pts = [(116 + 8 * math.cos(2 * math.pi * q / 24), 75 + 8 * math.sin(2 * math.pi * q / 24)) for q in range(24)]

    def alf(u, v, X, Y):
        d = math.hypot(u - 116, v - 75)
        return tt(AZUL_ALF, 2.4 if d > 6.8 or 3.2 < d < 3.9 else 3.6, X, Y)
    E.plano(pts, 0.05, alf)
    E.cilindro(116, 75, 3.6, 0, 3, k.liso(M((44, 40, 44), "mesa baja"), 0.3),
               techo=lambda uu, vv, X, Y: (90, 170, 255, 255) if math.hypot(uu - 115, vv - 74.5) < 1.1
               else tt(M((44, 40, 44), "mesa baja"), 3.8, X, Y))
    # El banco metálico junto al murete.
    caja(E, 138, 64, 4, 14, 3, 0.8, ACERO, tope=4.4)
    for dv in (0.5, 12.5):
        caja(E, 138.4, 64 + dv, 3.2, 1, 0, 3, ACERO, sube=-0.6)
    maceta(E, 139.5, 91.5, 2.2, 4, AMARILLO, alto=14, semilla=6, ancho=3)


def oficina(E):
    gente = [((40, 30, 26, 255), (206, 62, 58, 255), PIEL[0], 0),
             ((232, 196, 96, 255), (80, 160, 90, 255), PIEL[3], 1),
             ((20, 18, 20, 255), (60, 100, 190, 255), PIEL[2], 2),
             ((196, 96, 40, 255), (240, 200, 70, 255), PIEL[0], 3),
             ((150, 150, 156, 255), (226, 132, 48, 255), PIEL[1], 4),
             ((90, 50, 120, 255), (232, 112, 150, 255), PIEL[1], 1)]
    # Fila de atrás: de cara a nosotros, con el monitor a un lado y de espaldas.
    for n, u0 in enumerate((38, 74, 110)):
        pelo, ropa, piel, est = gente[n]
        mesa(E, u0, 40, 15, 7, MESA)
        crt(E, u0 + 9.5, 42.5, 6, "+v")
        E.rect(u0 + 3, 41.2, 4, 1.3, 6.05, lambda *a: tt(BLANCO, 3.4, a[2], a[3]))
        silla(E, u0 + 3.5, 47.6, TURQUESA, "v+")
        E.sprite(persona(pelo, ropa, piel, True, est), u0 + 5, 48.8, 4.2)
    # Fila de delante, corrida media mesa: de espaldas, mirando su pantalla.
    for n, u0 in enumerate((46, 82, 116)):
        pelo, ropa, piel, est = gente[n + 3]
        mesa(E, u0, 17, 15, 7, MESA)
        crt(E, u0 + 6, 20, 6, "-v")
        caja(E, u0 + 11, 20.5, 2, 3, 6, 4.5, GRIS_CRT, sube=-0.3)
        silla(E, u0 + 5.8, 13.2, TURQUESA, "v-")
        E.sprite(persona(pelo, ropa, piel, False, est if n != 1 else 4), u0 + 7.3, 14.6, 4.2)
    maceta(E, 141.2, 2.8, 2.6, 4.5, BARRO, alto=18, semilla=1, ancho=4)            # delante del todo
    maceta(E, 34.5, 4.5, 2.4, 4.5, BLANCO, alto=15, semilla=4, ancho=3)
    flores(E, 33.5, 56.5, FLOR_NAR, semilla=5)


# ---------------------------------------------------------------- todo junto
def escena():
    E = k.Parcela(9, 6, extra=60, margen=1)
    hierba_y_camino(E)
    suelos(E)
    paredes(E)
    # El murete de delante (con el hueco de la entrada) y el de la derecha.
    tabique(E, 0, -1.5, U + 1.5, 1.5, 4, huecos=[(71, 81)])
    tabique(E, U, 0, 1.5, V, 4)
    # Las medias paredes de dentro.
    tabique(E, IZQ, 0, 1, FRANJA, 6, huecos=[(25, 31), (44, 50)])
    tabique(E, 0, 34, IZQ, 1, 6)
    tabique(E, 0, FRANJA, U, 1, 6, huecos=[(34, 41), (60, 68), (124, 132)])
    tabique(E, 44, FRANJA + 1, 1, V - FRANJA - 1, 6, huecos=[(66, 72)])
    tabique(E, 100, FRANJA + 1, 1, V - FRANJA - 1, 6, huecos=[(84, 90)])
    dormitorio(E)
    ordenadores(E)
    despacho(E)
    comedor(E)
    salita(E)
    oficina(E)
    img = E.imagen(contorno=True)
    fondo = Image.new("RGBA", (img.width + 24, img.height + 24), (0, 0, 0, 255))
    fondo.alpha_composite(img, (12, 12))
    return fondo


if __name__ == "__main__":
    img = escena()
    img.save(os.path.join(AQUI, "oficina.png"))
    img.resize((img.width * 3, img.height * 3), Image.NEAREST).save(os.path.join(AQUI, "oficina_x3.png"))
    print(img.size)
