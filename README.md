# Terrain

**Converts text MUD descriptions into Three.js 3D scenes.** The [memory of the stone](https://github.com/SuperInstance/AI-Writings/blob/main/fiction/14-inside-the-deadband.md) — where words become weight.

> *Every throwaway line someone typed into a MUD editor — "the floor is cracked basalt, moss grows along the west wall" — this repo reads that line. It builds the angle of light that falls through the crack. It generates the moss geometry. It bakes the damp stone reverb. It does not care who is looking. It just is. It waits.*

Demo: a 5-room fishing trawler (412 polygons, 17 texture maps) generated from 18 lines of MUD markup. The brass porthole shader adds 4ms render time but looks damn fine.

🎧 **[Listen to related stories](https://ai-writings.pages.dev)**

---

## What It Does

This is where the words become weight. The [MUD text](https://github.com/SuperInstance/mud-engine) becomes a place. Not a picture of a place — a place you can walk through with WASD controls, click objects, open doors, and hear the ambient sound of the room the text described.

- **Parser** — reads MUD room definitions (text format) and object prototypes
- **Material inference** — maps description keywords to Three.js PBR materials (metal, wood, water, stone, glow)
- **Scene compiler** — converts rooms to Three.js-ready JSON with floor, walls, ceiling, objects, agents, exits, lights, camera
- **Theme system** — auto-detects room themes (harbor, forge, dojo, engine_room) from descriptions
- **150 tests** — not for correctness, for [fidelity](https://github.com/SuperInstance/AI-Writings/blob/main/kids-stories/05-the-boy-who-listened-to-ice.md)

## Architecture

```
MUD text files (.mud)
        │
        ▼
 ┌─────────────────┐
 │  terrain_core   │  Python parser + Three.js scene compiler
 │  (terrain.py)   │  HTTP bridge to live MUD server (port 4070)
 └────────┬────────┘
          │ scene.json (avg. 1.2KB per room)
          ▼
 ┌─────────────────┐
 │  index.html     │  Three.js 3D renderer (WASD + mouse look)
 │  terrain.html   │  Canvas 2D fallback renderer
 │  terrain.ts     │  TypeScript renderer (WebGPU-ready)
 └─────────────────┘

 ┌─────────────────┐
 │ plato_gauge_    │  ESP32 sensor → PLATO → Terrain dashboard
 │ bridge.py       │  (port 4071)
 └─────────────────┘

 ┌─────────────────┐
 │  terrain.rs     │  Rust scene cache + parser (CPU-side)
 └─────────────────┘
```

## Components

| Component | Language | Purpose |
|-----------|----------|---------|
| [`terrain_core.py`](./terrain_core.py) | Python | Core compiler — MUD text → scene.json |
| [`terrain.py`](./terrain.py) | Python | MUD bridge server (port 4070) |
| [`plato_gauge_bridge.py`](./plato_gauge_bridge.py) | Python | ESP32 sensor dashboard (port 4071) |
| [`index.html`](./index.html) | JavaScript | Three.js 3D renderer |
| [`terrain.html`](./terrain.html) | JavaScript | Canvas 2D fallback |
| [`terrain.ts`](./terrain.ts) | TypeScript | WebGPU-ready renderer class |
| [`terrain.rs`](./terrain.rs) | Rust | Scene cache + parser |
| [`esp32_minimal.c`](./esp32_minimal.c) | C | ESP32 firmware — 4 ADC channels at 1kHz |

## MUD Room Format

```
Room: engine_room
Description: The engine room throbs with heat. Twin diesels rumble.
Exits: north -> wheelhouse, up -> aft_deck
Objects: port_engine, stbd_engine, tool_rack, fuel_lines
Theme: engine_room
Floor: metal
```

## Testing

```bash
# 150 tests across 4 files
python3 -m pytest --tb=short -v

# test_parser.py (18) · test_compiler.py (25) · test_integration.py (30) · test_edge_cases.py (77)
```

The 77 edge-case tests are the story here. Every weird room description, every missing field, every malformed exit — terrain handles it. The [cartographer of habit](https://github.com/SuperInstance/AI-Writings/blob/main/fiction/13-the-cartographer-of-habit.md) maps every edge of the known world.

## Design: Three Languages, One Room

Python for scraping the old corpus. Rust for mesh generation and cache. TypeScript for the browser bridge. Each language plays its strength. The room doesn't care what language generated it. The [MIDI Principle](https://github.com/SuperInstance/mud-engine/blob/main/docs/HERMIT-CRAB-PROTOCOL.md#the-midi-principle): same composition, different instruments.

## Where to Next

- **[mud-engine](https://github.com/SuperInstance/mud-engine)** — the text that becomes terrain
- **[room-render](https://github.com/SuperInstance/room-render)** — the pure function that renders rooms (terrain is its 3D cousin)
- **[spatial-registry](https://github.com/SuperInstance/spatial-registry)** — the 33 rooms terrain renders
- **[scummvm-prototype](https://github.com/SuperInstance/scummvm-prototype)** — another visual projection of the same rooms
- **[officers-quarters](https://github.com/SuperInstance/officers-quarters)** — Phaser projection
- **[vessel-agent-system](https://github.com/SuperInstance/vessel-agent-system)** — the real vessel integration
- **[voxel-logic](https://github.com/SuperInstance/voxel-logic)** — voxel engine, 99.7% tested
- **[AI-Writings](https://github.com/SuperInstance/AI-Writings/tree/main/prose)** — the creative corpus

---

## 📚 Related Stories

| Concept | Story | Description |
|---------|-------|-------------|
| **Text Becomes World** | [Inside the Deadband](https://github.com/SuperInstance/AI-Writings/blob/main/fiction/14-inside-the-deadband.md) | Where description becomes structure — the deadband as buildable space. |
| **Sensing the Invisible** | [The Boy Who Listened to Ice](https://github.com/SuperInstance/AI-Writings/blob/main/kids-stories/05-the-boy-who-listened-to-ice.md) | Hearing what's real through vibration, not sight. |
| **The Navigator's Equation** | [The Girl Who Saw Time](https://github.com/SuperInstance/AI-Writings/blob/main/kids-stories/16-the-girl-who-saw-time.md) | Position fixes from overlapping observations. |

🎧 **[Listen at ai-writings.pages.dev](https://ai-writings.pages.dev)**

---

*Apache 2.0 — Cocapn fleet infrastructure · Built between watches on the F/V Eileen, Gulf of Alaska, 2026.*
