# Spatial Registry

![4-World Topology](docs/world-topology.svg)

**The unified spatial registry for the entire fleet. Every room from every project lives here.**

> *When everyone in the room agrees on the fiction, the room becomes the fiction — [the orchestra that was a room](https://github.com/SuperInstance/AI-Writings/blob/main/metaphor-mapping/18-the-orchestra-that-was-a-room.md). The Spatial Registry is that agreement made structural: four worlds, 33 rooms, one shared coordinate space where every door connects and every path resolves.*

🎧 **[Listen to related stories](https://ai-writings.pages.dev)**

---

## What This Is

The [map that knows it is not the territory](https://github.com/SuperInstance/AI-Writings/blob/main/kids-stories/16-the-girl-who-saw-time.md). A single source of truth for:

- **Room graphs** — all rooms from [Plato's Shell](https://github.com/SuperInstance/platos-shell), [Officers' Quarters](https://github.com/SuperInstance/elephant), [The Tap](https://github.com/SuperInstance/the-tap), and [ScummVM Arcade](https://github.com/SuperInstance/scummvm-arcade)
- **Coordinate frames** — each project's coordinate system mapped to a shared space
- **Portal system** — intra-world exits AND cross-world warp links
- **Pathfinding** — BFS routes that span worlds
- **Raycasting** — spatial queries in any direction

It answers only three questions, ever:
1. What is adjacent?
2. How do I get there?
3. Where am I, really?

It does not care what the rooms look like. It does not care if they are rendered at all. It will run pathfinding for a blind maintenance drone. It will transform coordinates for a log entry no human will ever read. This is the most trusted repository in the fleet. It has never once lied about position.

## Worlds

| World | Source Project | Rooms | Coordinate System |
|-------|---------------|-------|-------------------|
| Plato's Shell | [platos-shell](https://github.com/SuperInstance/platos-shell) | 12 | Phaser screen → logical grid |
| Officers' Quarters | [elephant](https://github.com/SuperInstance/elephant) | 12 | Phaser world → logical grid (offset) |
| The Tap (Rust) | [the-tap](https://github.com/SuperInstance/the-tap) | 3 | D1 room IDs → logical positions |
| ScummVM BSS | [scummvm-arcade](https://github.com/SuperInstance/scummvm-arcade) | 6 | MUD schema → grid layout |

**Total: 33 rooms across 4 worlds, connected by 6 cross-world portals.** Each world contributes its rooms like instruments in [an orchestra that was also a room](https://github.com/SuperInstance/AI-Writings/blob/main/metaphor-mapping/18-the-orchestra-that-was-a-room.md) — distinct voices, shared score.

## Cross-World Connections

Three bidirectional warp links connect the worlds:

1. **Plato's bar-rail ↔ The Tap bar** — the social hub link
2. **Plato's poker-room ↔ OQ poker-room** — [shared social space](https://github.com/SuperInstance/AI-Writings/blob/main/fiction/15-the-bluff-that-was-true.md)
3. **Plato's wheelhouse ↔ OQ bridge** — command center link

Example path: `tap-bar → bar-rail → aft-deck → wheelhouse` (crosses 2 worlds)

## Quick Start

```typescript
import { SpatialRegistry } from 'spatial-registry';
import { importAll } from 'spatial-registry/migrations/import-all';

const registry = new SpatialRegistry();
importAll(registry);

// Query neighbors
const neighbors = registry.getNeighbors('bar-rail');

// Find a path (works across worlds)
const path = registry.findPath('tap-bar', 'wheelhouse');
// → ['tap-bar', 'bar-rail', 'aft-deck', 'wheelhouse']
```

## API

| Method | Description |
|--------|-------------|
| `registerWorld(world)` | Register a world with rooms and frames |
| `getRoom(id)` | Get a room by ID |
| `getNeighbors(roomId)` | Get directly reachable rooms |
| `findPath(from, to)` | BFS pathfinding (cross-world) |
| `findRoomsNear(point, radius, worldId?)` | Radius query |
| `transform(point, fromFrame, toFrame)` | Coordinate transformation |
| `createPortal(portal)` | Create a portal (even cross-world) |
| `importFromMUDSchema(schema)` | Import [MUD-format](https://github.com/SuperInstance/mud-engine) world |

41 tests covering all functionality. Lua bindings in [`lua/`](./lua/spatial-registry.lua) for [Roblox](https://github.com/SuperInstance/roblox-beatclock) integration.

---

## Where to Next

- **[mud-engine](https://github.com/SuperInstance/mud-engine)** — defines what a room IS; registry persists them
- **[room-render](https://github.com/SuperInstance/room-render)** — renders the rooms this registry tracks
- **[terrain](https://github.com/SuperInstance/terrain)** — 3D bridge for the same rooms
- **[scummvm-prototype](https://github.com/SuperInstance/scummvm-prototype)** — first playable, rooms overlap
- **[the-tap](https://github.com/SuperInstance/the-tap)** — bar rooms connected via cross-world portal
- **[elephant](https://github.com/SuperInstance/elephant)** — 12 rooms registered here
- **[platos-shell](https://github.com/SuperInstance/platos-shell)** — 12 rooms + cross-world portals
- **[AI-Writings](https://github.com/SuperInstance/AI-Writings/tree/main/prose)** — the creative corpus

---

## 📚 Related Stories

| Concept | Story | Description |
|---------|-------|-------------|
| **Rooms as Compositions** | [The Orchestra That Was a Room](https://github.com/SuperInstance/AI-Writings/blob/main/metaphor-mapping/18-the-orchestra-that-was-a-room.md) | A room becomes a symphony when everyone agrees. |
| **Navigation** | [The Girl Who Saw Time](https://github.com/SuperInstance/AI-Writings/blob/main/kids-stories/16-the-girl-who-saw-time.md) | Finding paths by observing patterns in the bow wave. |
| **Spatial Philosophy** | [The Cartographer of Habit](https://github.com/SuperInstance/AI-Writings/blob/main/fiction/13-the-cartographer-of-habit.md) | Mapping habits as visible tiles in space. |

🎧 **[Listen at ai-writings.pages.dev](https://ai-writings.pages.dev)**

---

*MIT © SuperInstance · Built between watches on the F/V Eileen, Gulf of Alaska, 2026.*
