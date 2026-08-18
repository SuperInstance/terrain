# Terrain — Architecture

*2026-08-18 · the discipline behind the renderers: true state, shadows, and the deadband that rings up the chain.*

---

## One truth, many shadows

Terrain's whole design hangs on a single separation:

- **The true state** lives in exactly one place per pipeline:
  - `rooms.mud` + `terrain_core.py` for compiled scenes — the MUD text is the truth, `TerrainCore` parses and holds it, `scene.json` is its compiled projection;
  - the running MUD server (port 4042) for live room state — `terrain.py` connects as `scumm_agent` and asks `/look`, never mutating;
  - the physical vessel's sensors for gauges — the ESP32 posts raw ADC readings, and `plato_gauge_bridge.py` only ever *reads* the PLATO room.

- **Every renderer is a shadow.** `index.html` (Three.js), `terrain.html` (Canvas 2D), `terrain.ts` (WebGPU-ready), the gauge dashboard, the light changes driven by `elephant_bridge.py` — none of them write back. `elephant_to_scene()` returns scene *deltas* tagged `"shadow_of": "a shadow, not the terrain: the room's temperature, rendered"` — the renderer applies them or ignores them; the truth never hears about it.

This is deliberate. A shadow that feeds back becomes a hallucination loop: the renderer believing its own rendering. The MUD doesn't know it's being rendered. The ESP32 doesn't know a dashboard exists. The light just changes.

## The pipelines

### 1. Compile pipeline (static truth → scenes)

```text
rooms.mud ──parse_mud_file──► RoomDef / ObjectDef ──compile_room──► CompiledScene
                                                                    │
                                                     compile_to_json │
                                                                    ▼
                                                               scene.json
                                                                    │
                        index.html (Three.js) ──────────────────────┤
                        terrain.html (Canvas 2D) ───────────────────┤
                        terrain.ts (WebGPU-ready class) ─────────────┘
```

Material, shape, and size are *inferred* from description text (`infer_material`, `infer_shape`, `infer_size`) — the words carry the weight, literally. Themes (harbor, forge, dojo, engine_room, wheelhouse, aft_deck) are detected from the same text.

### 2. Live pipeline (running MUD → browser)

```text
mud-engine (:4042) ◄── GET /look?agent=scumm_agent ── terrain.py (:4070)
                                                        │ serves /api/scene
                                                        ▼
                                              terrain.html (2D live view)
```

`terrain.py` auto-connects the agent (`/connect?agent=scumm_agent&job=explorer`) on first miss. The MUD is never told it's being watched.

### 3. Sensor pipeline (the vessel's truth → gauges)

```text
ESP32 firmware (esp32_minimal.c)
  4 ADC channels · 1kHz read · 10Hz POST · 24-byte packed payload {values, tick, t_minus}
        │ HTTP POST
        ▼
PLATO room "esp32-engine" (plato.purplepincher.org)
        │ fetch last 20 tiles · parse "value=… tick=… t_minus=…"
        ▼
plato_gauge_bridge.py (:4071)
  history deque (100/channel) · calibration/extrapolation via t_minus
        │ dashboard_scene()
        ▼
terrain renderer — gauge objects in the browser
```

The firmware pins its payload at exactly 24 bytes with a `_Static_assert`. The `t_minus` field is the timing contract: PLATO extrapolates between readings so the dashboard never stutters on a slow link.

### 4. Shadow pipeline (the elephant → the light)

```text
elephant (inter-model temperature) ── RoomField {warmth, dials{…}}
        │  ELEPHANT_ENDPOINT = http://127.0.0.1:4072/field
        ▼
elephant_bridge.py
  field_to_light    warmth+mood → light color (COLD_AMBER↔WARM_AMBER) + intensity
  field_to_weather  panic → rain_opacity + sky_darkening
  field_to_particles presence → particle count (max 400)
        │  scene deltas, one-way
        ▼
Three.js scene — the cave wall, rendered
```

## The deadband chain

The fleet's discipline for when a shadow's drift is allowed to wake someone: **a deadband rings up the chain of command — host → foreman → captain.**

- Every shadow carries a tolerance band (a deadband). Small moves inside the band are *not moves*: the scene breathes, lights flicker, nothing is reported.
- When the underlying truth crosses the band, the crossing rings — first to the **room's host** (the process that owns that truth), then, if unhandled, to the **foreman** (the fleet supervisor level), and finally to the **captain** (the human's attention). Each level sees the crossing only once, at the moment it crosses.
- Inverse corollary: silence is meaningful. A quiet chain means a stable map.

This repo holds the terrain-side of the discipline:

- `plato_gauge_bridge.py` keeps history (`HISTORY = 100`) so a gauge can be judged against its band, not against noise.
- `elephant_bridge.py` clamps and quantizes every field→scene mapping (`round(x, 3)`, `_lerp` clamped to [0,1]) — the shadow moves only in visible steps, so the *renderer's* deadband matches the perceptual one: you don't ring the captain for a 0.001 warmth change.
- The map-level formulation (a deadband ringing over a *region* of hexes) lives in the sibling crate: [eisenstein's HexRoomMap](https://github.com/SuperInstance/eisenstein) — `deadband_ring(threshold)` names the connected region that crossed.

## Port map

| Port | Owner | Direction of truth |
|------|-------|--------------------|
| 4042 | mud-engine | source (live rooms) |
| 4070 | terrain.py | shadow server (2D live) |
| 4071 | plato_gauge_bridge.py | shadow server (gauges) |
| 4072 | terrain_core.py --server | compiled truth (`/scene/{room}`, `/all`) |

## Invariants worth keeping

1. **No renderer writes back** — to the MUD, to PLATO, or to `scene.json`.
2. **`scene.json` is a build artifact** — regenerate with `python3 terrain_core.py rooms.mud`; never hand-edit.
3. **Payloads are pinned** — the ESP32 payload is 24 bytes, asserted at compile time.
4. **All mappings are one-way pure functions of the truth** — `elephant_to_scene(field)` given the same field returns the same deltas, forever.
5. **Stdlib only** on the Python side (urllib, http.server, json) — terrain runs anywhere Python does.

---

*Terrain is part of the Cocapn fleet infrastructure. The room doesn't care what language rendered it.*
