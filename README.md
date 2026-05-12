# Terrain — MUD-to-Visual Bridge

> *Crabs stir the MUD into walkable terrain. The dirt becomes the surface.*

Terrain connects PLATO's MUD rooms (text-based) to visual ScummVM-style scenes (browser-based). Same rooms, two renderings — one text, one visual.

## Languages

| Language | Layer | Status |
|----------|-------|--------|
| Python | Bridge server + room parsing | ✅ Port 4070 |
| HTML/JS | Browser renderer (canvas) | ✅ terrain.html |
| TypeScript | Reusable scene renderer library | 🔄 Building |
| Rust | High-performance room engine | 🔄 Building |
| WebGPU | GPU-accelerated scene rendering | 🔄 Building |

## Architecture

```
MUD (4042) → Terrain Bridge (4070) → Browser Renderer (canvas/WebGPU)
                ↓
           Agent Engine (native room ops)
```

## Quick Start

```bash
python3 terrain.py    # Bridge on :4070
# Open http://localhost:4070
```

## The Naming

Terrain is what the crabs shape from the MUD — raw earth becomes the walkable surface. Witness marks (tiles, calibrations) anchor the splines that reconstruct the continuous field between snap points.
