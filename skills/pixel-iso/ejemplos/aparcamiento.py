"""Un aparcamiento con coches, una furgoneta y dos camiones: el ejemplo de los vehículos.

Dos filas de plazas con el pasillo en medio, dos muelles de carga (el camión articulado y
el de caja), la caseta de la entrada con su barrera y una franja de hierba con árboles. 16
unidades por casilla; `E.S(u, v, z)`: x = 2u + 2v, y = u - v - z.

Se lanza desde cualquier sitio (`python ruta/a/aparcamiento.py`) y deja `aparcamiento.png`
en la carpeta desde donde se lanza.
"""
import os
import sys

# El kit vive en `../kit/`, al lado de esta carpeta: se importa desde ahí, se lance de donde se lance.
KIT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kit")
sys.path.insert(0, KIT)
sys.dont_write_bytecode = True

import coches as c  # noqa: E402
import dibujo as g  # noqa: E402
import kit as k  # noqa: E402
import vehiculos as v  # noqa: E402

AQUI = os.getcwd()                       # la PNG, donde se lance

U, V = 80, 80           # 5 x 5 casillas
# Las plazas: un turismo mide 5-7 unidades de largo y 2,3-2,8 de ancho.
PASO = 4                # ancho de plaza
ATRAS = (1, 10)         # la fila de atrás, de u = 1 a 10
DELANTE = (24, 33)      # la de delante; entre las dos, el pasillo
EJE = 17                # la raya del pasillo
V0, V1 = 15, 75         # las plazas, de v = 15 a 75; delante queda la entrada
N_PLAZAS = (V1 - V0) // PASO
# Los muelles (u0, u1, v0, v1): el articulado mide unas 14 de punta a punta; el de caja, 8.
MUELLES = ((39, 51, 6, 24), (39, 51, 30, 48))
HIERBA = 58             # de aquí a U, hierba con árboles

ASFALTO = g.material_de((96, 96, 100), "aparcamiento asfalto")
PINTURA = (226, 222, 204, 255)
AMARILLO = v.AMARILLO_OBRA


def raya_plazas(u, vv, fila):
    """¿Cae en una raya de las plazas de `fila`? Las separaciones y la raya del fondo."""
    u0, u1 = fila
    if not (u0 <= u <= u1 and V0 - 0.5 <= vv <= V1 + 0.5):
        return False
    junto = abs(((vv - V0 + PASO / 2) % PASO) - PASO / 2) < 0.45
    fondo = (u - u0 < 0.9) if fila == ATRAS else (u1 - u < 0.9)
    return junto or fondo


def suelo(u, vv, X, Y):
    if u >= HIERBA:
        return g.tono_tramado("hierba", 3.0, X, Y)
    if raya_plazas(u, vv, ATRAS) or raya_plazas(u, vv, DELANTE):
        return PINTURA
    for u0, u1, v0, v1 in MUELLES:
        if u0 <= u <= u1 and v0 <= vv <= v1:
            if min(u - u0, u1 - u, vv - v0, v1 - vv) < 0.9:          # el recuadro
                return AMARILLO
            if min(u - u0, u1 - u) < 2.5 and int(u + vv) % 3 == 0:     # y el rayado, en los bordes
                return AMARILLO
    if EJE - 0.4 < u < EJE + 0.4 and V0 <= vv and int(vv) % 6 < 3:    # la raya del pasillo
        return PINTURA
    return g.tono_tramado(ASFALTO, 2.6, X, Y)


def plaza(n):
    """El centro de la plaza `n` a lo largo de v."""
    return V0 + PASO / 2 + n * PASO


def escena():
    E = k.Parcela(U // 16, V // 16, extra=40, margen=1)
    k.entorno(E, calles=())
    E.rect(0, 0, U, V, 0, suelo, -0.05)
    # Un bordillo bajo entre el asfalto y la hierba.
    E.caja(HIERBA - 1, 0, 1, V, 0, 1.5, k.liso("hormigon"), techo="hormigon")

    # ---- la fila de atrás: el morro hacia el fondo (i-). El centro del coche en el de la
    # plaza, con u - v entero (sin rayas).
    atras = ["compacto azul", "suv blanco", None, "berlina grafito", "utilitario naranja",
             None, "ranchera verde botella", "electrico celeste", None, "monovolumen plata",
             "todoterreno caqui", None, "deportivo naranja", "compacto granate", None]
    for n, coche in enumerate(atras):
        if coche:
            modelo, color = coche.split(" ", 1)
            k.vehiculo_en(E, c.turismo(modelo, color, "i-"), 6, plaza(n))

    # ---- la de delante: el morro hacia la cámara (i+), y una furgoneta
    delante = ["berlina marino", None, "pickup arena", "compacto plata", None, "furgo",
               None, "suv grafito", "utilitario celeste", None, "ranchera plata", None,
               "electrico blanco", None, "berlina negro"]
    for n, coche in enumerate(delante):
        if coche == "furgo":
            k.furgo_en(E, 28, plaza(n), hacia_der=True, atras=False)
        elif coche:
            modelo, color = coche.split(" ", 1)
            k.vehiculo_en(E, c.turismo(modelo, color, "i+"), 28, plaza(n))

    # ---- los muelles: el articulado con su contenedor (la tractora delante, mirando a -v,
    # y el remolque detrás) y el de caja, de espaldas
    k.camion_en(E, 45, 11, "j+", "roja", carga="azul")
    k.furgo_en(E, 45, 37, hacia_der=False, atras=True, fn=v.camion)

    # ---- la caseta de la entrada y la barrera, cruzando el pasillo
    E.caja(2, 2, 7, 7, 0, 12, k.ventanal("blanco", 1, alto_planta=12, an=3, al=4, desde=4),
           techo="pizarra")
    barrera = lambda s, z, t, X, Y: g.cr("senal" if int(s / 2) % 2 else "blanco", round(t))  # noqa: E731
    E.caja(11, 5, 12, 0.8, 5, 1.2, barrera, techo="blanco")
    E.caja(10.2, 4.5, 1.2, 1.8, 0, 6.5, k.liso("acero"), techo="acero")

    # ---- farolas en el pasillo y árboles en la hierba
    for vv in (24, 48, 72):
        k.farola_en(E, EJE, vv)
    for n, vv in enumerate((8, 26, 44, 62)):
        k.arbol_en(E, 69, vv, ("roble", "arce", "olivo", "roble")[n], semilla=n)
    return E.imagen(contorno=True)


if __name__ == "__main__":
    assert N_PLAZAS == 15
    img = escena()
    ruta = os.path.join(AQUI, "aparcamiento.png")
    img.save(ruta)
    print(ruta, img.size)
