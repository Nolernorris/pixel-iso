---
name: pixel-iso
description: Dibuja escenas isométricas 2:1 en pixel art por código (Python + Pillow) con el kit de Guremu City; edificios, plantas de casa u oficina por salas, interiores en corte, muebles, calles, jardines, aparcamientos y vehículos (coches, furgonetas, camiones) y personajes pequeños, con rampas de seis tonos, tramado y contorno de 1 px. Úsala cuando pidan una imagen, sprite, escena, maqueta o «dibujo» isométrico o de pixel art, estilo tycoon/citybuilder clásico, o retocar uno hecho con este kit.
---

# Escenas isométricas en pixel art

Esta skill dibuja **por código**: un script de Python monta la escena sobre una `Parcela`
del kit y escribe una PNG. Nada de generar imágenes con IA ni de pintar a mano: volúmenes con
su profundidad, materiales con rampas y tramado, y el contorno al final.

**La carpeta de la skill** (Claude Code la da al cargarla, «Base directory for this skill»;
aquí `SKILL_DIR`) lleva:

- `kit/kit.py` — la `Parcela` y las fachadas. `kit/dibujo.py` — paleta, rampas, tramado,
  contorno, suelos, calle, árboles y mobiliario. Se importan como `import kit as k` y
  `import dibujo as g`.
- `kit/vehiculos.py` y `kit/coches.py` — los vehículos: turismos, furgonetas, camiones de
  caja y articulados, en todas sus orientaciones (ver «Los vehículos»).
- `ejemplos/oficina.py` — **el ejemplo resuelto**: una oficina en corte, por salas, con gente.
  Léelo entero antes de la primera escena; casi todo lo que vas a necesitar está ahí.
- `ejemplos/aparcamiento.py` — el ejemplo de los vehículos: plazas, coches, una furgoneta y
  dos camiones. Léelo antes de poner vehículos en una escena.
- `ver.py` — amplía una PNG ×3 (o compara dos) para mirarla.

Requisitos: Python 3.10+, `pip install pillow numpy`. **No edites los ficheros de la skill**:
la escena nueva va en la carpeta de trabajo del usuario.

## El oficio: lo que hace que salga bien

**Pixel art antes que realismo.** «Más detalle» es más oficio de pixel art, no más render:
un contorno limpio, rampas de color bien escogidas, tramado entre tonos, texturas que siguen
la pendiente 2:1 (hiladas, tablas, baldosas), marcos y alféizares en las ventanas, una sombra
de un píxel bajo una mesa. Nada de degradados suaves, antialias, desenfoques ni fotos.
**Lo que no cabe a la escala, fuera**: un texto de 3 px, los números de un dado, los dedos de
una mano. Se sugiere con dos píxeles o se quita; un detalle ilegible es ruido.

**La luz, siempre del mismo lado**: la cara que mira a `-v` (la izquierda en pantalla), clara;
la que mira a `+u` (la derecha), en sombra; los techos, lo más claro. Las sombras tiran a azul
frío y las luces a crema cálida: eso ya lo hacen las rampas, no lo pelees con colores sueltos.

**Colores por material, no por píxel.** Cada color es un material con su rampa de seis tonos
(`g.material_de((r, g, b), "nombre")`, tonos 0 oscuro … 5 claro) y se pinta con
`g.tono_tramado(mat, t, X, Y)`: `t` con decimales trama los dos tonos vecinos con un damero
Bayer. Un `t` cerca de x,5 en una superficie grande sale a damero visible: úsalo en
transiciones, y tonos más enteros en lo liso.

**El contorno, una vez y al final** (`E.imagen(contorno=True)`): solo perfila la silueta
exterior. Los cantos de dentro se leen por el salto de tono entre caras, no con líneas negras.

**Componer para que cada sitio se lea.** Una planta con varias estancias se hace **por salas**:
cada una con su suelo distinto (baldosa, tarima, damero, moqueta), su color de pared y su
mueble característico, separadas por tabiques bajos con huecos de paso. Si dos salas
contiguas comparten suelo y color, se funden en una. En los interiores, **corte de casa de
muñecas**: paredes altas solo en los dos lados del fondo (`u = 0` y `v = V`), un murete bajo
delante y en el lado derecho; si no, las paredes de delante tapan todo.

**Mirar y corregir.** Una escena no está hecha hasta que la has mirado ampliada y corregido
al menos una vez (ver «El ciclo»).

## Coordenadas

- **Planta en unidades**: 16 unidades por casilla. `u` crece hacia abajo a la derecha en
  pantalla, `v` hacia arriba a la derecha. `v = 0` es el canto de delante. **`z` en píxeles**.
- En pantalla: **x = 2u + 2v, y = u − v − z** (`E.S(u, v, z)`). Una casilla es un rombo de
  64 × 32 px.
- Lo que se ve de un volumen: su techo, la cara que mira a `-v` y la que mira a `+u`. Las
  paredes que miran a otro lado no se pintan, salvo que fuerces su `normal` (las paredes del
  fondo vistas **por dentro**: `normal=(1, 0, 0)` la de `u = 0`, `(0, -1, 0)` la de `v = V`).
- Profundidad: `u − v + z/2`; más es más cerca de la cámara. Hay z-buffer por píxel, así que
  **el orden de dibujo no decide qué tapa a qué**; en un empate gana lo primero, y `delante=`
  empuja algo un pelo hacia la cámara (alfombras `0.05` sobre el suelo, suelos `-0.05`).

## Montar una escena

```python
import os, sys
SKILL_DIR = r"<la carpeta de la skill>"
sys.path.insert(0, os.path.join(SKILL_DIR, "kit"))
sys.dont_write_bytecode = True
import dibujo as g
import kit as k

E = k.Parcela(6, 4, extra=60, margen=1)   # 6 x 4 casillas; 60 px de aire arriba; 1 casilla de borde
k.entorno(E, calles=())                   # hierba alrededor (con calles=("delante",), calle)
# 1. suelos  2. paredes y tabiques  3. muebles y volúmenes  4. sprites (gente, plantas)
E.rect(0, 0, 96, 64, 0, lambda u, v, X, Y: g.tono_tramado("madera", 3.4, X, Y), -0.05)
E.caja(10, 10, 20, 12, 0, 24, k.ventanal("ladrillo", 2), techo="pizarra")
img = E.imagen(contorno=True)             # contorno y recorte
img.save("escena.png")
```

El orden 1-4 no es por tapar (eso lo hace el z-buffer) sino por cabeza: de lo grande a lo
pequeño, sala por sala. `entorno()` y `suelo_parcela()` pintan en el lienzo de fondo, siempre
debajo; no los uses los dos a la vez con margen, que el segundo pisa al primero. La calle
de `entorno()` es solo calzada, sin acera: entre ella y la hierba queda un canto oscuro.

### Lo que hay

En `E` (la `Parcela`): `rect(u, v, a, b, z, col)` y `plano(poligono_convexo, z, col)` para
suelos (`col(u, v, X, Y)` o un color); `caja(u, v, a, b, z0, h, fachada, techo=)`;
`prisma(poligono, z0, h, fachada, techo=)` (polígono **contra las agujas**);
`cilindro(cu, cv, r, z0, h, fachada, techo=)`; `cupula(cu, cv, r, z0, alto, mat)`;
`dos_aguas(u, v, a, b, z, alt, mat, eje="u")`; `cuatro_aguas(...)`;
`pared(p0, p1, z0, h, fachada, normal=)`; `punto(u, v, z, color)`; `linea(p0, p1, color)`;
`sprite(img, u, v, z)`; `imagen()`; `pieza()` (recortada y con ancla, para usarla de sprite).

Una **fachada** es `f(s, z, t, X, Y)` → color RGBA o `None` (hueco): `s` unidades a lo largo
de la pared, `z` px desde su pie, `t` el tono que le toca por luz. Dentro, `E.normal` dice a
qué cara pertenece. Hechas en `k`: `liso(mat, sube)`, `ventanal(mat, plantas)`,
`muro_cortina()`, `chapa(mat)`, `por_tramos((z_hasta, fachada), ...)`,
`con_franja(f, z0, z1, mat)`, `con_dibujo(f, s0, z0, filas, colores)`,
`porton(f, s0, an, al)`, `puerta_cristal(...)`, y `hueco_hondo(E, s0, an, al)` para un hueco
con fondo. Para pintar a mano: `k.pinta(mat, t, X, Y, z)` (con textura y manchas) o
`g.tono_tramado(mat, t, X, Y)`.

Otras piezas en `k`: `arbol_en(E, u, v, "hoja"|"pino"|"roble"|"arce"|"olivo")`,
`farola_en`, `macetero_en`, `palets`, `rotulo`, `tronco_cono`, `cilindro_tumbado`, `cuadro`,
`suelto(fn_dibujo, w, h)` (convierte una función `fn(px, img, x, suelo_y)` en sprite) y
`lamina([imgs])` para juntar varias. En `g`: los materiales de `g.MAT` (hierba, tierra,
asfalto, arena, agua, hormigon, ladrillo, madera, teja, metal, acero, pizarra, blanco, verde,
azul, cobre, bronce, nogal, carbon…), `g.cr(mat, 0..5)`, `g.suelo(mat)`, `g.calle(lados)`,
`g.banco`, `g.papelera`, `g.seto`, `g.mata`, `g._copa` (una masa de hojas) y `g.SIN_LUZ = True`
para pintarlo todo con las luces apagadas.

## Escalas que funcionan

| Cosa | Medida |
|---|---|
| Casilla | 16 × 16 unidades (rombo de 64 × 32 px) |
| Persona sentada | sprite de **9 × 10 px** (ver `persona()` del ejemplo) |
| Pared alta de interior | 24-26 px; murete de delante 4 px; tabique entre salas 6 px |
| Mesa de trabajo | 15 × 7 u, tablero a z 6 |
| Silla | asiento 3 × 3 u a z 3-4, respaldo de 3 a 4,5 px |
| Cama | 12 × 7 u, colchón a z 2,5-4 |
| Monitor de tubo | 3,6 u de ancho, 5,5 px de alto |
| Hueco de paso | 6-10 u |
| Planta de edificio | 8-10 px de alto |

Cuando algo «no se lee», casi siempre es escala: o es demasiado pequeño para su detalle (se
quita detalle), o tapa lo que importa (se baja; el respaldo de una silla de espaldas a
cámara, más bajo, o tapa a quien se sienta).

## Los sprites y la gente

Los personajes y las plantas son **sprites de caracteres** (ver `pinta_lista()` y `persona()`
del ejemplo): una lista de filas de texto y un diccionario carácter → color, con el ancla en el
pie. Se meten con `E.sprite(img, u, v, z)`. Para que no salgan a rayas, deja **`u − v`
entero** en el ancla (`v = u - round(u - v)`), como hace el ejemplo con las macetas.

## Los vehículos

Coches, furgonetas y camiones, en `kit/vehiculos.py` (`import vehiculos as v`) y
`kit/coches.py` (`import coches as c`). Son **piezas sueltas**, ya con su sombra y su perfil
negro, y el ancla en el centro de su planta: se meten con **`k.vehiculo_en(E, pieza, u, v)`**,
no con `E.sprite` a secas. `sprite()` da a todo el dibujo la profundidad de su ancla, y la mitad
del vehículo que asoma hacia la cámara quedaba detrás del suelo y de las rayas que tiene
delante: salía cortado en diagonal. `vehiculo_en` le da el margen (`k.DELANTE_VEHICULO`). El
ejemplo resuelto es `ejemplos/aparcamiento.py`.

**Lo que hay:**

| Pieza | Llamada | Orientaciones |
|---|---|---|
| Turismo (10 modelos) | `c.turismo(modelo, color, rumbo)`; `c.ORDEN` los modelos, `c.MODELOS[m].colores` sus cuatro colores, `c.CALLE` la paleta (12 nombres) | los 8 `RUMBOS` |
| Taxi y patrulla | `c.taxi(modelo, rumbo)` (modelos de `c.TAXIS`), `c.patrulla(rumbo)` | 8 |
| Camión de caja, furgoneta, furgoneta de obra, ambulancia, bomberos, furgón blindado | `v.camion(...)`, `v.furgoneta`, `v.furgoneta_obra`, `v.ambulancia`, `v.bombero`, `v.blindado`, con `hacia_der=` y `atras=`; las intermedias con `recto=True` (y `perfil=True` de lado) | 4 + 4 |
| Tractora, remolque, contenedor | `v.tractora(color, rumbo)` (`"roja"`, `"azul"`, `"blanca"`), `v.tractora_terminal(rumbo)`, `v.remolque(rumbo)`, `v.contenedor_rumbo(mat, rumbo)` (un material como `"azul"`, `"teja"`, `"verde"`, o una librea: `"tentaculo"`, `"sonrisa"`) | 8 |
| A medida | `v.vehiculo(mat_caja, mat_cabina, largo, alto, ancho, ...)` | 4 + 4 |

**Los faros y los pilotos**, encendidos o apagados: por defecto son píxeles de luz, en su sitio
en todos los rumbos. Para coches aparcados, una escena de día o si te lo piden, llama a
**`v.luces_encendidas(False)`** antes de pintar los vehículos: el faro sale de cristal gris, el
piloto rojo oscuro y las luces de gálibo de la tractora, ámbar sucio. Vale también para los
turismos de `coches.py`. `v.luces_encendidas(True)` los vuelve a encender para lo que venga
después; mezclar unos y otros en la misma escena es pintar cada grupo con su llamada delante.

**Los rumbos** (`v.RUMBOS`) dicen hacia dónde mira el morro: `"i+"` hacia `+u` (abajo a la
derecha en pantalla), `"i-"` hacia `-u` (arriba a la izquierda), `"j+"` hacia `-v` (abajo a
la izquierda), `"j-"` hacia `+v` (arriba a la derecha), y las diagonales, rectas en
pantalla: `"der"`, `"izq"`, `"arriba"`, `"abajo"`. En los de cabina y caja, `hacia_der` y
`atras` dan las cuatro primeras: (`True`, `False`) `i+`, (`True`, `True`) `i-`, (`False`,
`False`) `j+`, (`False`, `True`) `j-`; con `recto=True`, `perfil=True` es de lado (a la
derecha o, con `hacia_der=False`, a la izquierda) y sin él, de frente o de espaldas (`atras`).

**Colocarlos** con los atajos de `k`:

- `k.camion_en(E, u, v, rumbo, color, carga=None, remolque=True)`: la tractora en `(u, v)` y
  el remolque detrás, a su enganche, con un contenedor si se da `carga`. Solo los cuatro
  rumbos de la retícula. De punta a punta mide unas 14 unidades: casi una casilla.
- `k.furgo_en(E, u, v, hacia_der, atras, fn=v.camion)`: la furgoneta, o el de cabina y caja
  que se pase en `fn`.
- `k.coche_en(E, u, v, color, hacia_der, atras)`: un turismo aparcado, el modelo según el
  color. **Ojo**: el color de la primera llamada se queda para todos los de la misma
  ejecución (es como pinta el original). Para coches de colores distintos, usa
  `k.vehiculo_en(E, c.turismo(modelo, color, rumbo), u, v)`, como el ejemplo.
- Para el resto (las diagonales, los recto), la pieza a mano con `k.vehiculo_en`.

**La escala**: van a escala de ciudad, a un tercio de casilla.

| Vehículo | Planta (unidades) | Alto (px) |
|---|---|---|
| Turismo | 5-7 × 2,3-2,8 | 5-10 (el deportivo, el más bajo) |
| Furgoneta | 7 × 2 | 8 |
| Camión de caja | 8 × 2 | 9 |
| Tractora | 6,4 × 3 | 8,5 (11 con los escapes) |
| Tractora + remolque | unas 14 × 3 | contenedor encima: 12 |

Una plaza de turismo que se lee bien: **4 de ancho y 9 de largo**; un muelle para el
articulado, 12 × 18. A esta escala una persona de pie mediría 7-8 px: las del ejemplo de la
oficina (9 × 10 sentadas) son de interior y al lado de un coche salen gigantes, así que no
mezcles las dos escalas en una escena. Como con cualquier sprite, el ancla con **`u − v`
entero** (en el ejemplo, filas en `u = 6` y `u = 28` y plazas en `v = 17, 21, 25…`).

## El ciclo: escribir, lanzar, mirar, corregir

1. **Plano primero.** Antes de escribir código, reparte la parcela: qué sala va en qué
   rango de `u` y `v`, qué suelo y qué pared lleva cada una, dónde están los huecos de paso.
   Una tabla corta basta. Elige el tamaño en casillas para que quepa todo a la escala de arriba.
2. **Parte del ejemplo.** Copia `ejemplos/oficina.py` a la carpeta de trabajo con otro nombre,
   apunta `KIT` a `SKILL_DIR/kit` y rehaz `escena()` y las salas. Reutiliza sus piezas
   (`caja`, `mesa`, `silla`, `crt`, `persona`, `maceta`, `tabique`, `ventana`, `cartel`).
3. **Lanza**: `python escena.py`. Tarda segundos; el kit es Python puro.
4. **Mira**: `python SKILL_DIR/ver.py escena.png` y **lee la `_x3.png` con la herramienta de
   leer imágenes**. Para un detalle, `--recorte x0,y0,x1,y1`; para comparar antes y después,
   pásale dos PNG.
5. **Repasa con esta lista** y corrige; luego vuelve al 3. **Al menos una vuelta de
   corrección** antes de enseñarla, y di qué corregiste.
   - ¿Se distingue cada sala de un vistazo (suelo, pared, mueble)?
   - ¿Hay algo flotando o hundido (un `z` mal), o cortado arriba (sube `extra`)?
   - ¿Algo tapa lo importante (gente detrás de respaldos, paredes de delante)?
   - ¿Colores vecinos que se funden? Sube el contraste de material, no añadas líneas.
   - ¿Damero visible en superficies lisas (tono cerca de x,5)? ¿Sprites a rayas?
   - ¿Hay detalle ilegible a esta escala? Fuera.
6. Entrega la PNG a tamaño natural y la ampliada, y el script, que es lo que permite
   retocarla luego.
