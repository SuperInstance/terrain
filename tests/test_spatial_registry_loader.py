"""
test_spatial_registry_loader.py — the whole chart, 33 rooms, live.

Unit tests for the import-all.ts parser, compile-all coverage for the
33-room corpus, and the oracle contract: cross-world paths resolved via
the registry's own adjacency (mirrored from registry.ts findPath) must
agree with the compiled terrain exits — they must never disagree.
"""

import json
import os
import subprocess
import sys
import threading
import urllib.request
import urllib.error

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import spatial_registry_loader as srl
from spatial_registry_loader import (
    RegistryCorpus, load_registry, parse_import_all,
    registry_adjacency, corpus_exit_adjacency,
    find_path, bfs_distances, build_terrain_core, make_registry_server,
)
from terrain_core import ROOM_THEMES

IMPORT_ALL_PATH = os.path.join(
    REPO_ROOT, "external", "spatial-registry", "src", "migrations", "import-all.ts"
)


@pytest.fixture(scope="module")
def corpus() -> RegistryCorpus:
    return load_registry()


# ============================================================================
# PARSING — the import-all.ts literals
# ============================================================================

class TestParsing:
    def test_import_all_file_exists(self):
        assert os.path.exists(IMPORT_ALL_PATH)

    def test_thirty_three_rooms_four_worlds(self, corpus):
        stats = corpus.stats()
        assert stats["rooms"] == 33
        assert stats["worlds"] == 4

    def test_world_sizes(self, corpus):
        sizes = {w.id: w.room_count for w in corpus.worlds}
        # Plato's Shell: header comment claims 13, the array holds 12 (see
        # loader docstring). 12 + 12 + 3 + 6 = 33.
        assert sizes == {
            "platos-shell": 12,
            "officers-quarters": 12,
            "the-tap": 3,
            "scummvm-bss": 6,
        }

    def test_room_ids_unique(self, corpus):
        names = [r.name for r in corpus.rooms]
        assert len(names) == len(set(names)) == 33

    def test_world_names(self, corpus):
        names = {w.id: w.name for w in corpus.worlds}
        assert names["platos-shell"] == "Plato's Shell"
        assert names["officers-quarters"] == "Officers' Quarters"
        assert names["the-tap"] == "The Tap (Rust)"
        assert names["scummvm-bss"] == "Beneath a Steel Sky — MUD Twin"

    def test_sixty_six_portals_three_locked(self, corpus):
        stats = corpus.stats()
        assert stats["portals"] == 66
        assert stats["locked"] == 3
        assert stats["open"] == 63

    def test_officers_rooms_prefixed(self, corpus):
        names = {r.name for r in corpus.rooms}
        assert "oq-bridge" in names
        assert "oq-galley" in names
        assert "bridge" not in names          # no collision with platos-shell
        assert "galley" in names              # platos-shell keeps the bare id

    def test_platos_directions_preserved_when_unique(self, corpus):
        wheelhouse = next(r for r in corpus.rooms if r.name == "wheelhouse")
        assert wheelhouse.exits["south"] == "aft-deck"
        assert wheelhouse.exits["west"] == "galley"
        # engine-room shares registry direction 'south' -> carousel key,
        # but the TARGET (adjacency) survives:
        assert "engine-room" in wheelhouse.exits.values()

    def test_duplicate_directions_get_unique_keys(self, corpus):
        for room in corpus.rooms:
            keys = list(room.exits.keys())
            targets = list(room.exits.values())
            assert len(keys) == len(targets)   # dict guarantees unique keys
            assert len(targets) == len(set(targets)), room.name

    def test_exit_count_matches_open_portals(self, corpus):
        open_per_room = {}
        for p in corpus.portals:
            if not p.locked:
                open_per_room[p.from_room] = open_per_room.get(p.from_room, 0) + 1
        for room in corpus.rooms:
            assert len(room.exits) == open_per_room.get(room.name, 0), room.name

    def test_bss_descriptions_carried(self, corpus):
        plaza = next(r for r in corpus.rooms if r.name == "plaza")
        assert plaza.description.startswith("The plaza stretches before you")
        assert "industrial_hum" in plaza.description

    def test_bss_items_and_actors(self, corpus):
        plaza = next(r for r in corpus.rooms if r.name == "plaza")
        assert plaza.objects == ["wrench"]
        assert plaza.occupants == ["joey"]
        checkpoint = next(r for r in corpus.rooms if r.name == "checkpoint")
        assert checkpoint.objects == ["key_card"]
        assert checkpoint.occupants == ["guard"]

    def test_locked_portals_not_exits_but_recorded(self, corpus):
        locked = corpus.locked_portals
        assert {(p.from_room, p.to_room) for p in locked} == {
            ("plaza", "checkpoint"),          # key_card
            ("factory", "factory_maintenance"),  # wrench
            ("checkpoint", "cathedral"),      # security_pass
        }
        plaza = next(r for r in corpus.rooms if r.name == "plaza")
        assert "checkpoint" not in plaza.exits.values()
        assert set(plaza.exits.values()) == {"factory", "apartment"}

    def test_six_cross_world_portals(self, corpus):
        xworld = [p for p in corpus.portals if p.type == "warp"]
        assert len(xworld) == 6
        assert {(p.from_room, p.to_room) for p in xworld} == {
            ("bar-rail", "tap-bar"), ("tap-bar", "bar-rail"),
            ("poker-room", "oq-poker-room"), ("oq-poker-room", "poker-room"),
            ("oq-bridge", "wheelhouse"), ("wheelhouse", "oq-bridge"),
        }

    def test_cross_world_exits_land_in_rooms(self, corpus):
        by_name = {r.name: r for r in corpus.rooms}
        assert "tap-bar" in by_name["bar-rail"].exits.values()
        assert "bar-rail" in by_name["tap-bar"].exits.values()
        assert "oq-poker-room" in by_name["poker-room"].exits.values()
        assert "wheelhouse" in by_name["oq-bridge"].exits.values()

    def test_every_room_has_description_and_exits(self, corpus):
        for room in corpus.rooms:
            assert room.description, f"{room.name}: no description"
            assert room.exits, f"{room.name}: no exits"

    def test_no_dangling_exit_targets(self, corpus):
        names = {r.name for r in corpus.rooms}
        for room in corpus.rooms:
            for target in room.exits.values():
                assert target in names, f"{room.name} -> {target} dangles"

    def test_malformed_source_fails_loudly(self):
        with pytest.raises(ValueError):
            parse_import_all("const PLATOS_SHELL_ROOMS = [] as const;\n")

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_registry("/nonexistent/import-all.ts")


# ============================================================================
# COMPILATION — all 33 rooms through compile_all()
# ============================================================================

class TestCompileAll:
    def test_compile_all_returns_33_scenes(self, corpus):
        scenes = build_terrain_core(corpus).compile_all()
        assert len(scenes) == 33
        assert all(scene is not None for scene in scenes.values())

    def test_every_scene_well_formed(self, corpus):
        for name, scene in build_terrain_core(corpus).compile_all().items():
            assert scene["room"] == name
            for part in ("description", "theme", "floor", "walls", "ceiling",
                         "objects", "agents", "exits", "lights", "camera"):
                assert part in scene, f"{name}: missing {part}"
            assert len(scene["walls"]) == 4
            assert scene["exits"], f"{name}: no compiled exits"

    def test_scene_exit_targets_resolve(self, corpus):
        names = {r.name for r in corpus.rooms}
        for scene in build_terrain_core(corpus).compile_all().values():
            for exit_ in scene["exits"]:
                assert exit_["target"] in names

    def test_engine_room_theme_inferred(self, corpus):
        scenes = build_terrain_core(corpus).compile_all()
        assert scenes["engine-room"]["theme"]["bg"] == ROOM_THEMES["engine_room"]["bg"]
        assert scenes["oq-bridge"]["theme"]["bg"] == ROOM_THEMES["wheelhouse"]["bg"]

    def test_bss_objects_and_agents_render(self, corpus):
        scenes = build_terrain_core(corpus).compile_all()
        assert [o["name"] for o in scenes["plaza"]["objects"]] == ["wrench"]
        assert [a["name"] for a in scenes["plaza"]["agents"]] == ["joey"]

    def test_oq_bridge_has_twelve_exits(self, corpus):
        scene = build_terrain_core(corpus).compile("oq-bridge")
        assert len(scene["exits"]) == 12   # 11 stations + warp to wheelhouse


# ============================================================================
# ORACLE — registry adjacency vs terrain exits: never disagree
# ============================================================================

class TestOracleParity:
    def test_neighbor_sets_identical(self, corpus):
        oracle = registry_adjacency(corpus)
        terrain = corpus_exit_adjacency(corpus)
        assert set(oracle) == set(terrain)
        for room in oracle:
            assert set(oracle[room]) == set(terrain[room]), room
            assert len(oracle[room]) == len(terrain[room]), room

    def test_all_pairs_shortest_distances_identical(self, corpus):
        oracle = registry_adjacency(corpus)
        terrain = corpus_exit_adjacency(corpus)
        for start in oracle:
            assert bfs_distances(oracle, start) == bfs_distances(terrain, start), start

    def test_paths_identical_for_every_pair(self, corpus):
        oracle = registry_adjacency(corpus)
        terrain = corpus_exit_adjacency(corpus)
        for start in oracle:
            for goal in oracle:
                assert (find_path(oracle, start, goal)
                        == find_path(terrain, start, goal)), (start, goal)

    def test_bar_rail_to_tap_bar_direct_warp(self, corpus):
        adj = registry_adjacency(corpus)
        assert find_path(adj, "bar-rail", "tap-bar") == ["bar-rail", "tap-bar"]

    def test_tap_bar_to_wheelhouse(self, corpus):
        adj = registry_adjacency(corpus)
        assert find_path(adj, "tap-bar", "wheelhouse") == \
            ["tap-bar", "bar-rail", "aft-deck", "wheelhouse"]

    def test_tap_bar_to_oq_poker_room(self, corpus):
        adj = registry_adjacency(corpus)
        assert find_path(adj, "tap-bar", "oq-poker-room") == \
            ["tap-bar", "bar-rail", "poker-room", "oq-poker-room"]

    def test_bar_rail_to_oq_bridge(self, corpus):
        adj = registry_adjacency(corpus)
        assert find_path(adj, "bar-rail", "oq-bridge") == \
            ["bar-rail", "aft-deck", "wheelhouse", "oq-bridge"]

    def test_locked_chains_unreachable_by_design(self, corpus):
        adj = registry_adjacency(corpus)
        assert find_path(adj, "plaza", "cathedral") == []
        assert find_path(adj, "factory", "factory_maintenance") == []

    def test_worlds_connected_except_bss_island(self, corpus):
        adj = registry_adjacency(corpus)
        from_bar_rail = bfs_distances(adj, "bar-rail")
        assert len(from_bar_rail) == 27          # platos 12 + officers 12 + tap 3
        assert not any(r in from_bar_rail for r in
                       ("plaza", "factory", "cathedral"))  # BSS has no portals out
        # Inside BSS the locked doors split the world further: from plaza only
        # factory and apartment are reachable (wrench/key_card/security_pass).
        assert set(bfs_distances(adj, "plaza")) == {"plaza", "factory", "apartment"}
        assert find_path(adj, "plaza", "factory_maintenance") == []


# ============================================================================
# SERVER + CLI
# ============================================================================

class TestServer:
    def test_all_endpoint_returns_33_rooms(self, corpus):
        server = make_registry_server(port=0, corpus=corpus)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with urllib.request.urlopen(f"{base}/all", timeout=5) as resp:
                scenes = json.loads(resp.read().decode())
            assert len(scenes) == 33
            with urllib.request.urlopen(f"{base}/rooms", timeout=5) as resp:
                rooms = json.loads(resp.read().decode())["rooms"]
            assert len(rooms) == 33
            with urllib.request.urlopen(f"{base}/scene/oq-bridge", timeout=5) as resp:
                scene = json.loads(resp.read().decode())
            assert scene["room"] == "oq-bridge"
            with pytest.raises(urllib.error.HTTPError):
                urllib.request.urlopen(f"{base}/scene/no-such-room", timeout=5)
        finally:
            server.shutdown()
            server.server_close()


class TestCLI:
    def test_cli_compiles_and_writes_json(self, tmp_path):
        out = tmp_path / "registry_scenes.json"
        proc = subprocess.run(
            [sys.executable, "spatial_registry_loader.py", "--output", str(out)],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["meta"]["rooms"] == 33
        assert data["meta"]["portals"] == 66
        assert len(data["rooms"]) == 33
        assert data["exits"]["bar-rail"]["east"] == "aft-deck"
