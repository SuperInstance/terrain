/**
 * import-all.ts — Migration script.
 *
 * Reads room definitions from every fleet project and imports them
 * into the SpatialRegistry. Each project has its own coordinate frame.
 *
 * Run: npx tsx src/migrations/import-all.ts
 */

import { SpatialRegistry } from '../registry.js';
import type { World, Room, Portal, CoordinateFrame } from '../types.js';

// ═══════════════════════════════════════════════════════════════
// PLATO'S SHELL — 13 rooms (Phaser screen coordinates)
// ═══════════════════════════════════════════════════════════════

const PLATOS_SHELL_ROOMS = [
  { id: 'bar-rail',       name: 'The Tap — Bar Rail',  x: 0,   z: 0,  exits: { 'aft-deck': 'east', 'the-radio': 'west', 'quiet-corner': 'north', 'poker-room': 'south', 'library-nook': 'south' } },
  { id: 'the-radio',      name: 'The Radio Room',      x: -100, z: 0,  exits: { 'bar-rail': 'east' } },
  { id: 'aft-deck',       name: 'The Aft Deck',        x: 100, z: 0,  exits: { 'bar-rail': 'west', 'wheelhouse': 'north' } },
  { id: 'wheelhouse',     name: 'The Wheelhouse',      x: 100, z: -100, exits: { 'aft-deck': 'south', 'galley': 'west', 'engine-room': 'south' } },
  { id: 'galley',         name: 'The Galley',          x: 0,   z: -100, exits: { 'wheelhouse': 'east', 'aft-deck': 'south' } },
  { id: 'engine-room',    name: 'The Engine Room',     x: 200, z: -100, exits: { 'wheelhouse': 'north', 'aft-cockpit': 'north' } },
  { id: 'aft-cockpit',    name: 'The Aft Cockpit',     x: 200, z: 100,  exits: { 'engine-room': 'south', 'bar-rail': 'west' } },
  { id: 'poker-room',     name: 'The Poker Room',      x: 0,   z: 100,  exits: { 'bar-rail': 'north' } },
  { id: 'quiet-corner',   name: 'The Quiet Corner',    x: 0,   z: -200, exits: { 'bar-rail': 'south', 'listening-room': 'west' } },
  { id: 'listening-room', name: 'The Listening Room',  x: -100, z: -200, exits: { 'quiet-corner': 'east', 'the-study': 'west' } },
  { id: 'the-study',      name: 'The Study',           x: -200, z: -200, exits: { 'listening-room': 'east' } },
  { id: 'library-nook',   name: 'The Library Nook',    x: -100, z: 100,  exits: { 'bar-rail': 'north' } },
] as const;

const PLATOS_TAGS: Record<string, string[]> = {
  'bar-rail': ['bar', 'social', 'hub'],
  'the-radio': ['radio', 'comms'],
  'aft-deck': ['deck', 'outdoor'],
  'wheelhouse': ['bridge', 'command'],
  'galley': ['food', 'social'],
  'engine-room': ['engine', 'mechanical'],
  'aft-cockpit': ['deck', 'fishing'],
  'poker-room': ['poker', 'social', 'game'],
  'quiet-corner': ['quiet', 'private'],
  'listening-room': ['quiet', 'audio'],
  'the-study': ['quiet', 'writing'],
  'library-nook': ['library', 'reading'],
};

function importPlatosShell(registry: SpatialRegistry): World {
  const worldId = 'platos-shell';
  const rooms = new Map<string, Room>();
  const frames = new Map<string, CoordinateFrame>();

  const frameId = 'platos-frame';
  frames.set(frameId, {
    id: frameId,
    worldId,
    origin: { x: 0, y: 0, z: 0 },
    rotation: 0,
    scale: 1,
  });

  for (const r of PLATOS_SHELL_ROOMS) {
    const portals: Portal[] = Object.entries(r.exits).map(([target, dir]) => ({
      id: `${r.id}->${target}`,
      fromRoom: r.id,
      toRoom: target,
      direction: dir as Portal['direction'],
      type: 'walk',
    }));

    const room: Room = {
      id: r.id,
      name: r.name,
      worldId,
      coordinates: { x: r.x, y: 0, z: r.z },
      exits: portals,
      tags: PLATOS_TAGS[r.id] ?? [],
      metadata: { source: 'platos-shell', coordinateSystem: 'phaser-screen' },
    };

    rooms.set(r.id, room);
  }

  const world: World = { id: worldId, name: "Plato's Shell", rooms, frames, defaultFrame: frameId };
  registry.registerWorld(world);
  return world;
}

// ═══════════════════════════════════════════════════════════════
// OFFICERS' QUARTERS — 12 rooms (Phaser world coordinates)
// ═══════════════════════════════════════════════════════════════

const OFFICERS_ROOMS = [
  { id: 'bridge',          name: 'The Bridge',        x: 0,    z: 0,    category: 'command', exits: ['flash-station','pro-station','wesley-station','scribe-station','hermes-station','poker-room','library','workshop','galley','engine-room','chart-house'] },
  { id: 'flash-station',   name: 'Flash Station',     x: -200, z: 0,    category: 'station', exits: ['bridge'] },
  { id: 'pro-station',     name: 'Pro Station',       x: 200,  z: 0,    category: 'station', exits: ['bridge'] },
  { id: 'wesley-station',  name: 'Wesley Station',    x: 0,    z: -200, category: 'station', exits: ['bridge'] },
  { id: 'scribe-station',  name: 'Scribe Station',    x: 0,    z: 200,  category: 'station', exits: ['bridge'] },
  { id: 'hermes-station',  name: 'Hermes Station',    x: -200, z: -200, category: 'station', exits: ['bridge'] },
  { id: 'poker-room',      name: 'The Poker Room',    x: 200,  z: -200, category: 'social',  exits: ['bridge'] },
  { id: 'library',         name: 'The Library',       x: -200, z: 200,  category: 'utility', exits: ['bridge'] },
  { id: 'workshop',        name: 'The Workshop',      x: 200,  z: 200,  category: 'utility', exits: ['bridge'] },
  { id: 'galley',          name: 'The Galley',        x: -400, z: 0,    category: 'utility', exits: ['bridge'] },
  { id: 'engine-room',     name: 'The Engine Room',   x: 400,  z: 0,    category: 'utility', exits: ['bridge'] },
  { id: 'chart-house',     name: 'The Chart House',   x: 0,    z: 400,  category: 'utility', exits: ['bridge'] },
] as const;

function importOfficersQuarters(registry: SpatialRegistry): World {
  const worldId = 'officers-quarters';
  const rooms = new Map<string, Room>();
  const frames = new Map<string, CoordinateFrame>();

  const frameId = 'officers-frame';
  // Officers' Quarters is offset from Plato's Shell by a large distance
  frames.set(frameId, {
    id: frameId,
    worldId,
    origin: { x: 10000, y: 0, z: 0 }, // offset so rooms don't overlap
    rotation: 0,
    scale: 1,
  });

  for (const r of OFFICERS_ROOMS) {
    const portals: Portal[] = r.exits.map(target => ({
      id: `${r.id}->${target}`,
      fromRoom: r.id,
      toRoom: target,
      direction: 'portal',
      type: 'walk',
    }));

    const room: Room = {
      id: `oq-${r.id}`,  // prefix to avoid collision with platos-shell room IDs
      name: r.name,
      worldId,
      coordinates: { x: r.x, y: 0, z: r.z },
      exits: portals.map(p => ({ ...p, fromRoom: `oq-${p.fromRoom}`, toRoom: `oq-${p.toRoom}` })),
      tags: [r.category, 'officers-quarters'],
      metadata: { source: 'officers-quarters', category: r.category, coordinateSystem: 'phaser-world', originalId: r.id },
    };

    rooms.set(room.id, room);
  }

  const world: World = { id: worldId, name: "Officers' Quarters", rooms, frames, defaultFrame: frameId };
  registry.registerWorld(world);
  return world;
}

// ═══════════════════════════════════════════════════════════════
// THE TAP — D1 room IDs (Rust-based, no spatial coordinates)
// We assign logical positions based on the room graph from tap-room.
// ═══════════════════════════════════════════════════════════════

const TAP_ROOMS = [
  // Using numeric IDs from the tap-room lib. We map them to named rooms.
  { id: 'tap-bar',     name: 'The Tap — Bar',     x: 0,    z: 0,   exits: ['tap-hallway'] },
  { id: 'tap-hallway', name: 'The Tap — Hallway', x: 100,  z: 0,   exits: ['tap-bar', 'tap-kitchen'] },
  { id: 'tap-kitchen', name: 'The Tap — Kitchen', x: 200,  z: 0,   exits: ['tap-hallway'] },
] as const;

function importTheTap(registry: SpatialRegistry): World {
  const worldId = 'the-tap';
  const rooms = new Map<string, Room>();
  const frames = new Map<string, CoordinateFrame>();

  const frameId = 'tap-frame';
  frames.set(frameId, {
    id: frameId,
    worldId,
    origin: { x: 5000, y: 0, z: 5000 }, // separate region
    rotation: 0,
    scale: 1,
  });

  for (const r of TAP_ROOMS) {
    const portals: Portal[] = r.exits.map(target => ({
      id: `${r.id}->${target}`,
      fromRoom: r.id,
      toRoom: target,
      direction: 'portal',
      type: 'walk',
    }));

    const room: Room = {
      id: r.id,
      name: r.name,
      worldId,
      coordinates: { x: r.x, y: 0, z: r.z },
      exits: portals,
      tags: ['tap', 'rust'],
      metadata: { source: 'the-tap', coordinateSystem: 'logical', originalSystem: 'tap-room (Rust)' },
    };

    rooms.set(r.id, room);
  }

  const world: World = { id: worldId, name: 'The Tap (Rust)', rooms, frames, defaultFrame: frameId };
  registry.registerWorld(world);
  return world;
}

// ═══════════════════════════════════════════════════════════════
// SCUMMVM ARCADE — BSS (MUD schema, 6 rooms)
// ═══════════════════════════════════════════════════════════════

const BSS_MUD_WORLD = {
  id: 'bss-mud-twin',
  name: 'Beneath a Steel Sky — MUD Twin',
  version: '1.0.0',
  rooms: {
    plaza: {
      id: 'plaza',
      name: 'Union City Plaza',
      description: 'The plaza stretches before you, a vast expanse of cracked concrete...',
      exits: {
        north: { target: 'factory', label: 'factory' },
        south: { target: 'apartment', label: 'apartments' },
        east: { target: 'checkpoint', label: 'checkpoint', locked: true, lockedMessage: 'ACCESS DENIED.', requiredItem: 'key_card' },
      },
      items: ['wrench'],
      actors: ['joey'],
      ambient: 'industrial_hum',
      lighting: 'dim',
    },
    factory: {
      id: 'factory',
      name: 'Underground Factory',
      description: 'The factory is a cavern of metal and steam.',
      exits: {
        south: { target: 'plaza', label: 'plaza' },
        down: { target: 'factory_maintenance', label: 'maintenance shaft', locked: true, lockedMessage: 'Sealed with a heavy lock.', requiredItem: 'wrench' },
      },
      items: [],
      actors: [],
      ambient: 'machinery_clatter',
      lighting: 'normal',
    },
    factory_maintenance: {
      id: 'factory_maintenance',
      name: 'Factory Maintenance Shaft',
      description: 'Tight metal walls close in around you.',
      exits: {
        up: { target: 'factory', label: 'factory' },
      },
      items: ['security_pass'],
      actors: [],
      ambient: 'steam_hiss',
      lighting: 'dim',
    },
    checkpoint: {
      id: 'checkpoint',
      name: 'Security Checkpoint',
      description: 'The checkpoint is a chokepoint of turnstiles and scanners.',
      exits: {
        west: { target: 'plaza', label: 'plaza' },
        east: { target: 'cathedral', label: 'cathedral', locked: true, lockedMessage: 'Requires a security pass.', requiredItem: 'security_pass' },
      },
      items: ['key_card'],
      actors: ['guard'],
      ambient: 'scanner_beep',
      lighting: 'bright',
    },
    apartment: {
      id: 'apartment',
      name: 'Apartment Block',
      description: 'The apartment block is a warren of tiny living units.',
      exits: {
        north: { target: 'plaza', label: 'plaza' },
      },
      items: [],
      actors: [],
      ambient: 'dripping_water',
      lighting: 'dim',
    },
    cathedral: {
      id: 'cathedral',
      name: 'The Cathedral',
      description: 'The Cathedral rises like a monument to forgotten gods.',
      exits: {
        west: { target: 'checkpoint', label: 'checkpoint' },
      },
      items: [],
      actors: ['overseer'],
      ambient: 'cathedral_organ_electronic',
      lighting: 'bright',
    },
  },
};

function importScummVMArcade(registry: SpatialRegistry): World {
  return registry.importFromMUDSchema(BSS_MUD_WORLD, 'scummvm-bss');
}

// ═══════════════════════════════════════════════════════════════
// CROSS-WORLD PORTALS — Connect the worlds
// ═══════════════════════════════════════════════════════════════

function createCrossWorldPortals(registry: SpatialRegistry): void {
  // Plato's Shell bar-rail ↔ The Tap bar
  registry.createPortal({
    id: 'xworld:platos-bar->tap-bar',
    fromRoom: 'bar-rail',
    toRoom: 'tap-bar',
    direction: 'warp',
    type: 'warp',
  });

  registry.createPortal({
    id: 'xworld:tap-bar->platos-bar',
    fromRoom: 'tap-bar',
    toRoom: 'bar-rail',
    direction: 'warp',
    type: 'warp',
  });

  // Plato's Shell poker-room ↔ Officers' Quarters poker-room
  registry.createPortal({
    id: 'xworld:platos-poker->oq-poker',
    fromRoom: 'poker-room',
    toRoom: 'oq-poker-room',
    direction: 'warp',
    type: 'warp',
  });

  registry.createPortal({
    id: 'xworld:oq-poker->platos-poker',
    fromRoom: 'oq-poker-room',
    toRoom: 'poker-room',
    direction: 'warp',
    type: 'warp',
  });

  // Officers' Quarters bridge ↔ Plato's Shell wheelhouse
  registry.createPortal({
    id: 'xworld:oq-bridge->platos-wheelhouse',
    fromRoom: 'oq-bridge',
    toRoom: 'wheelhouse',
    direction: 'warp',
    type: 'warp',
  });

  registry.createPortal({
    id: 'xworld:platos-wheelhouse->oq-bridge',
    fromRoom: 'wheelhouse',
    toRoom: 'oq-bridge',
    direction: 'warp',
    type: 'warp',
  });
}

// ═══════════════════════════════════════════════════════════════
// MAIN — Import everything
// ═══════════════════════════════════════════════════════════════

export function importAll(registry: SpatialRegistry): {
  platosShell: World;
  officersQuarters: World;
  theTap: World;
  scummvmArcade: World;
} {
  const platosShell = importPlatosShell(registry);
  const officersQuarters = importOfficersQuarters(registry);
  const theTap = importTheTap(registry);
  const scummvmArcade = importScummVMArcade(registry);

  // Connect the worlds
  createCrossWorldPortals(registry);

  return { platosShell, officersQuarters, theTap, scummvmArcade };
}

// CLI entry point
if (process.argv[1]?.endsWith('import-all.ts')) {
  const registry = new SpatialRegistry();
  const result = importAll(registry);
  const stats = registry.stats();

  console.log('\n╔══════════════════════════════════════════════════════╗');
  console.log('║     SPATIAL REGISTRY — Import Complete               ║');
  console.log('╚══════════════════════════════════════════════════════╝');
  console.log(`  Worlds:   ${stats.worlds}`);
  console.log(`  Rooms:    ${stats.rooms}`);
  console.log(`  Portals:  ${stats.portals}`);
  console.log(`  Frames:   ${stats.frames}`);
  console.log('');

  for (const [name, world] of Object.entries(result)) {
    console.log(`  ${name}: ${world.name} (${world.rooms.size} rooms)`);
  }

  console.log('\n  Cross-world portals: 3 bidirectional warp links');
  console.log('  • Plato\'s Shell bar-rail ↔ The Tap bar');
  console.log('  • Plato\'s Shell poker-room ↔ Officers\' Quarters poker-room');
  console.log('  • Plato\'s Shell wheelhouse ↔ Officers\' Quarters bridge');

  // Verify cross-world pathfinding
  const path = registry.findPath('bar-rail', 'wheelhouse');
  console.log(`\n  Path test (bar-rail → wheelhouse): ${path.join(' → ')}`);

  const crossPath = registry.findPath('bar-rail', 'tap-bar');
  console.log(`  Cross-world path (bar-rail → tap-bar): ${crossPath.join(' → ')}`);

  const fullCross = registry.findPath('tap-bar', 'wheelhouse');
  console.log(`  Full cross (tap-bar → wheelhouse): ${fullCross.join(' → ')}`);

  const poker = registry.findPath('tap-bar', 'oq-poker-room');
  console.log(`  Full cross (tap-bar → OQ poker-room): ${poker.join(' → ')}`);

  console.log('');
}
