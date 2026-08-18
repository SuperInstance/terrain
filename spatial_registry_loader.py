#!/usr/bin/env python3
"""
spatial_registry_loader.py — the whole chart, live.

Loads the fleet's room graph from the vendored spatial-registry
(external/spatial-registry/, read-only) and compiles it with terrain_core:
33 rooms across 4 worlds (Plato's Shell 12, Officers' Quarters 12, The Tap 3,
ScummVM Arcade / BSS 6) plus 6 cross-world portals. Portals become exits.

PARSING STRATEGY (deliberate, documented):
    external/spatial-registry/src/migrations/import-all.ts holds the room
    graph as plain TS const array/object literals — PLATOS_SHELL_ROOMS,
    OFFICERS_ROOMS, TAP_ROOMS, BSS_MUD_WORLD — plus registry.createPortal(
    {...}) calls for the cross-world warps. We parse those literals with
    regexes: no TS runtime, no node, no sibling-repo dependency. The shapes
    are fixed and single-file; if upstream drifts, load_registry() raises
    ValueError loudly instead of silently dropping rooms.

    Counting note: the migration's header comment claims Plato's Shell has
    13 rooms, but the array holds 12 entries. 12 + 12 + 3 + 6 = 33 — the
    fleet-total is correct, the comment is off by one. The parser counts
    what is actually there; the tests pin 33.

DIRECTION KEYS (render hints only):
    terrain RoomDef.exits is a Dict[direction, target], so every exit needs
    a direction key unique within its room. The registry's directions can
    collide ('south' twice out of bar-rail) or be non-positional ('portal'
    for every Officers'/Tap exit, 'warp' for cross-world links). Rule:
    keep the registry direction when it is a positional direction terrain
    renders and not yet used in that room; otherwise take the next free
    slot from a fixed carousel; overflow becomes portal_N. Adjacency — the
    oracle contract — is the exit TARGETS, which are preserved exactly and
    in portal insertion order.

LOCKED PORTALS:
    registry.getNeighbors()/findPath() skip locked portals (three in BSS:
    the key_card, wrench, and security_pass doors). The corpus does the
    same: locked portals are recorded in RegistryCorpus.locked_portals and
    do NOT become exits, so the terrain exit graph and the registry's
    adjacency can never disagree.

ORACLE:
    registry_adjacency() + find_path() mirror external/spatial-registry/
    src/registry.ts findPath() exactly — locked portals skipped, FIFO
    queue, portals in insertion order (a room's own exits first, the
    cross-world warps appended last, as createPortal() does). The tests
    assert edge-set and all-pairs shortest-path parity between that oracle
    and the compiled terrain exits: they must never disagree.
"""

import json
import os
import re
from collections import deque
from dataclasses import dataclass, field
from http.server import HTTPServer
from typing import Dict, List, Optional

from terrain_core import RoomDef, TerrainCore, TerrainCoreHandler

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_IMPORT_ALL = os.path.join(
    REPO_ROOT, "external", "spatial-registry", "src", "migrations", "import-all.ts"
)

# The worlds the migration registers, in registration order.
WORLDS = [
    ("platos-shell", "Plato's Shell"),
    ("officers-quarters", "Officers' Quarters"),
    ("the-tap", "The Tap (Rust)"),
    ("scummvm-bss", "Beneath a Steel Sky — MUD Twin"),
]

# Positional directions terrain_core.compile_room() renders (exit_positions).
POSITION_DIRECTIONS = frozenset({
    "north", "south", "east", "west",
    "forward", "fore", "ahead", "aft", "aftward", "astern", "backward", "back",
    "port", "portward", "starboard", "stbd",
    "forward_up", "fore_up", "forward_down", "fore_down",
    "aft_up", "aftward_up", "aft_down", "aftward_down",
    "up", "down", "in", "out", "below", "upward",
})

# Round-robin slots for portals whose registry direction is missing,
# non-positional ('portal'/'warp'), or already taken in that room.
CAROUSEL = [
    "north", "south", "east", "west", "up", "down", "in", "out",
    "northeast", "northwest", "southeast", "southwest",
]

# registry.ts mapDirection(): known compass words pass through, else 'portal'.
_MUD_DIRECTIONS = {
    "north": "north", "n": "north",
    "south": "south", "s": "south",
    "east": "east", "e": "east",
    "west": "west", "w": "west",
    "up": "up", "u": "up",
    "down": "down", "d": "down",
}


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Portal:
    id: str
    from_room: str
    to_room: str
    direction: str = "portal"
    type: str = "walk"
    locked: bool = False
    locked_message: str = ""
    required_item: str = ""


@dataclass
class WorldInfo:
    id: str
    name: str
    room_count: int


@dataclass
class RegistryCorpus:
    worlds: List[WorldInfo] = field(default_factory=list)
    rooms: List[RoomDef] = field(default_factory=list)
    portals: List[Portal] = field(default_factory=list)

    @property
    def locked_portals(self) -> List[Portal]:
        return [p for p in self.portals if p.locked]

    def stats(self) -> Dict[str, int]:
        return {
            "worlds": len(self.worlds),
            "rooms": len(self.rooms),
            "portals": len(self.portals),
            "locked": len(self.locked_portals),
            "open": len(self.portals) - len(self.locked_portals),
        }


# ============================================================================
# PARSERS — regex/literal parse of import-all.ts (see module docstring)
# ============================================================================

def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _const_array(text: str, name: str) -> List[dict]:
    """Extract one `const NAME = [ ... ] as const;` array of one-line room
    entries. Each entry line carries id/name (required), x/z, optional
    category, and an exits literal (object target->direction, or list of
    targets)."""
    m = re.search(rf"const {name} = \[(.*?)\] as const;", text, re.S)
    if not m:
        raise ValueError(f"array {name} not found in import-all.ts")
    entries = []
    for line in m.group(1).splitlines():
        line = line.strip().rstrip(",").strip()
        if not line.startswith("{"):
            continue
        m_id = re.search(r"\bid:\s*'([^']+)'", line)
        m_name = re.search(r"\bname:\s*'([^']+)'", line)
        if not m_id or not m_name:
            raise ValueError(f"unparseable room entry in {name}: {line!r}")
        entry = {"id": m_id.group(1), "name": m_name.group(1)}
        for key in ("x", "z"):
            m_num = re.search(rf"\b{key}:\s*(-?\d+)", line)
            if m_num:
                entry[key] = int(m_num.group(1))
        m_cat = re.search(r"\bcategory:\s*'([^']+)'", line)
        if m_cat:
            entry["category"] = m_cat.group(1)
        m_dict = re.search(r"\bexits:\s*\{(.*?)\}", line)
        m_list = re.search(r"\bexits:\s*\[(.*?)\]", line)
        if m_dict:
            entry["exits"] = re.findall(r"'([^']+)':\s*'([^']+)'", m_dict.group(1))
        elif m_list:
            entry["exits"] = re.findall(r"'([^']+)'", m_list.group(1))
        else:
            raise ValueError(f"no exits literal in {name} entry {entry['id']!r}")
        entries.append(entry)
    if not entries:
        raise ValueError(f"array {name} in import-all.ts is empty")
    return entries


def _parse_platos_tags(text: str) -> Dict[str, List[str]]:
    m = re.search(r"const PLATOS_TAGS[^=]*=\s*\{(.*?)\n\};", text, re.S)
    if not m:
        raise ValueError("PLATOS_TAGS not found in import-all.ts")
    tags: Dict[str, List[str]] = {}
    for rid, lst in re.findall(r"'([^']+)':\s*\[([^\]]*)\]", m.group(1)):
        tags[rid] = re.findall(r"'([^']+)'", lst)
    return tags


def _parse_bss(text: str) -> dict:
    """Extract the BSS_MUD_WORLD object literal and JSON-ify it:
    quote bare keys, single->double quotes, json.loads. (The literal's
    strings contain no apostrophes, so the quote swap is safe.)"""
    m = re.search(r"const BSS_MUD_WORLD = \{(.*?)\n\};", text, re.S)
    if not m:
        raise ValueError("BSS_MUD_WORLD not found in import-all.ts")
    body = m.group(1)
    body = re.sub(r"(?<![\"'\w])([A-Za-z_][A-Za-z0-9_]*)\s*:", r'"\1":', body)
    body = re.sub(r",\s*([}\]])", r"\1", body)  # TS trailing commas
    body = body.rstrip().rstrip(",")  # ...including the one before our closing brace
    body = body.replace("'", '"')
    try:
        return json.loads("{" + body + "}")
    except json.JSONDecodeError as e:
        raise ValueError(f"BSS_MUD_WORLD literal no longer JSON-ifiable: {e}") from e


def _parse_xworld_portals(text: str) -> List[Portal]:
    portals = []
    for block in re.findall(r"registry\.createPortal\(\s*\{(.*?)\}\s*\);", text, re.S):
        def q(key: str, default: str = "") -> str:
            m = re.search(rf"\b{key}:\s*'([^']*)'", block)
            return m.group(1) if m else default
        portals.append(Portal(
            id=q("id"),
            from_room=q("fromRoom"),
            to_room=q("toRoom"),
            direction=q("direction", "portal"),
            type=q("type", "walk"),
        ))
    return portals


def parse_import_all(text: str) -> RegistryCorpus:
    """Parse import-all.ts source into a RegistryCorpus (rooms as RoomDefs,
    portals with registry semantics). Raises ValueError on format drift."""
    platos = _const_array(text, "PLATOS_SHELL_ROOMS")
    officers = _const_array(text, "OFFICERS_ROOMS")
    tap = _const_array(text, "TAP_ROOMS")
    platos_tags = _parse_platos_tags(text)
    bss = _parse_bss(text)
    xworld = _parse_xworld_portals(text)

    rooms: List[RoomDef] = []
    portals: List[Portal] = []

    # -- Plato's Shell: exits are { target: direction } pairs, ids as-is.
    for entry in platos:
        rid = entry["id"]
        for target, direction in entry["exits"]:
            portals.append(Portal(
                id=f"{rid}->{target}", from_room=rid, to_room=target,
                direction=direction, type="walk",
            ))
        tags = platos_tags.get(rid, [])
        desc = f"{entry['name']} — a room in Plato's Shell."
        if tags:
            desc += f" Tags: {', '.join(tags)}."
        rooms.append(RoomDef(
            name=rid, description=desc,
            exits=_assign_exit_keys([p for p in portals if p.from_room == rid]),
        ))

    # -- Officers' Quarters: exits are target lists, ids prefixed oq-.
    for entry in officers:
        rid = f"oq-{entry['id']}"
        for target in entry["exits"]:
            portals.append(Portal(
                id=f"{rid}->oq-{target}", from_room=rid, to_room=f"oq-{target}",
                direction="portal", type="walk",
            ))
        rooms.append(RoomDef(
            name=rid,
            description=(f"{entry['name']} — Officers' Quarters "
                         f"(category: {entry.get('category', 'uncategorized')})."),
            exits=_assign_exit_keys([p for p in portals if p.from_room == rid]),
        ))

    # -- The Tap: exits are target lists, ids as-is (already tap-*).
    for entry in tap:
        rid = entry["id"]
        for target in entry["exits"]:
            portals.append(Portal(
                id=f"{rid}->{target}", from_room=rid, to_room=target,
                direction="portal", type="walk",
            ))
        rooms.append(RoomDef(
            name=rid,
            description=f"{entry['name']} — a room in The Tap, the Rust MUD.",
            exits=_assign_exit_keys([p for p in portals if p.from_room == rid]),
        ))

    # -- ScummVM Arcade / BSS: MUD schema (importFromMUDSchema semantics —
    #    direction from the exit key, locked/requiredItem preserved).
    for rid, mud_room in bss["rooms"].items():
        for direction_key, exit_def in mud_room["exits"].items():
            portals.append(Portal(
                id=f"{rid}->{exit_def['target']}", from_room=rid,
                to_room=exit_def["target"],
                direction=_MUD_DIRECTIONS.get(direction_key.lower(), "portal"),
                type="walk",
                locked=bool(exit_def.get("locked", False)),
                locked_message=exit_def.get("lockedMessage", ""),
                required_item=exit_def.get("requiredItem", ""),
            ))
        desc = mud_room.get("description", "")
        ambient = mud_room.get("ambient")
        lighting = mud_room.get("lighting")
        if ambient or lighting:
            desc += f" Ambient: {ambient or 'none'}; lighting: {lighting or 'none'}."
        rooms.append(RoomDef(
            name=rid, description=desc,
            exits=_assign_exit_keys([p for p in portals if p.from_room == rid]),
            objects=list(mud_room.get("items", [])),
            occupants=list(mud_room.get("actors", [])),
        ))

    # -- Cross-world warps, appended after each room's own exits
    #    (exactly what registry.createPortal() does to room.exits).
    portals.extend(xworld)
    by_room: Dict[str, List[Portal]] = {r.name: [] for r in rooms}
    for p in portals:
        by_room.setdefault(p.from_room, []).append(p)
    for room in rooms:
        room.exits = _assign_exit_keys(by_room.get(room.name, []))

    # -- Sanity: every portal endpoint must be a defined room.
    known = {r.name for r in rooms}
    dangling = [p.id for p in portals if p.from_room not in known or p.to_room not in known]
    if dangling:
        raise ValueError(f"portals reference unknown rooms: {dangling}")

    counts = dict(platos=len(platos), officers=len(officers), tap=len(tap), bss=len(bss["rooms"]))
    worlds = [WorldInfo(wid, wname, counts[key])
              for (wid, wname), key in zip(WORLDS, ("platos", "officers", "tap", "bss"))]
    return RegistryCorpus(worlds=worlds, rooms=rooms, portals=portals)


def _assign_exit_keys(room_portals: List[Portal]) -> Dict[str, str]:
    """Direction key per portal, unique within the room (see module docstring).
    Locked portals are skipped — they are sealed doors, not exits."""
    used: Dict[str, str] = {}
    for p in room_portals:
        if p.locked:
            continue
        key = None
        if p.direction in POSITION_DIRECTIONS and p.direction not in used:
            key = p.direction
        else:
            key = next((c for c in CAROUSEL if c not in used), None)
        if key is None:
            n = 1
            while f"portal_{n}" in used:
                n += 1
            key = f"portal_{n}"
        used[key] = p.to_room
    return used


def load_registry(import_all_path: Optional[str] = None) -> RegistryCorpus:
    """Load the vendored registry migration and build the terrain corpus."""
    path = import_all_path or DEFAULT_IMPORT_ALL
    if not os.path.exists(path):
        raise FileNotFoundError(f"import-all.ts not found: {path}")
    return parse_import_all(_read(path))


# ============================================================================
# ADJACENCY + BFS — the oracle (mirrors registry.ts findPath exactly)
# ============================================================================

def registry_adjacency(corpus: RegistryCorpus) -> Dict[str, List[str]]:
    """Directed room -> [targets] graph from the parsed portals, locked
    portals skipped — the registry's own adjacency semantics."""
    adj: Dict[str, List[str]] = {room.name: [] for room in corpus.rooms}
    for p in corpus.portals:
        if p.locked:
            continue
        adj[p.from_room].append(p.to_room)
    return adj


def corpus_exit_adjacency(corpus: RegistryCorpus) -> Dict[str, List[str]]:
    """The same graph as seen through the compiled terrain exits."""
    return {room.name: list(room.exits.values()) for room in corpus.rooms}


def find_path(adj: Dict[str, List[str]], start: str, goal: str) -> List[str]:
    """BFS shortest-hop path, mirroring registry.ts findPath(): FIFO queue,
    neighbors in insertion order, a node is visited when first enqueued.
    Returns [] when no path exists (locked doors make some pairs unreachable
    by design)."""
    if start == goal:
        return [start]
    if start not in adj or goal not in adj:
        return []
    visited = {start}
    paths: Dict[str, List[str]] = {start: [start]}
    queue = deque([start])
    while queue:
        rid = queue.popleft()
        for nbr in adj.get(rid, []):
            if nbr in visited:
                continue
            path = paths[rid] + [nbr]
            if nbr == goal:
                return path
            visited.add(nbr)
            paths[nbr] = path
            queue.append(nbr)
    return []


def bfs_distances(adj: Dict[str, List[str]], start: str) -> Dict[str, int]:
    """Hop distances to every room reachable from start (unreachables absent)."""
    dist = {start: 0}
    queue = deque([start])
    while queue:
        rid = queue.popleft()
        for nbr in adj.get(rid, []):
            if nbr not in dist:
                dist[nbr] = dist[rid] + 1
                queue.append(nbr)
    return dist


# ============================================================================
# TERRAIN WIRING
# ============================================================================

def build_terrain_core(corpus: RegistryCorpus) -> TerrainCore:
    """A TerrainCore whose truth is the registry corpus — compile_all() away."""
    core = TerrainCore()
    core.rooms = list(corpus.rooms)
    core.room_map = {room.name: room for room in corpus.rooms}
    core.objects = {}
    return core


def make_registry_server(port: int = 0, corpus: Optional[RegistryCorpus] = None) -> HTTPServer:
    """Serve the registry corpus on terrain_core's API (/rooms, /scene/*, /all).
    port=0 binds an ephemeral port (tests)."""
    core = build_terrain_core(corpus or load_registry())

    class Handler(TerrainCoreHandler):
        pass

    Handler.compiler = core
    return HTTPServer(("0.0.0.0", port), Handler)


# ============================================================================
# CLI
# ============================================================================

def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="spatial-registry → terrain: the whole chart, 33 rooms, live")
    parser.add_argument("--import-all", default=DEFAULT_IMPORT_ALL,
                        help="path to import-all.ts (default: vendored registry)")
    parser.add_argument("-o", "--output", help="write compiled scenes JSON here")
    parser.add_argument("--serve", metavar="PORT", type=int,
                        help="serve the registry corpus on this port (default off)")
    args = parser.parse_args(argv)

    corpus = load_registry(args.import_all)
    stats = corpus.stats()
    print(f"\n  spatial-registry loaded: {stats['rooms']} rooms, "
          f"{stats['worlds']} worlds, {stats['portals']} portals "
          f"({stats['locked']} locked, {stats['open']} open)")
    for w in corpus.worlds:
        print(f"    {w.id:20s} {w.name} — {w.room_count} rooms")

    adj = registry_adjacency(corpus)
    probes = [
        ("bar-rail", "tap-bar"),
        ("tap-bar", "wheelhouse"),
        ("tap-bar", "oq-poker-room"),
        ("bar-rail", "oq-bridge"),
        ("plaza", "cathedral"),  # locked chain — unreachable by design
    ]
    print("\n  Cross-world paths (registry adjacency as oracle):")
    for a, b in probes:
        path = find_path(adj, a, b)
        shown = " -> ".join(path) if path else "(no path — locked)"
        print(f"    {a} -> {b}: {shown}")

    if args.output:
        core = build_terrain_core(corpus)
        scenes = core.compile_all()
        output = {
            "meta": {"source": args.import_all, **stats},
            "rooms": scenes,
            "exits": {r.name: dict(r.exits) for r in corpus.rooms},
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"\n  wrote {args.output} ({len(scenes)} room scenes)")

    if args.serve:
        print(f"\n  serving on http://localhost:{args.serve} (/rooms, /scene/<room>, /all)")
        make_registry_server(args.serve, corpus).serve_forever()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
