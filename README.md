# pixel-iso

A Claude Code plugin with a skill that **draws isometric pixel art scenes by code**:
buildings, a house or an office room by room, furniture, gardens, small people, cars, vans
and trucks. Claude writes a short Python script that builds the scene with the drawing kit
from *Guremu City* (six-tone colour ramps, dithering, 1 px outline, volumes with real depth),
runs it, looks at the image enlarged, fixes what reads badly, and hands you the PNG and the
script.

No AI image generation and no hand painting: every pixel comes from the kit, so the result is
consistent and you can keep editing the script.

| An office, room by room | A car park with vehicles |
| --- | --- |
| `skills/pixel-iso/ejemplos/oficina.py` | `skills/pixel-iso/ejemplos/aparcamiento.py` |

## A note from the author

Guremu City is a personal project: a city I built to reflect, on an isometric map, what I do
in my life and what I work on with Claude Code. I've always loved isometric city builders, the
SimCity and Transport Tycoon kind. They take me back to when I was a kid, and I used Claude to
indulge this whim. In the end I liked the result, and I spent time polishing it to my taste.
People I know liked it too, so even though it's something personal, I'm sharing it because of
the feedback I got. Obviously it isn't perfect, but if someone else likes it, I'm already happy ^^

## Requirements

- Claude Code.
- Python 3.10 or newer with Pillow and NumPy: `pip install pillow numpy`.

## Install

From Claude Code:

```
/plugin marketplace add Nolernorris/pixel-iso
/plugin install pixel-iso@pixel-iso
```

Or copy this folder to `~/.claude/skills/pixel-iso/` (on Windows,
`C:\Users\<you>\.claude\skills\pixel-iso\`): it loads by itself in the next session.
To try it once without installing: `claude --plugin-dir path/to/pixel-iso`.

## What it uses

**Measured in two simulated sessions**, not real use: on 30-10-2026, with Claude Code 2.1.314
and Claude Opus 5.5, asking in one go for a complete scene (a café with a terrace, and a
supermarket car park with cars, a van and a truck). Claude drew it, looked at it and fixed it
two to four times on its own.

| | Café | Supermarket |
|---|---|---|
| Steps | 21 | 37 |
| Time | 6 min | 6.5 min |
| Tokens written | 33,000 | 35,000 |
| Tokens read (almost all from cache) | 1.56 million | 1.99 million |
| Cost at API prices | $1.65 | $1.77 |

Most of what it reads is the same thing again and again: at every step Claude Code sends the
conversation so far, and that comes from the cache, which costs much less. On a Pro or Max plan
there is no extra charge, but it counts towards the plan's limit. We have not measured other
models, or asking for changes afterwards.

## Updating

Each new version bumps the number in `plugin.json` and is described in `CHANGELOG.md`. If you
installed it from Claude Code, **turn on auto-update once**: `/plugin` → **Marketplaces** tab →
`pixel-iso` → **Enable auto-update**. From then on Claude Code fetches new versions when it
starts and tells you; `/reload-plugins` applies them without restarting.

Without it, whenever you like: `/plugin marketplace update pixel-iso`. If you copied the folder
by hand, copy it again.

## Use

Just ask, for example:

- "Draw my flat in isometric pixel art: living room, open kitchen, two bedrooms and a bathroom."
- "A corner café with a terrace and three tables outside."
- "A warehouse with two loading doors, pallets at the entrance and a couple of trees."
- "A supermarket car park with cars, a delivery van and a truck unloading."

Or call the skill by name: `/pixel-iso a two-storey library in cutaway`.

Claude shows you the image and tells you what it fixed after looking at it. To change
something, just say so ("bigger kitchen", "tiles in the bathroom", "a plant in the corner").

## Vehicles

Every vehicle is a ready-made piece, with its shadow and its black outline, drawn in **all
eight directions**: the four along the grid (diagonal on screen) and the four in between
(straight on screen: up, down, left and right), each one its own drawing, not a rotated copy.

- **Cars: 10 models**, each in four colours from a 12-colour street palette: city car,
  hatchback, saloon, estate, SUV, off-roader, people carrier, pickup, sports car and electric.
  Also a **taxi** (on seven of those models) and a **police car**.
- **Vans and box trucks**: box truck, van, works van, ambulance, fire engine and armoured van,
  or one made to measure (length, height, width and the colours of the box and the cab).
- **Articulated lorry**: the tractor unit in red, blue or white, the trailer, and a shipping
  container on top, plain or with a printed livery. And a yard tractor, the kind that moves
  trailers around a port.
- **Headlights and tail lights** are real pixels in their place, so they show from every side
  the vehicle faces. They can be drawn **switched off** (grey glass and dark red) for parked
  vehicles or daytime scenes: `vehiculos.luces_encendidas(False)`. They are on by default.

They are at city scale, a third of a tile: a car is about 6 × 2.5 units and a parking space
that reads well is 4 × 9. The car park example shows how to place them.

## What's inside

- `skills/pixel-iso/SKILL.md` — what Claude reads: when to use it and the craft.
- `skills/pixel-iso/kit/` — the drawing kit (`kit.py`, `dibujo.py`) and the vehicles
  (`vehiculos.py`, `coches.py`: cars, vans and trucks in every orientation).
- `skills/pixel-iso/ejemplos/` — two worked examples: an office and a car park. Run one with
  `python skills/pixel-iso/ejemplos/oficina.py` and it writes `oficina.png` where you run it.
- `CHANGELOG.md` — what each version brings.
- `skills/pixel-iso/ver.py` — enlarges a PNG ×3 (or puts two side by side) to look at it.

The code, the comments and the skill are in Spanish; Claude reads them fine and answers in
your language.

## License

MIT — see `LICENSE`.
