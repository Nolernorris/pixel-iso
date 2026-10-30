# pixel-iso

Un plugin de Claude Code con una skill para **dibujar escenas isométricas en pixel art**:
edificios, una casa o una oficina por salas, muebles, jardines, gente pequeña, coches,
furgonetas y camiones.

Claude escribe un script de Python que monta la escena con el kit de dibujo de Guremu City
(rampas de seis tonos, tramado, contorno de 1 px, volúmenes con profundidad), lo lanza,
mira la imagen ampliada, la corrige y te entrega la PNG y el script.

## Nota del autor

Guremu City es un proyecto personal donde he creado una ciudad para reflejar lo que hago en mi vida
y lo que trabajo con Claude Code en un mapa isométrico. Siempre me han gustado los juegos isométricos
city builders, estilo SimCity, Transport Tycoon, etc. Les tengo nostalgia de pequeño y he
aprovechado a Claude para realizar este capricho. Al final, me ha gustado el resultado, dedicando
tiempo para perfeccionarlo a mi gusto. A gente que conozco le ha gustado y aunque es para algo
personal, lo comparto por las críticas recibidas. Obviamente no es perfecto, pero si a alguien más
le gusta ya estoy contento ^^

## Requisitos

- Claude Code.
- Python 3.10 o más nuevo, con Pillow y NumPy: `pip install pillow numpy`.

## Instalarlo

**Desde Claude Code**, si está publicada en GitHub:

    /plugin marketplace add Nolernorris/pixel-iso
    /plugin install pixel-iso@pixel-iso

**O a mano, para siempre**: copia la carpeta `pixel-iso` entera (la que tiene este fichero) a la
carpeta de skills de tu usuario de Claude Code, de modo que quede así:

- Windows: `C:\Users\<tú>\.claude\skills\pixel-iso\.claude-plugin\plugin.json`
- macOS / Linux: `~/.claude/skills/pixel-iso/.claude-plugin/plugin.json`

En la siguiente sesión se carga sola. `claude plugin list` la enseña como
`pixel-iso@skills-dir`.

**Solo para probarla**, sin copiar nada: `claude --plugin-dir ruta/a/pixel-iso`.

## Lo que gasta

**Medido en dos sesiones simuladas**, no en uso real: el 30-10-2026, con Claude Code 2.1.314 y
Claude Opus 5.5, pidiendo de una vez una escena completa (una cafetería con terraza y el
aparcamiento de un supermercado con coches, furgoneta y camión). Claude la dibujó, la miró y la
corrigió de dos a cuatro veces por su cuenta.

| | Cafetería | Supermercado |
|---|---|---|
| Pasos | 21 | 37 |
| Tiempo | 6 min | 6,5 min |
| Tokens escritos | 33.000 | 35.000 |
| Tokens leídos (casi todos de caché) | 1,56 millones | 1,99 millones |
| Coste a precio de la API | 1,65 $ | 1,77 $ |

Casi todo lo leído es lo mismo una y otra vez: en cada paso Claude Code vuelve a mandar lo que
lleva de conversación, y eso sale de la caché, que cuesta mucho menos. Con un plan Pro o Max no
se paga aparte, pero cuenta para su límite. Con otros modelos, o pidiendo retoques después, no
lo hemos medido.

## Actualizarla

Cada versión nueva sube el número de `plugin.json` y se cuenta en el `CHANGELOG.md`. Si la
instalaste desde Claude Code, **activa la actualización automática una vez**: `/plugin` →
pestaña **Marketplaces** → `pixel-iso` → **Enable auto-update**. Desde entonces, al abrir
Claude Code se baja la versión nueva y te avisa; `/reload-plugins` la aplica sin reiniciar.

Sin activarla, cuando quieras: `/plugin marketplace update pixel-iso`. Si la copiaste a mano,
vuelve a copiar la carpeta.

## Usarlo

Pídeselo con palabras normales, por ejemplo:

- «Dibújame en isométrico pixel art mi piso: salón, cocina americana, dos dormitorios y un baño.»
- «Una cafetería en una esquina, con terraza y tres mesas fuera.»
- «Una nave industrial con dos portones, palets en la entrada y un par de árboles.»
- «Un aparcamiento de supermercado con coches, una furgoneta de reparto y un camión descargando.»

O llama a la skill por su nombre: `/pixel-iso una biblioteca de dos plantas en corte`.

Claude te enseñará la imagen y te dirá qué ha corregido al mirarla. Para retocarla, pídelo
sobre la marcha («la cocina más grande», «suelo de baldosa en el baño», «una planta en la
esquina»): rehace el script y vuelve a mirar.

## Los vehículos

Cada vehículo es una pieza hecha, con su sombra y su perfil negro, dibujada en **las ocho
direcciones**: las cuatro de la retícula (en diagonal en pantalla) y las cuatro intermedias
(rectas en pantalla: arriba, abajo, izquierda y derecha), cada una con su dibujo, no girado.

- **Turismos: 10 modelos**, cada uno en cuatro colores de una paleta de calle de 12:
  utilitario, compacto, berlina, ranchera, SUV, todoterreno, monovolumen, pickup, deportivo y
  eléctrico. Y el **taxi** (sobre siete de esos modelos) y el **coche patrulla**.
- **Furgonetas y camiones de caja**: camión de caja, furgoneta, furgoneta de obra, ambulancia,
  bomberos y furgón blindado, o uno a medida (largo, alto, ancho y los colores de la caja y la
  cabina).
- **Camión articulado**: la tractora en rojo, azul o blanco, el remolque y un contenedor encima,
  liso o con librea pintada. Y la tractora de terminal, la que mueve remolques en un puerto.
- **Los faros y los pilotos** son píxeles en su sitio y se ven en todos los rumbos en que esa
  punta mira a la cámara. Se pueden pintar **apagados** (cristal gris y rojo oscuro), para
  coches aparcados o escenas de día: `vehiculos.luces_encendidas(False)`. Por defecto van
  encendidos.

Van a escala de ciudad, a un tercio de casilla: un turismo mide unas 6 × 2,5 unidades y una
plaza de aparcamiento que se lee bien, 4 × 9. El ejemplo del aparcamiento enseña a ponerlos.

## Qué hay dentro

- `skills/pixel-iso/SKILL.md` — lo que Claude lee: cuándo usarla y el oficio.
- `skills/pixel-iso/kit/` — el kit de dibujo (`kit.py` y `dibujo.py`) y los vehículos
  (`vehiculos.py` y `coches.py`: turismos, furgonetas y camiones en todas sus orientaciones).
- `skills/pixel-iso/ejemplos/oficina.py` — una oficina por salas, el ejemplo resuelto. Para
  verla: `python skills/pixel-iso/ejemplos/oficina.py` deja `oficina.png` donde lo lances.
- `skills/pixel-iso/ejemplos/aparcamiento.py` — un aparcamiento con coches, una furgoneta y
  dos camiones, el ejemplo de los vehículos. Igual: deja `aparcamiento.png` donde lo lances.
- `CHANGELOG.md` — lo que trae cada versión.
- `skills/pixel-iso/ver.py` — amplía una PNG ×3 para mirarla (`python ver.py escena.png`).

## Licencia

MIT: úsala, cámbiala y compártela, con la nota de autoría (`LICENSE`).
