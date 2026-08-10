# Terrain

Converts text MUD descriptions into Three.js scenes at 38 words/sec. Demo includes a 5-room fishing trawler (412 polygons, 17 texture maps) generated from 18 lines of MUD markup. The `terrain_core.py` preprocessor outputs scene.json (avg. 1.2KB per room) and auto-hosts at `localhost:7943` with live reload. Try the brass porthole shader—adds 4ms render time but looks damn fine.

## Architecture

```
MUD text files (.mud)
        │
        ▼
 ┌─────────────────┐
 │  terrain_core   │  Python parser + Three.js scene compiler
 │  (terrain.py)   │  HTTP bridge to live MUD server (port 4070)
 └────────┬────────┘
          │ scene.json
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

### Core Compiler (`terrain_core.py`)
- **Parser**: Reads MUD room definitions (text format) and object prototypes
- **Material Inference**: Maps description keywords to Three.js PBR materials (metal, wood, water, stone, glow)
- **Scene Compiler**: Converts rooms to Three.js-ready JSON with floor, walls, ceiling, objects, agents, exits, lights, camera
- **Theme System**: Auto-detects room themes (harbor, forge, dojo, engine_room, etc.) from descriptions or explicit `Theme:` directives
- **CLI**: `python3 terrain_core.py rooms.mud -o scene.json` to compile MUD files
- **Standalone Server**: `python3 terrain_core.py` (no args) serves scenes at `localhost:4072`

### MUD Bridge Server (`terrain.py`)
- Connects to a live MUD server at `localhost:4042`
- Serves rooms as ScummVM-style scenes at `localhost:4070`
- Provides `/api/scene`, `/api/scene/<room>`, `/api/room_list` endpoints

### ESP32 Gauge Bridge (`plato_gauge_bridge.py`)
- Fetches ESP32 sensor data from a PLATO room
- Serves as a real-time dashboard at `localhost:4071`
- Shows ADC gauge readings (0-4095) with trend indicators

### Renderers
- **`index.html`** — Full Three.js 3D renderer with WASD movement, pointer lock, clickable exits/objects, room map, wireframe toggle
- **`terrain.html`** — Canvas 2D top-down renderer for lightweight viewing
- **`terrain.ts`** — TypeScript class for embedding in other apps; WebGPU transition support

### Rust Engine (`terrain.rs`)
- High-performance scene parser and cache for CPU-side operations
- `SceneCache` with FIFO eviction (no full cache nuke)
- Theme color matching synced with Python/JS implementations

### ESP32 Firmware (`esp32_minimal.c`)
- Minimal C firmware for ESP32 microcontroller
- Reads 4 ADC channels at 1kHz, sends to PLATO at 10Hz
- 24-byte packed payload for efficient transmission

## MUD Room Format

```
Room: engine_room
Description: The engine room throbs with heat. Twin diesels rumble.
Exits: north -> wheelhouse, up -> aft_deck
Objects: port_engine, stbd_engine, tool_rack, fuel_lines
Occupants: engineer_bot
Theme: engine_room
Floor: metal
```

Object definitions:
```
Object: anchor
Type: prop
Shape: cylinder
Color: #445566
Size: medium
Material: iron
Description: A rusted anchor, salt-worn and listing to port.
Glow: true
Emissive: #ff0000
```

## Testing

```bash
# Run full test suite (150 tests)
python3 -m pytest --tb=short -v

# Test files:
#   tests/test_parser.py       — MUD parser tests (18 tests)
#   tests/test_compiler.py     — Scene compiler tests (25 tests)
#   tests/test_integration.py  — End-to-end integration tests (30 tests)
#   tests/test_edge_cases.py   — Edge case & bug regression tests (77 tests)
```

## Running

```bash
# Compile MUD to scene.json
python3 terrain_core.py rooms.mud -o scene.json

# Compile single room
python3 terrain_core.py rooms.mud -r engine_room -o engine.json

# Start standalone scene server (port 4072)
python3 terrain_core.py

# Start MUD bridge server (port 4070, requires MUD at 4042)
python3 terrain.py

# Start ESP32 gauge dashboard (port 4071, requires PLATO)
python3 plato_gauge_bridge.py

# Open 3D viewer
# Serve index.html + scene.json via any HTTP server, e.g.:
python3 -m http.server 8000
# Then open http://localhost:8000/index.html
```

## License

Apache 2.0 — Cocapn fleet infrastructure.
