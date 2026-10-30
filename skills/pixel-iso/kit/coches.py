"""**Los turismos**: diez modelos, cada uno **un perfil lateral extruido a lo ancho** en dos
piezas —la carrocería a todo lo ancho y el habitáculo un poco más estrecho encima—,
dibujados en 3D de raster (`Raster` y `_Rumbo` de `vehiculos.py`) como la tractora, así que
los ocho rumbos salen del mismo modelo. Lo que separa un modelo de otro **es el perfil**:
dónde empieza el parabrisas, cuánto se tumba, dónde acaba el techo y cómo cae la cola.

El detalle fino —montantes, retrovisores, junta de puertas, lamas de la parrilla,
matrícula— a escala 1 no se ve y a escala 3 ensucia, así que no está. Lo que cuenta el tipo
es la altura y el perfil, un poco exagerados (`fz`), más lo que sobrevive a escala 1: la
banda oscura de las lunas, el techo de otro color, las barras y la baca, la llanta clara y
los píxeles de las luces.

Las piezas: `turismo(modelo, color, rumbo)` con los cuatro colores de calle de cada modelo
(`MODELOS[m].colores`, de la paleta `CALLE`); `taxi(modelo, rumbo)`; `patrulla(rumbo)`; y
`aparcado(color, hacia_der, atras)`, el que pone `coche_en()` del kit. Todas con el ancla en
el centro de su planta. Se importa como `import coches as c`.
"""
from __future__ import annotations

import copy
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Sin el kit: un turismo no es una escena con parcela, son caras de `Raster` sobre un
# `_Rumbo`, como la tractora.
import vehiculos as g  # noqa: E402

# ---------------------------------------------------------------- materiales

LUNA = g.material_de((58, 72, 94), "coche luna")
LUNA_TINTADA = g.material_de((36, 40, 50), "coche luna tintada")
PLASTICO = g.material_de((52, 52, 54), "coche plastico")       # paragolpes y molduras
NEUMATICO = g.NEUMATICO
CROMO = g.CROMO
LLANTA_OSCURA = g.material_de((84, 86, 92), "coche llanta oscura")
LLANTA_AERO = g.material_de((200, 204, 208), "coche aero")
FARO = g.FARO
PILOTO = g.PILOTO
CAJA_PICKUP = g.material_de((44, 44, 46), "coche caja pickup")  # el forro de la caja
LONA_BACA = g.material_de((128, 112, 82), "coche lona baca")

# **La paleta de calle**. Los colores que se ven aparcados en cualquier calle
# —blancos, grises, negros, azules oscuros— y unos pocos con más color, todos **fuera de
# los de servicio**: ni el amarillo del taxi (226, 178, 48), ni el rojo de un parque
# (198, 58, 44), ni el blanco con la librea azul de la patrulla. El rojo de calle es un
# granate, y el blanco va con el techo o las lunas oscuras, nunca con franja azul.
CALLE = {
    "blanco": (218, 218, 212),
    "plata": (162, 168, 174),
    "grafito": (78, 82, 90),
    "negro": (38, 40, 44),
    "marino": (40, 58, 100),
    "azul": (62, 108, 168),
    "granate": (120, 36, 46),
    "verde botella": (44, 88, 64),
    "caqui": (118, 116, 82),
    "arena": (196, 178, 140),
    "celeste": (120, 168, 196),
    "naranja": (206, 108, 40),
}

# **Tres carrocerías van con el material del kit, no con el de la tabla**: el primer
# dibujo pintaba la chapa con `color if color in g.PAL`, y «blanco», «azul» y «arena» ya
# son materiales del kit (los de las fachadas). Así
# que el blanco de un coche es el blanco de un muro —más cálido que el (218, 218, 212) de
# arriba— y lo mismo el azul y el arena. Se escribe aquí a mano para que no dependa de
# qué haya en `g.PAL` el día que alguien añada un «plata». **Los techos sí van con la
# tabla** (`techo_de`): el techo blanco del utilitario es el de calle.
DE_LA_CIUDAD = {"blanco", "azul", "arena"}


def techo_de(nombre):
    """El material de un techo de otro color: siempre el de la paleta de calle."""
    return g.material_de(CALLE[nombre], "coche " + nombre)


def chapa_de(nombre):
    """El material de la carrocería (ver `DE_LA_CIUDAD`)."""
    return nombre if nombre in DE_LA_CIUDAD else techo_de(nombre)


# ---------------------------------------------------------------- geometría de perfil


def _convexo(poly):
    """El perfil tiene que ser convexo y contra las agujas (x adelante, z arriba): si no,
    el abanico de la tapa se sale. Lo comprueba al dibujar, que un modelo mal escrito
    sale con un triángulo de más y no se ve hasta ampliar."""
    m = len(poly)
    for i in range(m):
        (x0, z0), (x1, z1), (x2, z2) = poly[i], poly[(i + 1) % m], poly[(i + 2) % m]
        if (x1 - x0) * (z2 - z1) - (z1 - z0) * (x2 - x1) < -1e-9:
            raise ValueError(f"perfil no convexo en el punto {i + 1}: {poly}")


def rebanada_h(poly, z):
    """Dónde corta el perfil una horizontal a la altura `z`: (x de atrás, x de delante)."""
    xs = []
    m = len(poly)
    for i in range(m):
        (x0, z0), (x1, z1) = poly[i], poly[(i + 1) % m]
        if (z0 - z) * (z1 - z) <= 0 and z0 != z1:
            xs.append(x0 + (x1 - x0) * (z - z0) / (z1 - z0))
    return (min(xs), max(xs)) if xs else None


def rebanada_v(poly, x):
    """Dónde corta el perfil una vertical en `x`: (z de abajo, z de arriba)."""
    zs = []
    m = len(poly)
    for i in range(m):
        (x0, z0), (x1, z1) = poly[i], poly[(i + 1) % m]
        if (x0 - x) * (x1 - x) <= 0 and x0 != x1:
            zs.append(z0 + (z1 - z0) * (x - x0) / (x1 - x0))
    return (min(zs), max(zs)) if zs else None


class Coche:
    """Lo que hace falta para modelar un turismo sobre un `_Rumbo`: perfiles
    extruidos, ruedas con su llanta, y piezas pequeñas. `x` adelante, `y` a la izquierda,
    `z` en píxeles. `fz` estira o aplasta lo que hay por encima de los bajos: es la
    exageración de la silueta (el SUV más alto, el deportivo más bajo)."""

    def __init__(self, rm, fz=1.0, suelo=0.8):
        self.rm, self.fz, self.suelo = rm, fz, suelo
        self.ruedas = []                 # (x, r, zc, rz): las pinta y las usan los pasos
        self.luz = None                  # dónde va la barra, si la lleva: (x, y, z)
        self.luz_tipo = "policia"        # y de qué tipo: el rotativo, o el letrero del taxi

    def Z(self, z):
        return z if z <= self.suelo else self.suelo + (z - self.suelo) * self.fz

    def tono(self, n, mas=0.0):
        return self.rm.tono(n[0], n[1], n[2], mas)

    def cara(self, O, E1, E2, pinta, tri=False):
        rm = self.rm

        def col(a, b):
            return pinta(tuple(O[i] + a * E1[i] + b * E2[i] for i in range(3)))
        rm.r.cara(rm.P(*O), rm.V(*E1), rm.V(*E2), col, tri=tri)

    def extruido(self, perfil, y0, y1, pinta, escalar=True):
        """Un perfil convexo en (x, z) levantado de `y0` a `y1`. `pinta(parte, p, n, t)`
        devuelve el color de un punto: `parte` es `"lado"` en las dos tapas y `"piel"` en
        lo que da la vuelta; `n` la normal (con la z ya en unidades: **una unidad de
        planta son dos píxeles de alto**) y `t` el tono que le toca por luz."""
        if escalar:
            perfil = [(x, self.Z(z)) for x, z in perfil]
        _convexo(perfil)
        m = len(perfil)
        for i in range(m):
            (x0, z0), (x1, z1) = perfil[i], perfil[(i + 1) % m]
            dx, dz = x1 - x0, z1 - z0
            L = math.hypot(dx, dz / 2) or 1
            n = (dz / 2 / L, 0.0, -dx / L)
            t = self.tono(n)
            self.cara((x0, y0, z0), (0, y1 - y0, 0), (dx, 0, dz),
                      lambda p, n=n, t=t: pinta("piel", p, n, t))
        for y, s in ((y0, -1), (y1, 1)):
            n = (0.0, float(s), 0.0)
            t = self.tono(n)
            x0, z0 = perfil[0]
            for i in range(1, m - 1):
                (xa, za), (xb, zb) = perfil[i], perfil[i + 1]
                self.cara((x0, y, z0), (xa - x0, 0, za - z0), (xb - x0, 0, zb - z0),
                          lambda p, n=n, t=t: pinta("lado", p, n, t), tri=True)
        return perfil

    def rueda(self, x, W, r=0.68, ancho=0.5, llanta=0.52, mat_llanta=CROMO, tapacubos=False):
        """Las dos ruedas de un eje, asomando un pelo del costado. La banda en tramos,
        sombreada como un tubo, y en la cara de fuera el neumático oscuro con **la llanta
        clara**, más grande que el cubo de un camión: es lo que dice turismo."""
        rm = self.rm
        rz = 2 * r * 0.85
        zc = rz + 0.02
        self.ruedas.append((x, r, zc, rz))
        for s in (-1, 1):
            y0, y1 = sorted((s * (W + 0.04), s * (W - ancho)))
            n = 14
            for kk in range(n):
                t0, t1 = 2 * math.pi * kk / n, 2 * math.pi * (kk + 1) / n
                tm = (t0 + t1) / 2
                rm.r.cara(rm.P(x + r * math.cos(t0), y0, zc + rz * math.sin(t0)),
                          rm.V(r * (math.cos(t1) - math.cos(t0)), 0,
                               rz * (math.sin(t1) - math.sin(t0))),
                          rm.V(0, y1 - y0, 0),
                          g.cr(NEUMATICO, rm.tono(math.cos(tm), 0, math.sin(tm))))
            yb = s * (W + 0.04)

            def disco(a, b):
                d = a * a + b * b
                if d < llanta * llanta:
                    if tapacubos:                      # el aero del eléctrico: liso
                        return g.cr(mat_llanta, 4 if a - b < 0 else 3)
                    return g.cr(mat_llanta, 2 if d < 0.05 else 4 if a < -0.1 else 3)
                return g.cr(NEUMATICO, 0)
            rm.r.cara(rm.P(x, yb, zc), rm.V(r, 0, 0), rm.V(0, 0, rz), disco, disco=True)

    def en_paso(self, x, z, holgura=1.0):
        """Si el punto de un costado cae en el paso de rueda: 0 fuera, 1 en el hueco
        oscuro, 2 en la moldura (cuando la hay)."""
        for xr, r, zc, rz in self.ruedas:
            e = ((x - xr) / (r + 0.3)) ** 2 + ((z - zc) / (rz + 0.6)) ** 2
            if e < 1:
                return 1
            if e < holgura ** 2:
                return 2
        return 0


# ---------------------------------------------------------------- cómo se pinta


class Modelo:
    """Un turismo: sus medidas y sus dos perfiles, y lo que lleva aparte. Todo en
    unidades a lo largo y a lo ancho, y en píxeles de alto. `colores` son los cuatro de
    calle que lleva, el primero el suyo de siempre."""

    def __init__(self, nombre, largo, ancho, suelo, cuerpo, cabina, ruedas, r,
                 metida=0.22, faros=(2.3, 3.0), pilotos=(2.6, 3.4), parrilla=None,
                 tintadas_desde=None, moldura=False, techo=None, barras=False, fz=1.0,
                 extras=None, llanta=CROMO, tapacubos=False, tira_luz=False, colores=()):
        self.__dict__.update(locals())
        del self.__dict__["self"]
        self.W = ancho / 2
        self.franja = None               # la librea de los de servicio
        self.caja_hasta = None           # la caja abierta de la pickup


def pintor_cuerpo(c, M, mat, techo_mat=None):
    """La carrocería: pasos de rueda, hombro, faldón, luces envolventes, parrilla y
    paragolpes."""
    W, xf, xr = M.W, M.largo / 2, -M.largo / 2
    belt = c.Z(max(z for _x, z in M.cuerpo))
    suelo = M.suelo
    fa0, fa1 = c.Z(M.faros[0]), c.Z(M.faros[1])
    pi0, pi1 = c.Z(M.pilotos[0]), c.Z(M.pilotos[1])
    pa = M.parrilla and (c.Z(M.parrilla[0]), c.Z(M.parrilla[1]))

    def pinta(parte, p, n, t):
        x, y, z = p
        base = lambda tt: g.cr(mat, max(0, min(5, tt)))   # noqa: E731
        if parte == "lado":
            paso = c.en_paso(x, z, 1.28 if M.moldura else 1.0)
            if paso == 1:
                return g.cr(NEUMATICO, 0)
            if paso == 2 or (M.moldura and z < suelo + 0.9):
                return g.cr(PLASTICO, t)
            if z < suelo + 0.45:
                return base(t - 1)
            # Las luces dan la vuelta a la esquina: es lo único que se ve de ellas de
            # perfil (en `der` e `izq` el morro va de canto).
            if x > xf - 0.32 and fa0 <= z <= fa1:
                return FARO
            if x < xr + 0.3 and pi0 <= z <= pi1:
                return PILOTO
            fr = M.franja
            if fr and c.Z(fr[0]) <= z <= c.Z(fr[1]):
                return g.cr(fr[2], t)                  # la librea o el filete de servicio
            if belt - 0.75 < z:
                return base(t + 1)                     # el hombro que coge la luz
            return base(t)
        # la piel: el morro, la cola y las tapas de arriba
        if n[0] > 0.6:                                 # el frente
            if M.tira_luz and fa0 <= z <= fa1 and abs(y) < W - 0.1:
                return FARO
            if abs(y) > W - 0.62 and fa0 <= z <= fa1:
                return FARO
            if pa and abs(y) < W - 0.75 and pa[0] <= z <= pa[1]:
                return g.cr(NEUMATICO, 1)              # la parrilla, de un tono: sin lamas
            if z < suelo + 0.8:
                return g.cr(PLASTICO, t) if M.moldura else base(t - 1)
            return base(t)
        if n[0] < -0.6 and M.caja_hasta is not None:
            return g.cr(CAJA_PICKUP, t) if z < c.Z(M.borde_caja) else base(t)
        if n[0] < -0.6:                                # la cola
            if M.tira_luz and pi0 <= z <= pi1 and abs(y) < W - 0.1:
                return PILOTO
            if abs(y) > W - 0.55 and pi0 <= z <= pi1:
                return PILOTO
            if z < suelo + 0.8:
                return g.cr(PLASTICO, t) if M.moldura else base(t - 1)
            return base(t)
        if n[2] > 0.5 and techo_mat:
            return g.cr(techo_mat, t)
        return base(t)
    return pinta


def luces_de(c, M):
    """**Dónde lleva los faros y los pilotos**, de lo mismo con que los pinta `pintor_cuerpo()`:
    a media altura de su franja, en medio de la banda de cada esquina y en la piel del frente
    o de la cola a esa altura (en la pickup, el portón). `[delante, lado, alto]` desde el
    centro de la planta, que es su ancla."""
    W = M.W
    cuerpo = [(x, c.Z(z)) for x, z in M.cuerpo]
    zf = (c.Z(M.faros[0]) + c.Z(M.faros[1])) / 2
    zp = (c.Z(M.pilotos[0]) + c.Z(M.pilotos[1])) / 2
    xf = rebanada_h(cuerpo, zf)[1]
    pickup = M.caja_hasta is not None
    xp = -M.largo / 2 if pickup else rebanada_h(cuerpo, zp)[0]
    lado_f, lado_p = W - 0.31, W - (0.25 if pickup else 0.275)
    return ([[xf, s * lado_f, zf] for s in (-1, 1)],
            [[xp, s * lado_p, zp] for s in (-1, 1)])


def pintor_cabina(c, M, mat, perfil, techo_mat=None):
    """El habitáculo: las lunas, el techo y, en el SUV, las traseras tintadas. Las lunas
    de un lado se sacan del propio perfil: a cada altura, lo que queda dentro con un
    margen, que es el marco."""
    z_bajo = min(z for _x, z in perfil)

    def luna(t, oscura=False):
        # **Las lunas, oscuras siempre**: con el tono por luz de la chapa, el parabrisas
        # que mira al cielo salía gris claro y se leía como techo. Un cristal visto desde
        # arriba refleja el asfalto: se queda en los tres tonos de abajo.
        m = LUNA_TINTADA if oscura else LUNA
        return g.cr(m, max(0, min(3, round(t * 0.55))))

    def pinta(parte, p, n, t):
        x, y, z = p
        if parte == "lado":
            if z < z_bajo + 0.3:
                return g.cr(mat, t + 1)                # el filo de la cintura
            h = rebanada_h(perfil, z)
            v = rebanada_v(perfil, x)
            if h and v and h[0] + 0.1 < x < h[1] - 0.1 and z < v[1] - 0.4:
                tint = M.tintadas_desde is not None and x < M.tintadas_desde
                return luna(t + (1 if z > v[1] - 1.4 else 0), oscura=tint)
            return g.cr(mat, t)
        if n[2] > 0.82:                                # el techo
            return g.cr(techo_mat or mat, t)
        # el parabrisas y la luna de atrás, a todo lo ancho: los montantes de las
        # esquinas eran del camino «detalle»
        oscura = n[0] < 0 and M.tintadas_desde is not None
        return luna(t + (1 if n[2] > 0.5 else 0), oscura=oscura)
    return pinta


def dibuja(c, M, mat, techo_mat=None):
    """Monta el turismo: ruedas primero (para que la carrocería sepa dónde van los pasos),
    la carrocería, el habitáculo y lo que lleve aparte."""
    W = M.W
    for xr in M.ruedas:
        c.rueda(xr, W, M.r, mat_llanta=M.llanta, tapacubos=M.tapacubos)
    c.extruido(M.cuerpo, -W, W, pintor_cuerpo(c, M, mat, techo_mat))
    Wc = W - M.metida
    perfil = [(x, c.Z(z)) for x, z in M.cabina]
    c.extruido(perfil, -Wc, Wc, pintor_cabina(c, M, mat, perfil, techo_mat), escalar=False)
    z_techo = max(z for _x, z in perfil)
    if M.barras:
        top = [x for x, z in perfil if z > z_techo - 0.05]
        x0, x1 = min(top) + 0.2, max(top) - 0.1
        # Las barras, macizas y pegadas al techo: con patas y hueco salían motas sueltas;
        # así son una raya oscura a cada lado, que es lo que se ve de una barra de verdad.
        for s in (-1, 1):
            yb = s * (Wc - 0.2)
            c.rm.caja(x0, x1, yb - 0.12, yb + 0.12, z_techo, z_techo + 0.5, PLASTICO, -1.0)
    if M.extras:
        M.extras(c, M, mat, z_techo, perfil)


# ---------------------------------------------------------------- los extras


def baca(c, M, mat, z_techo, perfil):
    """La baca del todoterreno: un bastidor bajo a todo lo largo del techo, con una carga
    tapada dentro. Es lo que más rompe la silueta por arriba."""
    Wc = M.W - M.metida
    top = [x for x, z in perfil if z > z_techo - 0.05]
    x0, x1 = min(top) + 0.05, max(top) - 0.05
    for s in (-1, 1):
        c.rm.caja(x0, x1, *sorted((s * (Wc - 0.05), s * (Wc - 0.25))), z_techo + 0.3,
                  z_techo + 1.1, NEUMATICO, 0.6)
    for xx in (x0, x1 - 0.2):
        c.rm.caja(xx, xx + 0.2, -Wc + 0.05, Wc - 0.05, z_techo + 0.3, z_techo + 1.1,
                  NEUMATICO, 0.6)
    c.rm.caja(x0 + 0.1, x1 - 0.1, -Wc + 0.1, Wc - 0.1, z_techo, z_techo + 0.4, NEUMATICO, -0.5)
    c.rm.caja(x0 + 0.5, x0 + 2.0, -Wc + 0.35, Wc - 0.35, z_techo + 0.4, z_techo + 2.0,
              LONA_BACA)


def repuesto(c, M, mat, z_techo, perfil):
    """La rueda de repuesto colgada en el portón, y la baca. **Sobresale 0,45 de la
    cola**: el todoterreno mide 5,8 de chapa y 6,25 con la rueda."""
    rm = c.rm
    xr = -M.largo / 2
    r, ancho = 0.72, 0.45
    rz = 2 * r * 0.85
    zc = c.Z(M.suelo + 3.4)
    n = 14
    for kk in range(n):                                # la banda, de pie y de lado
        t0, t1 = 2 * math.pi * kk / n, 2 * math.pi * (kk + 1) / n
        tm = (t0 + t1) / 2
        rm.r.cara(rm.P(xr - ancho, r * math.cos(t0), zc + rz * math.sin(t0)),
                  rm.V(0, r * (math.cos(t1) - math.cos(t0)), rz * (math.sin(t1) - math.sin(t0))),
                  rm.V(ancho, 0, 0),
                  g.cr(NEUMATICO, rm.tono(0, math.cos(tm), math.sin(tm))))

    def disco(a, b):
        return g.cr(CROMO, 3) if a * a + b * b < 0.2 else g.cr(NEUMATICO, 1)
    rm.r.cara(rm.P(xr - ancho, 0, zc), rm.V(0, -r, 0), rm.V(0, 0, rz), disco, disco=True)
    baca(c, M, mat, z_techo, perfil)


def caja_pickup(c, M, mat, z_techo, perfil):
    """La caja abierta: el suelo hundido con su forro oscuro, los dos laterales y el portón,
    con los pasos de rueda de atrás pintados en los laterales. Se probó con el arco de
    seguridad tras la cabina y se quitó: a escala 1 eran dos motas grises sobre el techo."""
    W = M.W
    xr = -M.largo / 2
    xc = M.caja_hasta
    zs, zt = M.suelo, c.Z(M.borde_caja)
    zf = c.Z(M.suelo_caja)

    def lado(parte, p, n, t):
        x, y, z = p
        # Todo lo que mira hacia dentro de la caja va con el forro oscuro: es lo que la
        # abre vista desde arriba. Con la chapa por dentro salía una losa del color.
        if parte == "lado" and abs(y) < W - 0.01 and z > zf - 0.05:
            return g.cr(CAJA_PICKUP, t)
        if parte == "piel" and n[0] > 0.6 and x < xc - 0.3:
            return g.cr(CAJA_PICKUP, t)
        if parte == "lado" and abs(y) > W - 0.01:
            paso = c.en_paso(x, z)
            if paso == 1:
                return g.cr(NEUMATICO, 0)
            if x < xr + 0.3 and c.Z(M.pilotos[0]) <= z <= c.Z(M.pilotos[1]):
                return PILOTO
            if z > zt - 0.75:
                return g.cr(mat, t + 1)
            if z < zs + 0.45:
                return g.cr(mat, t - 1)
        if parte == "piel" and n[0] < -0.6:
            if abs(y) > W - 0.5 and c.Z(M.pilotos[0]) <= z <= c.Z(M.pilotos[1]):
                return PILOTO
            if z < zs + 0.8:
                return g.cr(mat, t - 1)
        if parte == "piel" and n[2] > 0.8 and abs(y) < W - 0.2 and xr + 0.2 < x < xc - 0.1:
            return g.cr(CAJA_PICKUP, t - 1)            # el forro, visto por dentro
        return g.cr(mat, t)
    # Los bajos de la caja, hasta el suelo de carga.
    c.extruido([(xr, zs), (xc, zs), (xc, zf), (xr, zf)], -W, W, lado, escalar=False)
    # Los laterales y el portón, finos, hasta el borde de la caja.
    for s in (-1, 1):
        y0, y1 = sorted((s * W, s * (W - 0.2)))
        c.extruido([(xr, zf), (xc, zf), (xc, zt), (xr, zt)], y0, y1, lado, escalar=False)
    c.extruido([(xr, zf), (xr + 0.2, zf), (xr + 0.2, zt), (xr, zt)], -W, W, lado,
               escalar=False)


def aleron(c, M, mat, z_techo, perfil):
    """El alerón del deportivo, sobre la cola: una lama en dos patas."""
    xr = -M.largo / 2
    zc = c.Z(max(z for x, z in M.cuerpo if x < 0))
    # Bajo: con la lama a un píxel y pico de la tapa, de perfil salía una torreta.
    for s in (-1, 1):
        c.rm.caja(xr + 0.3, xr + 0.5, *sorted((s * 0.75, s * 0.95)), zc, zc + 0.5, PLASTICO)
    c.rm.caja(xr + 0.05, xr + 0.65, -M.W + 0.1, M.W - 0.1, zc + 0.5, zc + 0.9, NEUMATICO, 0.6)


# ---------------------------------------------------------------- los diez


def _modelos():
    M = {}
    M["utilitario"] = Modelo(
        "utilitario", 5.0, 2.3, 0.8,
        cuerpo=[(-2.5, 0.8), (2.5, 0.8), (2.56, 2.4), (2.35, 3.2), (1.35, 3.7), (-2.45, 3.8),
                (-2.56, 2.6)],
        cabina=[(-2.45, 3.6), (1.35, 3.6), (0.25, 6.3), (-0.05, 6.6), (-2.05, 6.6),
                (-2.42, 6.1)],
        ruedas=(1.62, -1.68), r=0.62, metida=0.2, faros=(2.5, 3.1), pilotos=(2.9, 3.6),
        parrilla=(1.7, 2.3), techo="blanco",
        colores=("celeste", "naranja", "blanco", "granate"))
    M["compacto"] = Modelo(
        "compacto", 5.6, 2.5, 0.8,
        cuerpo=[(-2.8, 0.8), (2.8, 0.8), (2.86, 2.4), (2.6, 3.2), (1.3, 3.9), (-2.7, 4.0),
                (-2.86, 2.6)],
        cabina=[(-2.7, 3.8), (1.3, 3.8), (0.1, 6.4), (-0.3, 6.7), (-1.9, 6.7), (-2.66, 5.5)],
        ruedas=(1.85, -1.9), r=0.65, faros=(2.5, 3.1), pilotos=(3.0, 3.7), parrilla=(1.6, 2.3),
        colores=("azul", "plata", "granate", "blanco"))
    M["berlina"] = Modelo(
        "berlina", 6.4, 2.6, 0.8,
        cuerpo=[(-3.2, 0.8), (3.2, 0.8), (3.26, 2.4), (3.0, 3.2), (1.4, 3.8), (-2.55, 4.0),
                (-3.15, 3.9), (-3.26, 2.6)],
        cabina=[(-2.5, 3.8), (1.3, 3.8), (0.15, 6.1), (-0.25, 6.4), (-1.45, 6.4), (-1.9, 6.0)],
        ruedas=(2.1, -2.15), r=0.67, faros=(2.5, 3.1), pilotos=(3.0, 3.7), parrilla=(1.5, 2.3),
        colores=("grafito", "plata", "marino", "negro"))
    M["ranchera"] = Modelo(
        "ranchera", 6.5, 2.6, 0.8,
        cuerpo=[(-3.25, 0.8), (3.25, 0.8), (3.31, 2.4), (3.05, 3.2), (1.45, 3.8), (-3.15, 4.0),
                (-3.31, 2.6)],
        cabina=[(-3.17, 3.8), (1.35, 3.8), (0.2, 6.2), (-0.2, 6.5), (-2.95, 6.5), (-3.2, 5.9)],
        ruedas=(2.15, -2.2), r=0.67, faros=(2.5, 3.1), pilotos=(3.0, 3.8), parrilla=(1.5, 2.3),
        barras=True, colores=("verde botella", "plata", "arena", "marino"))
    M["suv"] = Modelo(
        "SUV", 6.2, 2.7, 1.2,
        cuerpo=[(-3.1, 1.2), (3.1, 1.2), (3.16, 3.0), (2.9, 4.0), (1.3, 4.6), (-3.0, 4.8),
                (-3.16, 3.4)],
        cabina=[(-3.0, 4.6), (1.25, 4.6), (0.15, 7.3), (-0.2, 7.6), (-2.65, 7.6), (-3.0, 6.5)],
        ruedas=(2.05, -2.05), r=0.76, metida=0.25, faros=(3.3, 3.9), pilotos=(3.7, 4.4),
        parrilla=(2.2, 3.2), tintadas_desde=-0.7, moldura=True,
        barras=True, fz=1.1, llanta=LLANTA_OSCURA,
        colores=("blanco", "grafito", "azul", "arena"))
    M["todoterreno"] = Modelo(
        "todoterreno", 5.8, 2.7, 1.5,
        cuerpo=[(-2.9, 1.5), (2.9, 1.5), (2.96, 4.3), (2.7, 5.0), (-2.9, 5.0)],
        cabina=[(-2.88, 4.8), (1.0, 4.8), (0.55, 8.4), (0.38, 8.6), (-2.75, 8.6), (-2.88, 8.3)],
        ruedas=(1.95, -1.95), r=0.86, metida=0.12, faros=(3.6, 4.3), pilotos=(2.9, 3.5),
        parrilla=(2.6, 4.0), moldura=True, fz=1.12,
        extras=repuesto, colores=("caqui", "blanco", "verde botella", "arena"))
    M["monovolumen"] = Modelo(
        "monovolumen", 6.4, 2.7, 0.9,
        cuerpo=[(-3.2, 0.9), (3.2, 0.9), (3.26, 2.6), (3.0, 3.4), (2.1, 4.1), (-3.1, 4.4),
                (-3.26, 2.8)],
        cabina=[(-3.14, 4.1), (2.05, 4.0), (0.6, 7.6), (0.2, 8.0), (-2.9, 8.0), (-3.14, 7.0)],
        ruedas=(2.2, -2.2), r=0.68, faros=(2.7, 3.3), pilotos=(3.3, 4.2), parrilla=(1.7, 2.5),
        fz=1.1, colores=("plata", "marino", "granate", "blanco"))
    M["pickup"] = Modelo(
        "pickup", 7.0, 2.7, 1.3,
        cuerpo=[(-1.0, 1.3), (3.5, 1.3), (3.56, 3.4), (3.3, 4.4), (1.9, 4.9), (-1.0, 5.0)],
        cabina=[(-1.0, 4.8), (1.85, 4.8), (0.85, 7.5), (0.6, 7.8), (-0.85, 7.8), (-1.0, 7.6)],
        ruedas=(2.4, -2.35), r=0.8, faros=(3.4, 4.0), pilotos=(3.4, 4.6), parrilla=(2.4, 3.6),
        moldura=True, fz=1.05, extras=caja_pickup,
        colores=("arena", "blanco", "negro", "granate"))
    # El suelo de la caja, **más alto que el de verdad**: con la caja honda (2 px) el lateral
    # de delante tapaba el fondo entero, y desde arriba la pickup era una berlina larga.
    M["pickup"].caja_hasta, M["pickup"].suelo_caja, M["pickup"].borde_caja = -1.0, 3.9, 5.0
    M["deportivo"] = Modelo(
        "deportivo", 6.2, 2.8, 0.6,
        cuerpo=[(-3.1, 0.6), (3.1, 0.6), (3.2, 1.8), (3.0, 2.5), (0.8, 3.3), (-2.6, 3.5),
                (-3.1, 3.3), (-3.2, 2.0)],
        cabina=[(-2.8, 3.3), (0.75, 3.2), (-0.45, 5.3), (-0.85, 5.55), (-1.5, 5.55)],
        ruedas=(1.95, -2.0), r=0.7, metida=0.26, faros=(2.0, 2.5), pilotos=(2.6, 3.1),
        parrilla=(1.0, 1.6), fz=0.88, extras=aleron,
        colores=("naranja", "negro", "azul", "plata"))
    M["electrico"] = Modelo(
        "eléctrico", 6.0, 2.6, 0.8,
        cuerpo=[(-3.0, 0.8), (3.0, 0.8), (3.1, 2.2), (2.9, 3.0), (1.3, 3.7), (-2.7, 3.9),
                (-3.05, 3.5), (-3.1, 2.4)],
        cabina=[(-2.75, 3.7), (1.25, 3.6), (0.0, 5.8), (-0.5, 6.1), (-1.4, 6.0)],
        ruedas=(1.95, -2.0), r=0.68, faros=(2.6, 3.0), pilotos=(3.0, 3.4), parrilla=None,
        techo="negro", fz=0.96, tapacubos=True, tira_luz=True, llanta=LLANTA_AERO,
        colores=("blanco", "celeste", "grafito", "verde botella"))
    return M


MODELOS = _modelos()
ORDEN = ("utilitario", "compacto", "berlina", "ranchera", "suv", "todoterreno",
         "monovolumen", "pickup", "deportivo", "electrico")


# ---------------------------------------------------------------- y los de servicio
# **El taxi y la patrulla**, con la carrocería de un turismo y lo que los distingue: la
# librea ancha, no un filete, y lo de encima. Lo que se enciende va **apagado en el
# dibujo**.

AMARILLO = g.material_de(g.AMARILLO_TAXI, "coche taxi")
BLANCO_PATRULLA = g.material_de(g.BLANCO_PATRULLA, "coche patrulla")
AZUL_LIBREA = g.material_de((44, 70, 140), "coche librea")
FILETE_TAXI = g.material_de((42, 44, 56), "coche filete taxi")
# La carcasa de la barra, **con los colores de los rotativos** (`g.LUCES`): la carcasa de
# un rotativo sale de su tipo y no de un color suelto, que es la regla de todos los demás.
BARRA_AZUL = g.material_de(g.LUCES["azul"]["carcasa"][:3], "coche barra azul")
BARRA_ROJA = g.material_de(g.LUCES["rojo"]["carcasa"][:3], "coche barra roja")


def _barra(c, M, mat, z_techo, perfil):
    """La barra de luces, apagada: media azul y media roja, sobre una base. Apunta su
    centro de arriba, el píxel que `turismo()` pinta del color de la carcasa."""
    top = [x for x, z in perfil if z > z_techo - 0.05]
    xm = (min(top) + max(top)) / 2 + 0.2
    c.rm.caja(xm - 0.35, xm + 0.35, -0.9, 0.9, z_techo, z_techo + 0.4, NEUMATICO, 0.4)
    c.rm.caja(xm - 0.3, xm + 0.3, 0.0, 0.85, z_techo + 0.4, z_techo + 1.1, BARRA_AZUL)
    c.rm.caja(xm - 0.3, xm + 0.3, -0.85, 0.0, z_techo + 0.4, z_techo + 1.1, BARRA_ROJA)
    c.luz = (xm, 0.0, z_techo + 1.1)


def _letrero(c, M, mat, z_techo, perfil):
    """El letrero del taxi, a lo ancho: blanco y apagado."""
    top = [x for x, z in perfil if z > z_techo - 0.05]
    xm = (min(top) + max(top)) / 2
    c.rm.caja(xm - 0.3, xm + 0.3, -0.7, 0.7, z_techo, z_techo + 1.0, "blanco", 0.3)
    c.luz, c.luz_tipo = (xm, 0.0, z_techo + 1.0), "taxi"


# **El taxi, de cualquier turismo** sin deportivos y esas cosas: los de calle que hacen de
# taxi de verdad.
TAXIS = ("utilitario", "compacto", "berlina", "ranchera", "suv", "monovolumen", "electrico")


def berlina_servicio(cual, modelo="berlina"):
    """El taxi o la patrulla: el turismo con su librea, su color y lo que lleva encima. La
    patrulla es siempre la berlina; el taxi, el modelo que se le pida de `TAXIS`."""
    M = copy.copy(MODELOS[modelo])
    if cual == "taxi":
        M.franja = (3.0, 3.35, FILETE_TAXI)
        M.extras, M.chapa = _letrero, AMARILLO
    elif cual == "patrulla":
        M.franja = (1.5, 3.2, AZUL_LIBREA)
        M.extras, M.chapa = _barra, BLANCO_PATRULLA
    else:
        raise ValueError(cual)
    return M


# ---------------------------------------------------------------- la pieza


def turismo(modelo, color=None, rumbo="i+"):
    """La pieza de un turismo a un rumbo, con su sombra, su perfil negro por fuera y el
    ancla en el centro de su planta, como la tractora (`_pieza_camion`). `modelo` es el
    nombre de uno de los diez o un `Modelo` hecho aparte (los de servicio, que traen su
    `chapa`); `color`, uno de la paleta de calle (por defecto, el primero del modelo)."""
    M = MODELOS[modelo] if isinstance(modelo, str) else modelo
    mat = getattr(M, "chapa", None) or chapa_de(color or M.colores[0])
    techo_mat = techo_de(M.techo) if M.techo else None
    W, H = g.CAMION_LIENZO
    r = g.Raster(*g.CAMION_ANCLA)
    rm = g._Rumbo(r, g.RUMBOS[rumbo])
    c = Coche(rm, M.fz, M.suelo)
    dibuja(c, M, mat, techo_mat)
    # **Y los faros y los pilotos en punto**, donde se declaran: pintados en la piel, la franja
    # de luz mide medio píxel y en algunos rumbos caía entre dos centros (el eléctrico de
    # frente o el compacto de espaldas salían sin ninguno).
    faros, pilotos = luces_de(c, M)
    rm.luces(faros, pilotos, FARO, PILOTO)
    img = g.contorno_fuera(r.imagen(W, H))
    s = g.Raster(g.CAMION_ANCLA[0] + 2, g.CAMION_ANCLA[1] + 1)
    rs = g._Rumbo(s, g.RUMBOS[rumbo])
    s.cara(rs.P(-M.largo / 2, -M.W - 0.1, 0), rs.V(M.largo, 0, 0), rs.V(0, 2 * M.W + 0.2, 0),
           (0, 0, 0, 60))
    fondo = s.imagen(W, H)
    fondo.alpha_composite(img)
    x0, y0, x1, y1 = fondo.getbbox()
    caja = (x0 - 1, y0 - 1, x1 + 1, y1 + 1)              # un píxel de aire, como todas
    out = fondo.crop(caja)
    out = g.con_ancla(out, g.CAMION_ANCLA[0] - caja[0], g.CAMION_ANCLA[1] - caja[1])
    if c.luz:
        sx, sy = g.Raster.S(rm.P(*c.luz))
        lx, ly = round(g.CAMION_ANCLA[0] + sx) - caja[0], round(g.CAMION_ANCLA[1] + sy) - caja[1]
        # **El píxel del rotativo, del color de su carcasa**, como en `barra_luces()`: la caja
        # sombreada lo aclaraba.
        if c.luz_tipo in g.DESTELLOS:
            out.putpixel((lx, ly), g.LUCES["azul"]["carcasa"])
    return g.con_ruedas(out)


def taxi(modelo="berlina", rumbo="i+"):
    return turismo(berlina_servicio("taxi", modelo), rumbo=rumbo)


def patrulla(rumbo="i+"):
    return turismo(berlina_servicio("patrulla"), rumbo=rumbo)


# **Los aparcados** (los de `coche_en()` del kit): el mismo turismo, con una firma corta —un
# color y hacia dónde mira—. El modelo sale del color, así que no todos son el mismo coche
# y el mismo dibujo sale siempre igual.
# **Ojo**: la chapa se registra siempre como el material «coche aparcado», y `material_de`
# no pisa uno que ya existe: **el color de la primera llamada se queda para todas** las de
# la misma ejecución (cambia el modelo, no el color). Así pinta el original y así se ha
# dejado. Para coches de colores distintos, `turismo(modelo, color, rumbo)`.
APARCADOS = ("utilitario", "compacto", "berlina", "ranchera", "suv", "monovolumen", "electrico")


def aparcado(color, hacia_der=True, atras=False):
    rumbo = {(True, False): "i+", (True, True): "i-", (False, False): "j+", (False, True): "j-"}[(hacia_der, atras)]
    M = copy.copy(MODELOS[APARCADOS[sum(color[:3]) % len(APARCADOS)]])
    M.chapa = g.material_de(tuple(color[:3]), "coche aparcado")
    return turismo(M, rumbo=rumbo)


def catalogo():
    """Las piezas, `(nombre, imagen)`: los diez modelos en sus cuatro colores y sus ocho
    rumbos, y el taxi y la patrulla."""
    fuera = [(f"turismo {m} {col} {r}", turismo(m, col, r))
             for m in ORDEN for col in MODELOS[m].colores for r in g.RUMBOS]
    fuera += [(f"taxi {m} {r}", taxi(m, r)) for m in TAXIS for r in g.RUMBOS]
    fuera += [(f"patrulla {r}", patrulla(r)) for r in g.RUMBOS]
    return fuera
