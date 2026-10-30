"""**El kit de las escenas isométricas**: una `Parcela` de casillas sobre la que se montan
volúmenes de verdad —cajas, prismas de cualquier planta, cilindros, cúpulas, cubiertas,
paredes pintadas— rasterizados con su profundidad, y sprites metidos en la escena que se
tapan bien con ellos.

Sacado del generador de sprites de Guremu City, **copiado tal cual pinta**.

- **Prismas de cualquier planta** (`prisma`): un polígono en planta levantado, con su tapa.
- **Cajas** (`caja`), **cilindros** y **cúpulas** facetados finos con el tono **por normal**,
  así que se leen redondos.
- **Cubiertas** a dos y a cuatro aguas, pirámides y faldones inclinados.
- **Fachadas pintadas sobre la cara**: cada pared sabe su `s` (unidades a lo largo) y su `z`
  (píxeles de alto), y quien la pinta decide ventanas, franjas, letreros o dibujos.
- **Suelos** (`rect`, `plano`), **puntos** y **líneas** sueltos.
- **Sprites** (`sprite`): árboles, gente, cualquier imagen con su ancla, con profundidad.
- **Vehículos aparcados** (`camion_en`, `furgo_en`, `coche_en`): las piezas de `vehiculos.py`
  y `coches.py`, que solo se cargan si se usan.

La luz: arriba lo más claro, lo que mira a `-v` (la cara de delante, izquierda en pantalla)
iluminado, lo que mira a `+u` (la derecha) en sombra; con los tonos fraccionarios tramados
(`tono_tramado`).

La planta: 16 unidades por casilla, `u` a lo largo de las columnas (hacia abajo a la derecha
en pantalla) y `v` a lo largo de las filas (hacia arriba a la derecha), `v = 0` el canto de
delante. `z` en píxeles. En pantalla, `S(u, v, z)`: x = 2u + 2v, y = u - v - z.
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image  # noqa: E402

import dibujo as g  # noqa: E402

CASILLA = 16                      # unidades de planta por casilla
VIDRIO = g.material_de((70, 92, 120), "kit vidrio")
VIDRIO_OSCURO = g.material_de((40, 50, 66), "kit vidrio oscuro")
LUZ_VENTANA = (236, 206, 120, 255)
LUZ_FRIA = (176, 214, 226, 255)
APAGADA = (40, 46, 56, 255)


def luz_ventana():
    """La ventana encendida, **si hay luz** (`g.hay_luz()`): con el apagón, oscura. Sin
    pasar por ahí, las piezas del kit se quedaban encendidas en una escena a oscuras."""
    return LUZ_VENTANA if g.hay_luz() else APAGADA


def luz_fria():
    return LUZ_FRIA if g.hay_luz() else APAGADA


def tono_normal(nu, nv, nz):
    return g._tono_tubo(nu, nv, nz)


def tono_pared(n):
    """El tono base de una pared por hacia dónde mira, **en la escala del kit**: la que
    mira a `-v` es la izquierda (3, `IZQ`), la que mira a `+u` la derecha (1, `DER`), y las
    oblicuas en medio. La fórmula de los tubos da 3,7 y 1,5, que tramado en una pared plana
    sale a damero."""
    t = (g._tono_tubo(n[0], n[1], 0) - 1.5) / 2.2 * 2 + 1
    return max(0.6, min(3.6, t))


def pinta(mat, t, X, Y, dentro=5, alto=99):
    """Un punto de pared como una pared de casilla: la textura del material, sus manchas
    y el tramado entre tonos."""
    d = g._tex(mat, X, Y, int(dentro))
    if d and 1 < dentro < alto - 1:
        t += d
    return g.mancha(mat, round(t), X, Y) or g.tono_tramado(mat, t, X, Y)


class Parcela:
    """Una parcela de `cols x filas` casillas con todo lo que se monte encima, rasterizado
    con profundidad. `extra` es el sitio por arriba para lo alto."""

    def __init__(self, cols, filas, extra=160, margen=0):
        self.cols, self.filas = cols, filas
        self.img, self.ox, self.oy = g.parcela(cols + 2 * margen, filas + 2 * margen, extra)
        self.margen = margen
        self.wx = self.ox - (filas + 2 * margen) * g.MX + 2 * margen * CASILLA * 0
        self.wy = self.oy + (filas + 2 * margen - 1) * g.MY
        # Con margen, la parcela de verdad empieza `margen` casillas dentro.
        self.du = margen * CASILLA
        self.dv = margen * CASILLA
        self.buf = {}

    # ------------------------------------------------------------ lo básico
    def S(self, u, v, z):
        u, v = u + self.du, v + self.dv
        return self.wx + 2 * u + 2 * v, self.wy + u - v - z

    @staticmethod
    def prof(u, v, z):
        return u - v + z / g.Z_REDONDO

    def poner(self, X, Y, p, col):
        if col is None:
            return
        antes = self.buf.get((X, Y))
        if antes is None or p > antes[0]:
            self.buf[(X, Y)] = (p, col)

    def cara(self, O, E1, E2, col, tri=False, delante=0.0):
        """Un paralelogramo `O + a E1 + b E2` (o su triángulo con `tri`). `col(a, b, X, Y)`
        devuelve el color del punto o None para dejarlo hueco."""
        sx, sy = self.S(*O)
        e1x, e1y = self.S(*E1)[0] - self.S(0, 0, 0)[0], self.S(*E1)[1] - self.S(0, 0, 0)[1]
        e2x, e2y = self.S(*E2)[0] - self.S(0, 0, 0)[0], self.S(*E2)[1] - self.S(0, 0, 0)[1]
        det = e1x * e2y - e2x * e1y
        if abs(det) < 1e-6:
            return
        esq = [(sx + a * e1x + b * e2x, sy + a * e1y + b * e2y) for a in (0, 1) for b in (0, 1)]
        for X in range(math.floor(min(p[0] for p in esq)) - 1, math.ceil(max(p[0] for p in esq)) + 2):
            for Y in range(math.floor(min(p[1] for p in esq)) - 1, math.ceil(max(p[1] for p in esq)) + 2):
                dx, dy = X + 0.5 - sx, Y + 0.5 - sy
                a = (dx * e2y - e2x * dy) / det
                b = (e1x * dy - dx * e1y) / det
                if not (-1e-9 <= a <= 1 + 1e-9 and -1e-9 <= b <= 1 + 1e-9):
                    continue
                if tri and a + b > 1 + 1e-9:
                    continue
                c = col(a, b, X, Y) if callable(col) else col
                if c is not None:
                    u, v, z = (O[k] + a * E1[k] + b * E2[k] for k in range(3))
                    self.poner(X, Y, self.prof(u, v, z) + delante, c)

    def punto(self, u, v, z, col, delante=0.02):
        X, Y = self.S(u, v, z)
        self.poner(int(round(X)), int(round(Y)), self.prof(u, v, z) + delante, col)

    def linea(self, p0, p1, col, delante=0.02):
        n = int(max(abs(self.S(*p1)[0] - self.S(*p0)[0]), abs(self.S(*p1)[1] - self.S(*p0)[1]), 1) * 2)
        for k in range(n + 1):
            t = k / n
            p = [p0[i] + (p1[i] - p0[i]) * t for i in range(3)]
            self.punto(*p, col, delante)

    # ------------------------------------------------------------ superficies
    def plano(self, poly, z, col, delante=0.0):
        """Un polígono horizontal a la altura `z`, en abanico: tiene que ser convexo, o
        partirlo uno. `col(u, v, X, Y)` o un color."""
        p0 = poly[0]
        for k in range(1, len(poly) - 1):
            p1, p2 = poly[k], poly[k + 1]
            O = (p0[0], p0[1], z)
            E1 = (p1[0] - p0[0], p1[1] - p0[1], 0)
            E2 = (p2[0] - p0[0], p2[1] - p0[1], 0)

            def c(a, b, X, Y, O=O, E1=E1, E2=E2):
                if not callable(col):
                    return col
                return col(O[0] + a * E1[0] + b * E2[0], O[1] + a * E1[1] + b * E2[1], X, Y)
            self.cara(O, E1, E2, c, tri=True, delante=delante)

    def rect(self, u, v, a, b, z, col, delante=0.0):
        self.plano([(u, v), (u + a, v), (u + a, v + b), (u, v + b)], z, col, delante)

    def pared(self, p0, p1, z0, h, fachada, normal=None, suave=None, h_total=None, desde=0, delante=0.0):
        """Una pared vertical de `p0` a `p1` (planta) entre `z0` y `z0 + h`. Solo si mira a
        la cámara. `fachada(s, z, tono, X, Y)` pinta: `s` en unidades desde `p0`, `z` en px
        desde el suelo de la pared, `tono` el que le toca por luz. `suave` = (n0, n1)
        interpola la normal a lo largo, para lo redondo."""
        du, dv = p1[0] - p0[0], p1[1] - p0[1]
        largo = math.hypot(du, dv)
        if largo < 1e-9:
            return
        n = normal or (dv / largo, -du / largo, 0.0)
        if n[0] - n[1] <= 1e-6 and not suave:          # de espaldas
            return

        alto = max(1, h_total or h)
        self.largo, self.normal = largo, n        # para la fachada que quiera saber de qué pared es
        # Y dónde está, para el hueco con fondo (`hueco_hondo()`), que monta lo de dentro detrás.
        self.pared_p0, self.pared_paso, self.pared_z0 = p0, (du / largo, dv / largo), z0

        def c(a, b, X, Y):
            nn = n
            if suave:
                n0, n1 = suave
                nn = g._norm(tuple(n0[k] + (n1[k] - n0[k]) * a for k in range(3)))
                if nn[0] - nn[1] <= 0:
                    return None
            z = b * h
            uu = (desde + z) / alto                        # 0 al pie, 1 en el alero
            t = tono_pared(nn) + max(0.0, (uu - 0.70) / 0.30) - g.FONDO * (1 - uu) ** 1.7
            if desde + z <= 1:
                t -= 0.9                                   # el zócalo que pisa el suelo
            return fachada(a * largo, z, t, X, Y)
        self.cara((p0[0], p0[1], z0), (du, dv, 0), (0, 0, h), c, delante=delante)

    # ------------------------------------------------------------ volúmenes
    def prisma(self, poly, z0, h, fachada, techo=None, suave=False, h_total=None, desde=0):
        """Un polígono en planta, **contra las agujas** con `u` a la derecha y `v` hacia
        arriba (el interior a la izquierda al recorrerlo), levantado de `z0` a `z0 + h`. `fachada` pinta las paredes; `techo`, un
        color, un material o `col(u, v, X, Y)`. Con `suave` las normales se interpolan
        entre caras: para lo redondo."""
        m = len(poly)
        normales = []
        for k in range(m):
            p0, p1 = poly[k], poly[(k + 1) % m]
            du, dv = p1[0] - p0[0], p1[1] - p0[1]
            L = math.hypot(du, dv) or 1
            normales.append((dv / L, -du / L, 0.0))
        for k in range(m):
            p0, p1 = poly[k], poly[(k + 1) % m]
            if suave:
                na = g._norm(tuple(normales[k - 1][i] + normales[k][i] for i in range(3)))
                nb = g._norm(tuple(normales[k][i] + normales[(k + 1) % m][i] for i in range(3)))
                self.pared(p0, p1, z0, h, fachada, suave=(na, nb), h_total=h_total, desde=desde)
            else:
                self.pared(p0, p1, z0, h, fachada, normal=normales[k], h_total=h_total, desde=desde)
        if techo is not None:
            self.plano(poly, z0 + h, techo if callable(techo) or isinstance(techo, tuple)
                       else (lambda u, v, X, Y, m_=techo: g.tono_tramado(m_, 5, X, Y)))

    def caja(self, u, v, a, b, z0, h, fachada, techo=None, **kw):
        self.prisma([(u, v), (u, v + b), (u + a, v + b), (u + a, v)][::-1], z0, h, fachada, techo, **kw)

    def cilindro(self, cu, cv, r, z0, h, fachada, techo=None, lados=32, **kw):
        pts = [(cu + r * math.cos(2 * math.pi * k / lados), cv - r * math.sin(2 * math.pi * k / lados))
               for k in range(lados)]
        self.prisma(pts[::-1], z0, h, fachada, techo, suave=True, **kw)

    def cupula(self, cu, cv, r, z0, alto, mat, bandas=8, lados=32, col=None):
        """Media esfera achatada a `alto` px, en bandas de latitud con su tono por normal."""
        for kb in range(bandas):
            f0, f1 = kb / bandas * math.pi / 2, (kb + 1) / bandas * math.pi / 2
            r0, r1 = r * math.cos(f0), r * math.cos(f1)
            z_0, z_1 = z0 + alto * math.sin(f0), z0 + alto * math.sin(f1)
            for k in range(lados):
                a0, a1 = 2 * math.pi * k / lados, 2 * math.pi * (k + 1) / lados
                P = lambda rr, aa, zz: (cu + rr * math.cos(aa), cv - rr * math.sin(aa), zz)
                A, B, C, D = P(r0, a0, z_0), P(r0, a1, z_0), P(r1, a1, z_1), P(r1, a0, z_1)
                am = (a0 + a1) / 2
                fm = (f0 + f1) / 2
                nn = (math.cos(am) * math.cos(fm), -math.sin(am) * math.cos(fm), math.sin(fm) * 1.3)
                nn = g._norm(nn)
                t = tono_normal(*nn)

                def c(a, b, X, Y, t=t):
                    return col(t, X, Y) if col else g.tono_tramado(mat, t, X, Y)
                E1 = tuple(B[i] - A[i] for i in range(3))
                E2 = tuple(D[i] - A[i] for i in range(3))
                self.cara(A, E1, E2, c)
                E1 = tuple(C[i] - B[i] for i in range(3))
                self.cara(D, tuple(C[i] - D[i] for i in range(3)), tuple(B[i] - D[i] for i in range(3)), c, tri=True)

    def faldon(self, A, B, C, D, mat, col=None):
        """Un faldón plano de cuatro esquinas (A-B-C-D en orden): una cubierta inclinada."""
        E1 = tuple(B[i] - A[i] for i in range(3))
        E2 = tuple(D[i] - A[i] for i in range(3))
        n = _cruz(E1, E2)
        if n[2] < 0:
            n = tuple(-x for x in n)
        n = g._norm(n)
        t = tono_normal(*n)

        def c(a, b, X, Y):
            return col(a, b, t, X, Y) if col else g.tono_tramado(mat, t, X, Y)
        self.cara(A, E1, E2, c, tri=True)
        self.cara(C, tuple(D[i] - C[i] for i in range(3)), tuple(B[i] - C[i] for i in range(3)), c, tri=True)

    def cuatro_aguas(self, u, v, a, b, z, alt, mat, cumbre=None, col=None):
        """Cubierta a cuatro aguas sobre la caja `(u, v, a, b)`. `cumbre`: lo que mide la
        cumbrera a lo largo del lado largo (0 = pirámide)."""
        cu, cv = u + a / 2, v + b / 2
        k = (cumbre if cumbre is not None else max(0.0, abs(a - b))) / 2
        if a >= b:
            T0, T1 = (cu - k, cv, z + alt), (cu + k, cv, z + alt)
        else:
            T0, T1 = (cu, cv - k, z + alt), (cu, cv + k, z + alt)
        E = [(u, v, z), (u + a, v, z), (u + a, v + b, z), (u, v + b, z)]
        if a >= b:
            self.faldon(E[0], E[1], T1, T0, mat, col)          # el de delante (v bajo)
            self.faldon(E[1], E[2], T1, T1, mat, col)
            self.faldon(E[2], E[3], T0, T1, mat, col)
            self.faldon(E[3], E[0], T0, T0, mat, col)
        else:
            self.faldon(E[0], E[1], T0, T0, mat, col)
            self.faldon(E[1], E[2], T1, T0, mat, col)
            self.faldon(E[2], E[3], T1, T1, mat, col)
            self.faldon(E[3], E[0], T0, T1, mat, col)

    def dos_aguas(self, u, v, a, b, z, alt, mat, eje="u", mat_testero=None, col=None):
        """Cumbrera a lo largo de `eje`. Los testeros, triángulos de pared."""
        if eje == "u":
            T0, T1 = (u, v + b / 2, z + alt), (u + a, v + b / 2, z + alt)
            self.faldon((u, v, z), (u + a, v, z), T1, T0, mat, col)
            self.faldon((u + a, v + b, z), (u, v + b, z), T0, T1, mat, col)
            mt = mat_testero or mat
            self.cara((u + a, v, z), (0, b, 0), (0, b / 2, alt),
                      lambda A, B, X, Y: g.tono_tramado(mt, 1.6, X, Y), tri=True)
        else:
            T0, T1 = (u + a / 2, v, z + alt), (u + a / 2, v + b, z + alt)
            self.faldon((u + a, v, z), (u + a, v + b, z), T1, T0, mat, col)
            self.faldon((u, v + b, z), (u, v, z), T0, T1, mat, col)
            mt = mat_testero or mat
            self.cara((u, v, z), (a, 0, 0), (a / 2, 0, alt),
                      lambda A, B, X, Y: g.tono_tramado(mt, 3.6, X, Y), tri=True)

    # ------------------------------------------------------------ sprites
    def sprite(self, spr, u, v, z=0, ax=None, ay=None, delante=0.0):
        """Un sprite de pie en `(u, v, z)`: cada píxel con la profundidad de
        su base más lo que sube. `ax, ay` su ancla (por defecto, la de la pieza o el pie
        centrado)."""
        if ax is None:
            info = spr.info.get("ancla")
            ax, ay = info if info else (spr.width // 2, spr.height - 1)
        X0, Y0 = self.S(u, v, z)
        # **El ancla se redondea una vez**, y luego píxeles enteros. Redondeando
        # cada píxel, con el ancla en medio píxel `round()` lleva los empates al par y un
        # píxel sí y otro no se pisaban dos: los árboles salían a rayas.
        X0, Y0 = math.floor(X0 - ax + 0.5), math.floor(Y0 - ay + 0.5)
        px = spr.load()
        base = self.prof(u, v, z)
        for y in range(spr.height):
            for x in range(spr.width):
                c = px[x, y]
                if c[3] < 128:
                    continue
                sube = max(0, ay - y)
                self.poner(X0 + x, Y0 + y, base + sube / g.Z_REDONDO + delante, c)

    # ------------------------------------------------------------ salida
    def imagen(self, contorno=True):
        img = self.img.copy()
        px = img.load()
        W, H = img.size
        for (X, Y), (_p, c) in self.buf.items():
            if 0 <= X < W and 0 <= Y < H:
                px[X, Y] = c
        if contorno:
            img = g.contorno(img)
        bb = img.getbbox()
        return img.crop(bb) if bb else img

    def pieza(self, contorno=True):
        """**La escena como pieza suelta**: con el perfil negro, recortada y con el ancla
        (`img.info["ancla"]`) en el centro de su casilla de delante. Sin margen: la parcela
        es la pieza."""
        img = self.img.copy()
        px = img.load()
        W, H = img.size
        for (X, Y), (_p, c) in self.buf.items():
            if 0 <= X < W and 0 <= Y < H:
                px[X, Y] = c
        if contorno:
            img = g.contorno(img)
        ax, ay = g.celda(self.ox, self.oy, self.cols - 1, self.filas - 1)
        x0, y0, x1, y1 = img.getbbox()
        sale = g.con_ancla(img.crop((x0, y0, x1, y1)), ax - x0, ay - y0)
        return sale

    def suelo_parcela(self, mat="hormigon"):
        g.suelo_parcela(self.img, self.ox, self.oy, self.cols + 2 * self.margen,
                        self.filas + 2 * self.margen, mat)


def _cruz(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


# ---------------------------------------------------------------- fachadas


def liso(mat, sube=0.0):
    """Pared de un material, con el pie un pelo más oscuro (`g.FONDO`)."""
    def f(s, z, t, X, Y):
        return pinta(mat, t + sube, X, Y, z)
    return f


def ventanal(mat, plantas, alto_planta=9, paso=6, an=3, al=5, desde=3, luz=0.5,
             cristal=VIDRIO, semilla=0, marco=None, techo_libre=0):
    """Ventanas en rejilla sobre una pared de `mat`: `plantas` filas de `alto_planta` px,
    cada una con huecos de `an` x `al` cada `paso` unidades. Una parte encendidas al azar."""
    def f(s, z, t, X, Y):
        k = int((z - desde) // alto_planta)
        dz = (z - desde) - k * alto_planta
        if 0 <= k < plantas and 0 <= dz < al:
            col = int(s // paso)
            ds = s - col * paso
            if 1 <= ds < 1 + an:
                if (col * 7 + k * 13 + semilla) % 100 < luz * 100:
                    return luz_ventana() if dz > 0.5 else g.cr("bronce", 5)
                return g.tono_tramado(cristal, t + (0.6 if dz > al - 2 else 0), X, Y)
            if marco and (ds < 1 or ds >= 1 + an) and 0 <= dz < al:
                return g.tono_tramado(marco, t, X, Y)
        return pinta(mat, t, X, Y, z)
    return f


def muro_cortina(cristal=VIDRIO, montante="acero", paso=4, alto_planta=6, luz=0.3, semilla=0,
                 reflejo=True):
    """Fachada de vidrio entera: montantes cada `paso` unidades y forjados cada
    `alto_planta` px, con un reflejo en diagonal que la hace cristal y no pared azul."""
    def f(s, z, t, X, Y):
        if int(s * 2) % int(paso * 2) == 0:
            return g.tono_tramado(montante, t + 0.5, X, Y)
        if int(z) % alto_planta == 0:
            return g.tono_tramado(montante, t, X, Y)
        k, col = int(z // alto_planta), int(s // paso)
        if (col * 11 + k * 7 + semilla) % 100 < luz * 100:
            return luz_fria()
        brillo = 0.9 if reflejo and (X + Y // 2) % 23 < 4 else 0
        return g.tono_tramado(cristal, t + brillo, X, Y)
    return f


def por_tramos(*tramos):
    """Encadena fachadas por altura: `(z_hasta, fachada)`, de abajo arriba."""
    def f(s, z, t, X, Y):
        for hasta, fa in tramos:
            if z < hasta:
                return fa(s, z, t, X, Y)
        return tramos[-1][1](s, z, t, X, Y)
    return f


def con_franja(fachada, z0, z1, mat, sube=0.0):
    def f(s, z, t, X, Y):
        if z0 <= z < z1:
            return g.tono_tramado(mat, t + sube, X, Y)
        return fachada(s, z, t, X, Y)
    return f


def con_dibujo(fachada, s0, z0, dibujo, colores, escala=1):
    """Un dibujo de caracteres (`"#"`, `"o"`…) pintado en la pared: la fila 0 arriba, cada
    carácter `escala` unidades de ancho y `escala` px de alto. `colores` dice el color de
    cada carácter."""
    alto = len(dibujo)

    def f(s, z, t, X, Y):
        cx = int((s - s0) / escala)
        cy = alto - 1 - int((z - z0) / escala)
        if 0 <= cy < alto and 0 <= cx < len(dibujo[cy]) and s >= s0 and z >= z0:
            ch = dibujo[cy][cx]
            if ch in colores:
                c = colores[ch]
                return c(t, X, Y) if callable(c) else c
        return fachada(s, z, t, X, Y)
    return f


def lamina(imgs, titulos=None, fondo=(56, 60, 52, 255), escala=2, hueco=24, cols=None):
    """Junta varias maquetas en una lámina, a `escala`, sobre fondo de hierba oscura."""
    cols = cols or len(imgs)
    filas = [imgs[k:k + cols] for k in range(0, len(imgs), cols)]
    W = max(sum(i.width for i in f) + hueco * (len(f) + 1) for f in filas) * escala
    H = sum(max(i.height for i in f) + hueco for f in filas) * escala + hueco * escala
    out = Image.new("RGBA", (W, H), fondo)
    y = hueco * escala
    for f in filas:
        x = hueco * escala
        alto = max(i.height for i in f)
        for i in f:
            big = i.resize((i.width * escala, i.height * escala), Image.NEAREST)
            out.alpha_composite(big, (x, y + (alto - i.height) * escala))
            x += big.width + hueco * escala
        y += (alto + hueco) * escala
    return out


# ---------------------------------------------------------------- el entorno


def baldosa(E, tile, i, j):
    """Una losa de suelo (64 x 32) en la casilla `(i, j)` del lienzo entero,
    margen incluido: así se pinta la calle de delante o la hierba de alrededor."""
    x, y = g.celda(E.ox, E.oy, i, j)
    E.img.alpha_composite(tile, (x - g.MX, y - g.MY))


def entorno(E, calles=("delante",), hierba="hierba"):
    """La parcela con su margen: hierba alrededor y calle en los cantos que se pidan
    (`delante` es el canto j+, `derecha` el i+, `detras` el j-, `izquierda` el i-), con
    sus cruces en las esquinas. Necesita una `Parcela` con `margen=1`."""
    n_i, n_j = E.cols + 2, E.filas + 2
    lados = set(calles)
    for i in range(n_i):
        for j in range(n_j):
            borde = {"izquierda": i == 0, "derecha": i == n_i - 1, "detras": j == 0, "delante": j == n_j - 1}
            en = [k for k, v in borde.items() if v and k in lados]
            if not any(borde.values()):
                continue
            if not en:
                baldosa(E, g.suelo(hierba, i * 7 + j), i, j)
                continue
            if len(en) == 1:
                eje = ("i-", "i+") if en[0] in ("delante", "detras") else ("j-", "j+")
                baldosa(E, g.calle(eje), i, j)
            else:
                baldosa(E, g.calle(("i-", "i+", "j-", "j+")), i, j)


def porton(fachada, s0, an, al, hoja="acero"):
    """Un portón de persiana en la pared: lamas cada dos px, marco oscuro y el umbral."""
    def f(s, z, t, X, Y):
        if s0 <= s < s0 + an and z < al:
            if s < s0 + 0.8 or s >= s0 + an - 0.8 or z >= al - 1:
                return g.tono_tramado(hoja, t - 1.2, X, Y)
            return g.tono_tramado(hoja, t + (0.5 if int(z) % 2 else -0.3), X, Y)
        return fachada(s, z, t, X, Y)
    return f


def puerta_cristal(fachada, s0, an, al, marco="acero"):
    def f(s, z, t, X, Y):
        if s0 <= s < s0 + an and z < al:
            if s < s0 + 0.6 or s >= s0 + an - 0.6 or z >= al - 1 or abs(s - (s0 + an / 2)) < 0.4:
                return g.tono_tramado(marco, t - 0.5, X, Y)
            return g.tono_tramado(VIDRIO, t + 0.4, X, Y)
        return fachada(s, z, t, X, Y)
    return f


def chapa(mat, paso=2, sube=0.0):
    """Chapa grecada: nervios verticales cada `paso` unidades."""
    def f(s, z, t, X, Y):
        k = (s / paso) % 1
        return g.tono_tramado(mat, t + sube + (0.6 if k < 0.25 else (-0.4 if k > 0.75 else 0)), X, Y)
    return f


def anclado(spr):
    """El ancla de un sprite (`info['ancla']`), o su pie centrado."""
    a = spr.info.get("ancla")
    return a if a else (spr.width // 2, spr.height - 1)


def suelto(dibujar, w=60, h=70, pie=None):
    """Un sprite hecho con una función de dibujo que pinta en `(px, img, x,
    suelo_y, ...)`: se dibuja en su lienzo con el pie en `(w/2, pie)` y se recorta."""
    img = Image.new("RGBA", (w, h), g.NADA)
    pie = pie if pie is not None else h - 4
    dibujar(img.load(), img, w // 2, pie)
    bb = img.getbbox()
    out = img.crop(bb)
    out.info["ancla"] = (w // 2 - bb[0], pie - bb[1])
    return out


# ---------------------------------------------------------------- más formas

VISTA = (1.0, -1.0, 0.5)            # hacia la cámara: por donde crece la profundidad


def _ve(n):
    return n[0] * VISTA[0] + n[1] * VISTA[1] + n[2] * VISTA[2] > 1e-6


def cuadro(E, A, B, C, D, col, tono=None):
    """Un cuadrilátero plano cualquiera (A-B-C-D), con su tono por normal. `col(t, X, Y)`
    o un material."""
    E1 = tuple(B[i] - A[i] for i in range(3))
    E2 = tuple(D[i] - A[i] for i in range(3))
    n = g._norm(_cruz(E1, E2))
    if not _ve(n):
        n = tuple(-x for x in n)
    t = tono if tono is not None else (tono_normal(*n) if abs(n[2]) > 0.2 else tono_pared(n))

    def c(a, b, X, Y):
        return col(t, X, Y) if callable(col) else g.tono_tramado(col, t, X, Y)
    E.cara(A, E1, E2, c, tri=True)
    E.cara(C, tuple(D[i] - C[i] for i in range(3)), tuple(B[i] - C[i] for i in range(3)), c, tri=True)


def tronco_cono(E, cu, cv, r0, r1, z0, h, col, lados=28):
    """Un tronco de cono de radio `r0` abajo a `r1` arriba: el horno de una vidriera, una
    chimenea que se estrecha. Con `r1 = 0`, un cono."""
    for k in range(lados):
        a0, a1 = 2 * math.pi * k / lados, 2 * math.pi * (k + 1) / lados
        P = lambda r, a, z: (cu + r * math.cos(a), cv - r * math.sin(a), z)
        am = (a0 + a1) / 2
        lado = math.atan2(r0 - r1, h / 2)                  # cuánto mira arriba
        n = (math.cos(am) * math.cos(lado), -math.sin(am) * math.cos(lado), math.sin(lado))
        if not _ve(n):
            continue
        t = tono_pared(n) + 1.4 * max(0.0, n[2])
        cuadro(E, P(r0, a0, z0), P(r0, a1, z0), P(r1, a1, z0 + h), P(r1, a0, z0 + h), col, tono=t)


def cilindro_tumbado(E, u0, u1, cv, cz, r, col, tapa=None, lados=20):
    """Un cilindro con el eje a lo largo de `u`: una bobina, un depósito tumbado. `tapa`, el
    color o material de la cara del extremo `u1`, que es la que se ve."""
    for k in range(lados):
        a0, a1 = 2 * math.pi * k / lados, 2 * math.pi * (k + 1) / lados
        am = (a0 + a1) / 2
        n = (0.0, math.cos(am), math.sin(am))
        if not _ve(n):
            continue
        Q = lambda u, a: (u, cv + r * math.cos(a), cz + r * math.sin(a) * 2)
        cuadro(E, Q(u0, a0), Q(u1, a0), Q(u1, a1), Q(u0, a1), col, tono=tono_normal(*n))
    if tapa is not None:
        for k in range(lados):
            a0, a1 = 2 * math.pi * k / lados, 2 * math.pi * (k + 1) / lados
            A = (u1, cv, cz)
            B = (u1, cv + r * math.cos(a0), cz + r * math.sin(a0) * 2)
            C = (u1, cv + r * math.cos(a1), cz + r * math.sin(a1) * 2)
            E.cara(A, tuple(B[i] - A[i] for i in range(3)), tuple(C[i] - A[i] for i in range(3)),
                   (lambda a, b, X, Y: tapa(a + b, X, Y)) if callable(tapa)
                   else (lambda a, b, X, Y: g.tono_tramado(tapa, 1.6, X, Y)), tri=True)


def rotulo(E, u, v, z, ancho, alto, icono, colores, fondo, marco=None, cara="v"):
    """Un panel de rótulo plantado de cara a la calle (`cara` "v": mira a `-v`; "u": mira a
    `+u`), con un icono de caracteres centrado. Un dedo de grosor."""
    marco = marco or fondo
    filas, cols = len(icono), max(len(f) for f in icono)
    esc = min(ancho / (cols + 2), alto / (filas + 2) / 2)

    def f(s, zz, t, X, Y):
        L = ancho if cara == "v" else ancho
        if s < 0.7 or s > L - 0.7 or zz < 1 or zz > alto - 1:
            return g.tono_tramado(marco, t + 0.4, X, Y)
        cx = int((s - (L - cols * esc) / 2) / esc)
        cy = filas - 1 - int((zz - (alto - filas * esc * 2) / 2) / (esc * 2))
        if 0 <= cy < filas and 0 <= cx < len(icono[cy]) and icono[cy][cx] in colores:
            c = colores[icono[cy][cx]]
            return c if not isinstance(c, str) else g.tono_tramado(c, t + 1, X, Y)
        return g.tono_tramado(fondo, t, X, Y)
    if cara == "v":
        E.caja(u, v, ancho, 0.8, z, alto, f, techo=marco)
    else:
        E.caja(u, v, 0.8, ancho, z, alto, f, techo=marco)


RUMBO_UV = {"i+": (1, 0), "i-": (-1, 0), "j+": (0, -1), "j-": (0, 1)}


# **Un vehículo aparcado, por encima de su suelo.** `sprite()` le da a todo el dibujo la
# profundidad de su ancla, así que la mitad que asoma hacia la cámara quedaba detrás del
# asfalto y de las rayas que tiene delante y salía cortada en diagonal. Con este margen (lo que
# asoma un vehículo largo desde su centro, en unidades) el suelo no lo tapa; lo que está de pie
# más cerca de la cámara, otro vehículo o una farola, sí.
DELANTE_VEHICULO = 5.0


def vehiculo_en(E, spr, u, v, z=0, delante=0.0):
    """Un vehículo (cualquier sprite de `coches` o `vehiculos`) aparcado en `(u, v)`."""
    E.sprite(spr, u, v, z, delante=DELANTE_VEHICULO + delante)


def camion_en(E, u, v, rumbo="j+", color="roja", carga=None, remolque=True, color_remolque=None):
    """Una tractora con su remolque aparcada: la tractora en `(u, v)` mirando a `rumbo` y el
    remolque detrás a su enganche. `carga`, el color de un contenedor encima."""
    import vehiculos as g                          # aquí y no arriba: solo si se usan
    du, dv = RUMBO_UV[rumbo]
    vehiculo_en(E, g.tractora(color, rumbo), u, v)
    if remolque:
        ru, rv = u - du * 5.5, v - dv * 5.5
        rem = g.remolque(rumbo, color_remolque)
        vehiculo_en(E, rem, ru, rv)
        if carga:
            cont = g.contenedor_rumbo(carga, rumbo)
            cx, cy = rem.info.get("cama", (0, -4))
            # **Encima de la cama**, a su alto (30-10-2026): a ras de suelo tapaba el remolque
            # entero, chasis y ruedas, y el contenedor parecía apoyado en el asfalto.
            ax, ay = anclado(cont)
            E.sprite(cont, ru, rv, -cy, ax - cx, ay, delante=DELANTE_VEHICULO + 0.05)


def furgo_en(E, u, v, hacia_der=True, atras=False, fn=None):
    import vehiculos as g                          # aquí y no arriba: solo si se usan
    spr = g.con_ruedas((fn or g.furgoneta)(hacia_der=hacia_der, atras=atras))
    vehiculo_en(E, spr, u, v)


def coche_en(E, u, v, color=(58, 122, 186), hacia_der=True, atras=False):
    import coches                                  # aquí y no arriba: solo si se usan
    vehiculo_en(E, coches.aparcado(color, hacia_der=hacia_der, atras=atras), u, v)


def palets(E, u, v, n_u=2, n_v=1, pisos=2, mat=None, lado=3):
    """Palets con su carga envuelta: la tarima de madera y el fardo encima."""
    mat = mat or g.material_de((196, 176, 140), "kit carton")
    for a in range(n_u):
        for b in range(n_v):
            uu, vv = u + a * (lado + 0.6), v + b * (lado + 0.6)
            E.caja(uu, vv, lado, lado, 0, 1, liso("madera"), techo="madera")
            E.caja(uu + 0.2, vv + 0.2, lado - 0.4, lado - 0.4, 1, 2 * pisos + 1, liso(mat), techo=mat)


def arbol_en(E, u, v, especie="hoja", alto=20, semilla=0):
    fn = {"hoja": lambda px, img, x, y: g.arbol_hoja(px, img, x, y, alto, semilla),
          "pino": lambda px, img, x, y: g.pino(px, img, x, y, alto, semilla),
          "roble": lambda px, img, x, y: g.roble(px, img, x, y, alto, semilla),
          "arce": lambda px, img, x, y: g.arce(px, img, x, y, alto, semilla),
          "olivo": lambda px, img, x, y: g._olivo(px, img, x, y, alto, semilla)}[especie]
    E.sprite(suelto(fn), u, v, 0)


def farola_en(E, u, v, alto=22):
    E.sprite(suelto(lambda px, img, x, y: g.farola(px, img, x, y, alto)), u, v, 0)


# **El macetero de flores**: barro, dos matas y flores sueltas.
FLORES = ((214, 82, 96), (236, 186, 72), (150, 118, 196), (238, 232, 220))


def macetero_en(E, u, v, a=3.0, b=3.0, alto=1.6, semilla=0):
    """Un macetero de barro de `a` x `b` con dos matas y flores sueltas encima: en barro y no
    en hormigón, que sobre el asfalto de la parcela el gris no se veía."""
    E.caja(u, v, a, b, 0, alto, liso("ladrillo", 0.4), techo="ladrillo")
    E.rect(u + 0.4, v + 0.4, a - 0.8, b - 0.8, alto,
           lambda uu, vv, X, Y: g.tono_tramado("hierba", 3.0, X, Y), delante=0.01)
    for q, (du, dv) in enumerate(((a * 0.32, b * 0.62), (a * 0.68, b * 0.36))):
        uu, vv = u + du, v + dv
        vv = uu - round(uu - vv)                       # u - v entero: sin rayas
        E.sprite(suelto(lambda px, img, x, y, q=q: g.mata(px, img, x, y, lavanda=(q + semilla) % 2 == 1,
                                                          semilla=semilla + q)), uu, vv, alto)
    for q in range(6):
        fu = u + 0.6 + ((semilla * 7 + q * 5) % 10) / 10 * (a - 1.2)
        fv = v + 0.6 + ((semilla * 3 + q * 7) % 10) / 10 * (b - 1.2)
        for dz in (0.6, 1.1):                          # dos píxeles: uno solo no se leía
            E.punto(fu, fv, alto + dz, FLORES[(semilla + q) % len(FLORES)], delante=0.05)


# ---------------------------------------------------------------- el hueco con fondo
# **Los huecos con fondo**: un portón o un túnel no es un rectángulo oscuro pintado en la
# fachada; la fachada deja el hueco y dentro se ven **el suelo, la pared de un costado y el
# fondo**, cada vez más a oscuras hacia dentro. Solo la profundidad.
FONDO_HUECO = (8, 8, 12, 255)
HONDO_HUECO = 8.0                 # unidades de planta hacia dentro: medio casilla


def hueco_hondo(E, s0, an, al, hondo=HONDO_HUECO, mat="hormigon"):
    """**Lo de dentro de un hueco de fachada**, llamado desde la fachada que lo pinta, en el
    hueco: devuelve None (la fachada no pinta ahí) y, la primera vez, monta detrás el suelo,
    las paredes de los costados y el fondo, oscureciendo con la hondura. `s0`, `an` y `al`
    son los de la fachada (desde el principio de su pared y desde su pie). Usa la pared que
    se está pintando (`Parcela.pared()` la deja apuntada), así que vale en cualquier cara."""
    if getattr(E, "pared_p0", None) is None:
        return None
    p0, (du, dv), z0, n = E.pared_p0, E.pared_paso, E.pared_z0, E.normal
    A = (p0[0] + du * s0, p0[1] + dv * s0)
    clave = (round(A[0], 3), round(A[1], 3), round(z0, 3), round(an, 3), round(al, 3))
    hechos = E.__dict__.setdefault("huecos_hondos", set())
    if clave in hechos:
        return None
    hechos.add(clave)
    guardado = (E.largo, E.normal, E.pared_p0, E.pared_paso, E.pared_z0)
    try:
        B = (A[0] + du * an, A[1] + dv * an)
        di = (-n[0] * hondo, -n[1] * hondo)              # hacia dentro del edificio
        A2, B2 = (A[0] + di[0], A[1] + di[1]), (B[0] + di[0], B[1] + di[1])

        def oscuro(col, f):
            f = 0.55 + 0.45 * max(0.0, min(1.0, f))
            return tuple(round(col[i] + (FONDO_HUECO[i] - col[i]) * f) for i in range(3)) + (255,)

        def hondura(u, v):
            return ((u - A[0]) * -n[0] + (v - A[1]) * -n[1]) / hondo

        E.plano([A, B, B2, A2], z0 + 0.02,
                lambda u, v, X, Y: oscuro(g.tono_tramado(mat, 2.6, X, Y), hondura(u, v)))
        for P, sentido in ((A, 1), (B, -1)):
            Q = (P[0] + di[0], P[1] + di[1])
            E.pared(P, Q, z0, al, lambda s, z, t, X, Y: oscuro(g.tono_tramado(mat, t + 0.4, X, Y), s / hondo),
                    normal=(du * sentido, dv * sentido, 0.0))
        E.pared(A2, B2, z0, al, lambda s, z, t, X, Y: FONDO_HUECO, normal=n)
    finally:
        E.largo, E.normal, E.pared_p0, E.pared_paso, E.pared_z0 = guardado
    return None
