/**
 * types.ts — Core spatial types for the unified registry.
 *
 * Every room from every project lives in this type system.
 * A Room is the atomic unit of space. A Portal connects rooms.
 * A CoordinateFrame maps between different coordinate systems.
 * A World is a collection of rooms + frames.
 */

// ── Primitives ────────────────────────────────────────────────

export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

export interface BoundingBox {
  min: Vec3;
  max: Vec3;
}

// ── Room ──────────────────────────────────────────────────────

export interface Room {
  id: string;
  name: string;
  worldId: string;
  coordinates: Vec3;
  bounds?: BoundingBox;
  exits: Portal[];
  tags: string[];
  metadata: Record<string, any>;
}

// ── Portal ────────────────────────────────────────────────────

export type PortalType = 'walk' | 'warp' | 'transition' | 'teleport';
export type PortalDirection = 'north' | 'south' | 'east' | 'west' | 'up' | 'down' | 'portal' | 'warp';

export interface Portal {
  id: string;
  fromRoom: string;
  toRoom: string;
  direction?: PortalDirection;
  type: PortalType;
  locked?: boolean;
  lockedMessage?: string;
  requiredItem?: string;
  coordinateOffset?: { dx: number; dy: number; dz: number };
}

// ── Coordinate Frame ──────────────────────────────────────────

export interface CoordinateFrame {
  id: string;
  worldId: string;
  origin: Vec3;
  rotation?: number;   // yaw in radians
  scale?: number;      // uniform scale, default 1
  parentFrame?: string;
}

// ── World ─────────────────────────────────────────────────────

export interface World {
  id: string;
  name: string;
  rooms: Map<string, Room>;
  frames: Map<string, CoordinateFrame>;
  defaultFrame: string;
}

// ── MUD Schema (for import compatibility) ─────────────────────

export interface MUDExit {
  target: string;
  label: string;
  locked?: boolean;
  lockedMessage?: string;
  requiredItem?: string;
}

export interface MUDRoom {
  id: string;
  name: string;
  description: string;
  exits: Record<string, MUDExit>;
  items?: string[];
  actors?: string[];
  ambient?: string;
  lighting?: string;
  flags?: Record<string, any>;
}

export interface MUDWorld {
  id: string;
  name: string;
  version?: string;
  rooms: Record<string, MUDRoom>;
  items?: Record<string, any>;
  actors?: Record<string, any>;
  verbs?: any[];
  initialState?: Record<string, any>;
}

// ── Query Results ─────────────────────────────────────────────

export interface HitResult {
  roomId: string;
  point: Vec3;
  distance: number;
}

export interface PathResult {
  found: boolean;
  rooms: string[];
  distance: number;
}
