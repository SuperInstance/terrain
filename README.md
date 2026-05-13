# Terrain

You remember text adventures. Dark rooms. A skeleton in the corner holding a rusty key. A lantern that's almost out. The prose painted everything — you supplied the 3D in your head.

Now imagine walking through that room instead of imagining it.

`terrain` parses MUD room descriptions and compiles them into 3D scenes you can walk through in a browser. The MUD doesn't know it's being rendered. It just serves rooms. Terrain sits between the text world and the visual one — the chart table where you translate between them.

## How It Works

Write a room file:

```
Room: wheelhouse
Description: The wheelhouse is the nerve center of the vessel.
  Navigation electronics line the console in careful rows.
  Radar and chartplotter displays cast pale light across polished teak trim.
Exits: aft -> aft_cockpit, down -> galley  
Objects: helm_wheel, radar_display, compass_rose
```

Run the compiler:

```bash
python3 terrain_core.py rooms.mud
```

Open the viewer — your rooms are now a 3D space. Drag to look around. Click exits to walk. Each object in the room description becomes a 3D primitive with appropriate materials (metal → metallic, wood → wood grain, water → reflective).

## Why

MUD rooms are the purest form of spatial description — a room is defined by what's in it, what connects to it, and what mood it creates. Terrain makes that description visible without losing the text. Both versions coexist. The room file is always the canonical form.

## Quick Start

```bash
git clone https://github.com/SuperInstance/terrain.git
cd terrain
python3 terrain_core.py rooms.mud
# Open index.html in a browser
```

## License

Apache 2.0 — Cocapn fleet infrastructure.
