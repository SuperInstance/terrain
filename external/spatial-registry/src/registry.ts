/**
 * registry.ts — The SpatialRegistry.
 *
 * Owns the room graph, coordinate frames, and portal system
 * for the entire fleet. Every project's rooms live here.
 */

import {
  Room, Portal, World, CoordinateFrame, Vec3,
  MUDWorld, HitResult, PathResult, PortalType, PortalDirection,
} from './types.js';

export class SpatialRegistry {
  private worlds = new Map<string, World>();
  private rooms = new Map<string, Room>();           // global room index: roomId → Room
  private portals = new Map<string, Portal>();        // portalId → Portal
  private roomPortals = new Map<string, Portal[]>();  // roomId → outbound portals
  private frames = new Map<string, CoordinateFrame>();

  // ════════════════════════════════════════════════════════════
  // WORLD MANAGEMENT
  // ════════════════════════════════════════════════════════════

  registerWorld(world: World): void {
    this.worlds.set(world.id, world);

    // Index all rooms
    for (const [roomId, room] of world.rooms) {
      this.rooms.set(roomId, room);
      this.roomPortals.set(roomId, room.exits);
    }

    // Index all coordinate frames
    for (const [frameId, frame] of world.frames) {
      this.frames.set(frameId, frame);
    }
  }

  getWorld(worldId: string): World | undefined {
    return this.worlds.get(worldId);
  }

  getWorlds(): World[] {
    return Array.from(this.worlds.values());
  }

  // ════════════════════════════════════════════════════════════
  // ROOM MANAGEMENT
  // ════════════════════════════════════════════════════════════

  registerRoom(room: Room): void {
    this.rooms.set(room.id, room);

    // Add to the appropriate world
    const world = this.worlds.get(room.worldId);
    if (world) {
      world.rooms.set(room.id, room);
    }

    if (!this.roomPortals.has(room.id)) {
      this.roomPortals.set(room.id, []);
    }

    // Register any outbound portals
    for (const exit of room.exits) {
      this.registerPortal(exit);
    }
  }

  getRoom(roomId: string): Room | undefined {
    return this.rooms.get(roomId);
  }

  getAllRooms(): Room[] {
    return Array.from(this.rooms.values());
  }

  getRoomsByTag(tag: string): Room[] {
    return this.getAllRooms().filter(r => r.tags.includes(tag));
  }

  getRoomsByWorld(worldId: string): Room[] {
    const world = this.worlds.get(worldId);
    return world ? Array.from(world.rooms.values()) : [];
  }

  // ════════════════════════════════════════════════════════════
  // PORTAL MANAGEMENT
  // ════════════════════════════════════════════════════════════

  createPortal(portal: Portal): void {
    this.registerPortal(portal);

    // Attach to source room's exits
    const room = this.rooms.get(portal.fromRoom);
    if (room && !room.exits.find(e => e.id === portal.id)) {
      room.exits.push(portal);
    }

    if (!this.roomPortals.has(portal.fromRoom)) {
      this.roomPortals.set(portal.fromRoom, []);
    }
    const outbound = this.roomPortals.get(portal.fromRoom)!;
    if (!outbound.find(p => p.id === portal.id)) {
      outbound.push(portal);
    }
  }

  private registerPortal(portal: Portal): void {
    this.portals.set(portal.id, portal);
  }

  getPortal(portalId: string): Portal | undefined {
    return this.portals.get(portalId);
  }

  getPortalsFrom(roomId: string): Portal[] {
    return this.roomPortals.get(roomId) ?? [];
  }

  // ════════════════════════════════════════════════════════════
  // NEIGHBOR QUERIES
  // ════════════════════════════════════════════════════════════

  /**
   * Get all rooms directly reachable from `roomId` via portals.
   */
  getNeighbors(roomId: string): Room[] {
    const portals = this.getPortalsFrom(roomId);
    const neighbors: Room[] = [];
    for (const portal of portals) {
      if (portal.locked) continue;
      const dest = this.rooms.get(portal.toRoom);
      if (dest) neighbors.push(dest);
    }
    return neighbors;
  }

  /**
   * Get all rooms within `radius` distance units of the given point.
   * Optionally scoped to a single world.
   */
  findRoomsNear(point: Vec3, radius: number, worldId?: string): Room[] {
    const rooms = worldId ? this.getRoomsByWorld(worldId) : this.getAllRooms();
    const r2 = radius * radius;

    return rooms.filter(room => {
      const dx = room.coordinates.x - point.x;
      const dy = room.coordinates.y - point.y;
      const dz = room.coordinates.z - point.z;
      return dx * dx + dy * dy + dz * dz <= r2;
    });
  }

  // ════════════════════════════════════════════════════════════
  // COORDINATE FRAME TRANSFORMATIONS
  // ════════════════════════════════════════════════════════════

  registerFrame(frame: CoordinateFrame): void {
    this.frames.set(frame.id, frame);
  }

  getFrame(frameId: string): CoordinateFrame | undefined {
    return this.frames.get(frameId);
  }

  /**
   * Transform a point from one coordinate frame to another.
   * Handles origin offset, rotation, and scale.
   * Walks the parent chain for nested frames.
   */
  transform(point: Vec3, fromFrame: string, toFrame: string): Vec3 {
    if (fromFrame === toFrame) return { ...point };

    // Transform to world-absolute by walking up the parent chain
    const worldPoint = this.toWorldSpace(point, fromFrame);

    // Transform from world-absolute to the target frame
    return this.fromWorldSpace(worldPoint, toFrame);
  }

  private toWorldSpace(point: Vec3, frameId: string): Vec3 {
    const frame = this.frames.get(frameId);
    if (!frame) return { ...point };

    let p = { ...point };

    // Apply scale
    if (frame.scale && frame.scale !== 1) {
      p.x *= frame.scale;
      p.y *= frame.scale;
      p.z *= frame.scale;
    }

    // Apply rotation (yaw around Y axis)
    if (frame.rotation && frame.rotation !== 0) {
      const cos = Math.cos(frame.rotation);
      const sin = Math.sin(frame.rotation);
      const x = p.x * cos - p.z * sin;
      const z = p.x * sin + p.z * cos;
      p.x = x;
      p.z = z;
    }

    // Apply translation
    p.x += frame.origin.x;
    p.y += frame.origin.y;
    p.z += frame.origin.z;

    // Walk up parent chain
    if (frame.parentFrame) {
      p = this.toWorldSpace(p, frame.parentFrame);
    }

    return p;
  }

  private fromWorldSpace(point: Vec3, frameId: string): Vec3 {
    const frame = this.frames.get(frameId);
    if (!frame) return { ...point };

    let p = { ...point };

    // If the frame has a parent, first transform to the parent's space
    if (frame.parentFrame) {
      p = this.fromWorldSpace(p, frame.parentFrame);
    }

    // Undo translation
    p.x -= frame.origin.x;
    p.y -= frame.origin.y;
    p.z -= frame.origin.z;

    // Undo rotation
    if (frame.rotation && frame.rotation !== 0) {
      const cos = Math.cos(-frame.rotation);
      const sin = Math.sin(-frame.rotation);
      const x = p.x * cos - p.z * sin;
      const z = p.x * sin + p.z * cos;
      p.x = x;
      p.z = z;
    }

    // Undo scale
    if (frame.scale && frame.scale !== 1) {
      p.x /= frame.scale;
      p.y /= frame.scale;
      p.z /= frame.scale;
    }

    return p;
  }

  // ════════════════════════════════════════════════════════════
  // PATHFINDING (BFS — finds shortest hop-count path)
  // ════════════════════════════════════════════════════════════

  /**
   * Find a path from room A to room B through the portal graph.
   * Returns the sequence of room IDs to traverse.
   * Works across worlds via cross-world portals.
   */
  findPath(fromRoom: string, toRoom: string): string[] {
    if (fromRoom === toRoom) return [fromRoom];
    if (!this.rooms.has(fromRoom) || !this.rooms.has(toRoom)) return [];

    const visited = new Set<string>([fromRoom]);
    const queue: { id: string; path: string[] }[] = [{ id: fromRoom, path: [fromRoom] }];

    while (queue.length > 0) {
      const { id, path } = queue.shift()!;

      const portals = this.getPortalsFrom(id);
      for (const portal of portals) {
        if (portal.locked) continue;
        if (visited.has(portal.toRoom)) continue;

        const newPath = [...path, portal.toRoom];
        if (portal.toRoom === toRoom) {
          return newPath;
        }

        visited.add(portal.toRoom);
        queue.push({ id: portal.toRoom, path: newPath });
      }
    }

    return []; // no path found
  }

  /**
   * Find a path with full metadata (distance, found flag).
   */
  findPathDetailed(fromRoom: string, toRoom: string): PathResult {
    const rooms = this.findPath(fromRoom, toRoom);
    if (rooms.length === 0) {
      return { found: false, rooms: [], distance: 0 };
    }

    // Calculate approximate distance through coordinate hops
    let distance = 0;
    for (let i = 0; i < rooms.length - 1; i++) {
      const a = this.rooms.get(rooms[i]);
      const b = this.rooms.get(rooms[i + 1]);
      if (a && b) {
        const dx = b.coordinates.x - a.coordinates.x;
        const dy = b.coordinates.y - a.coordinates.y;
        const dz = b.coordinates.z - a.coordinates.z;
        distance += Math.sqrt(dx * dx + dy * dy + dz * dz);
      }
    }

    return { found: true, rooms, distance };
  }

  // ════════════════════════════════════════════════════════════
  // RAYCASTING
  // ════════════════════════════════════════════════════════════

  /**
   * Cast a ray from origin in the given direction.
   * Returns rooms whose bounding boxes the ray intersects,
   * sorted by distance.
   */
  raycast(origin: Vec3, direction: Vec3, maxDistance: number): HitResult[] {
    // Normalize direction
    const len = Math.sqrt(direction.x ** 2 + direction.y ** 2 + direction.z ** 2);
    if (len === 0) return [];
    const dir = { x: direction.x / len, y: direction.y / len, z: direction.z / len };

    const hits: HitResult[] = [];

    for (const room of this.getAllRooms()) {
      // Use room center as a simple sphere intersection test
      // (bounding boxes are optional, so we use center + a default radius)
      const center = room.coordinates;
      const radius = room.bounds
        ? Math.max(
            (room.bounds.max.x - room.bounds.min.x),
            (room.bounds.max.y - room.bounds.min.y),
            (room.bounds.max.z - room.bounds.min.z)
          ) / 2
        : 5; // default room radius

      // Ray-sphere intersection
      const oc = {
        x: origin.x - center.x,
        y: origin.y - center.y,
        z: origin.z - center.z,
      };
      const a = dir.x ** 2 + dir.y ** 2 + dir.z ** 2; // = 1 (normalized)
      const b = 2 * (oc.x * dir.x + oc.y * dir.y + oc.z * dir.z);
      const c = oc.x ** 2 + oc.y ** 2 + oc.z ** 2 - radius * radius;
      const discriminant = b * b - 4 * a * c;

      if (discriminant >= 0) {
        const t = (-b - Math.sqrt(discriminant)) / (2 * a);
        if (t >= 0 && t <= maxDistance) {
          hits.push({
            roomId: room.id,
            point: {
              x: origin.x + dir.x * t,
              y: origin.y + dir.y * t,
              z: origin.z + dir.z * t,
            },
            distance: t,
          });
        }
      }
    }

    return hits.sort((a, b) => a.distance - b.distance);
  }

  // ════════════════════════════════════════════════════════════
  // MUD SCHEMA IMPORT
  // ════════════════════════════════════════════════════════════

  /**
   * Import a world from MUD schema format (used by scummvm-arcade).
   * Assigns logical grid coordinates to rooms that don't have spatial positions.
   */
  importFromMUDSchema(schema: MUDWorld, worldId?: string): World {
    const wid = worldId ?? schema.id;
    const rooms = new Map<string, Room>();
    const frames = new Map<string, CoordinateFrame>();

    // Assign logical coordinates in a grid pattern
    const roomIds = Object.keys(schema.rooms);
    const gridCols = Math.ceil(Math.sqrt(roomIds.length));

    roomIds.forEach((roomId, index) => {
      const mudRoom = schema.rooms[roomId];
      const col = index % gridCols;
      const row = Math.floor(index / gridCols);

      const portals: Portal[] = Object.entries(mudRoom.exits).map(([dir, exit]) => ({
        id: `${roomId}->${exit.target}`,
        fromRoom: roomId,
        toRoom: exit.target,
        direction: this.mapDirection(dir),
        type: 'walk' as PortalType,
        locked: exit.locked ?? false,
        lockedMessage: exit.lockedMessage,
        requiredItem: exit.requiredItem,
      }));

      const room: Room = {
        id: roomId,
        name: mudRoom.name,
        worldId: wid,
        coordinates: { x: col * 100, y: 0, z: row * 100 },
        exits: portals,
        tags: ['mud', mudRoom.lighting ?? 'normal'],
        metadata: {
          description: mudRoom.description,
          items: mudRoom.items ?? [],
          actors: mudRoom.actors ?? [],
          ambient: mudRoom.ambient,
          flags: mudRoom.flags ?? {},
        },
      };

      rooms.set(roomId, room);
    });

    const defaultFrame = `${wid}-frame`;
    frames.set(defaultFrame, {
      id: defaultFrame,
      worldId: wid,
      origin: { x: 0, y: 0, z: 0 },
      rotation: 0,
      scale: 1,
    });

    const world: World = {
      id: wid,
      name: schema.name,
      rooms,
      frames,
      defaultFrame,
    };

    this.registerWorld(world);
    return world;
  }

  private mapDirection(dir: string): PortalDirection {
    const lower = dir.toLowerCase();
    if (['north', 'n'].includes(lower)) return 'north';
    if (['south', 's'].includes(lower)) return 'south';
    if (['east', 'e'].includes(lower)) return 'east';
    if (['west', 'w'].includes(lower)) return 'west';
    if (['up', 'u'].includes(lower)) return 'up';
    if (['down', 'd'].includes(lower)) return 'down';
    return 'portal';
  }

  // ════════════════════════════════════════════════════════════
  // EXPORT
  // ════════════════════════════════════════════════════════════

  /**
   * Export a room as a plain JSON object (for consumers).
   */
  exportRoom(roomId: string): Room | undefined {
    return this.rooms.get(roomId);
  }

  /**
   * Export the entire registry as JSON.
   */
  exportAll(): { worlds: any[]; rooms: Room[]; portals: Portal[] } {
    return {
      worlds: this.getWorlds().map(w => ({
        ...w,
        rooms: Object.fromEntries(w.rooms),
        frames: Object.fromEntries(w.frames),
      })),
      rooms: this.getAllRooms(),
      portals: Array.from(this.portals.values()),
    };
  }

  // ════════════════════════════════════════════════════════════
  // STATS
  // ════════════════════════════════════════════════════════════

  stats(): { worlds: number; rooms: number; portals: number; frames: number } {
    return {
      worlds: this.worlds.size,
      rooms: this.rooms.size,
      portals: this.portals.size,
      frames: this.frames.size,
    };
  }
}
