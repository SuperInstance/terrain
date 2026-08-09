"""
test_integration.py — End-to-end integration tests.
"""

import pytest
import json
import os
import shutil
import subprocess
import sys

# Ensure the repo root is on the path so terrain_core can be imported
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from terrain_core import (
    load_mud_file, generate_scene, generate_all_scenes,
    compile_room, compile_to_json, TerrainCore
)

# Setup: copy necessary files to /tmp/terrain for the integration tests
TERRAIN_TMP = "/tmp/terrain"

@pytest.fixture(autouse=True, scope="session")
def setup_terrain_files():
    """Copy terrain files to /tmp/terrain/ before tests, clean up after."""
    os.makedirs(TERRAIN_TMP, exist_ok=True)
    for fname in ["rooms.mud", "scene.json", "terrain_core.py"]:
        src = os.path.join(REPO_ROOT, fname)
        dst = os.path.join(TERRAIN_TMP, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
    yield
    # Cleanup is optional — leave files for debugging
    # shutil.rmtree(TERRAIN_TMP, ignore_errors=True)


# ============================================================================
# TESTS — load and verify rooms.mud
# ============================================================================

class TestRoomsMud:
    def test_rooms_mud_file_exists(self):
        assert os.path.exists("/tmp/terrain/rooms.mud")

    def test_five_rooms_in_file(self):
        rooms, objects = load_mud_file("/tmp/terrain/rooms.mud")
        assert len(rooms) == 5

    def test_all_expected_rooms_present(self):
        rooms, objects = load_mud_file("/tmp/terrain/rooms.mud")
        names = [r.name for r in rooms]
        expected = ["wheelhouse", "galley", "foredeck", "engine_room", "aft_cockpit"]
        for name in expected:
            assert name in names, f"Room {name} not found in {names}"

    def test_rooms_have_exits(self):
        rooms, objects = load_mud_file("/tmp/terrain/rooms.mud")
        for room in rooms:
            assert len(room.exits) > 0, f"Room {room.name} has no exits"

    def test_rooms_have_descriptions(self):
        rooms, objects = load_mud_file("/tmp/terrain/rooms.mud")
        for room in rooms:
            assert len(room.description) > 0, f"Room {room.name} has no description"

    def test_wheelhouse_exits_correctly(self):
        rooms, objects = load_mud_file("/tmp/terrain/rooms.mud")
        wh = next(r for r in rooms if r.name == "wheelhouse")
        assert "aft" in wh.exits
        assert wh.exits["aft"] == "aft_cockpit"
        assert "down" in wh.exits
        assert wh.exits["down"] == "galley"

    def test_engine_room_exits_correctly(self):
        rooms, objects = load_mud_file("/tmp/terrain/rooms.mud")
        er = next(r for r in rooms if r.name == "engine_room")
        assert "up" in er.exits
        assert er.exits["up"] == "foredeck"
        assert "forward" in er.exits
        assert er.exits["forward"] == "aft_cockpit"


# ============================================================================
# TESTS — generate scenes from rooms.mud
# ============================================================================

class TestGenerateAllScenes:
    def test_generate_all_scenes_returns_dict(self):
        rooms, objects = load_mud_file("/tmp/terrain/rooms.mud")
        scenes = generate_all_scenes(rooms, objects)
        assert isinstance(scenes, dict)
        assert len(scenes) == 5

    def test_all_scenes_have_meta_keys(self):
        rooms, objects = load_mud_file("/tmp/terrain/rooms.mud")
        scenes = generate_all_scenes(rooms, objects)
        for name, scene in scenes.items():
            assert "room" in scene
            assert "description" in scene
            assert "theme" in scene
            assert "floor" in scene
            assert "walls" in scene
            assert "exits" in scene
            assert "lights" in scene

    def test_all_five_room_names_present(self):
        rooms, objects = load_mud_file("/tmp/terrain/rooms.mud")
        scenes = generate_all_scenes(rooms, objects)
        for expected in ["wheelhouse", "galley", "foredeck", "engine_room", "aft_cockpit"]:
            assert expected in scenes

    def test_scene_json_has_meta_rooms_exits_keys(self):
        rooms, objects = load_mud_file("/tmp/terrain/rooms.mud")
        scenes = generate_all_scenes(rooms, objects)
        # Each scene is a dict with expected top-level keys
        for name, scene in scenes.items():
            assert "theme" in scene
            assert "camera" in scene


# ============================================================================
# TESTS — TerrainCore API
# ============================================================================

class TestTerrainCore:
    def test_terrain_core_loads_rooms(self):
        tc = TerrainCore("/tmp/terrain/rooms.mud")
        assert len(tc.rooms) == 5

    def test_list_rooms(self):
        tc = TerrainCore("/tmp/terrain/rooms.mud")
        rooms = tc.list_rooms()
        assert len(rooms) == 5

    def test_get_room(self):
        tc = TerrainCore("/tmp/terrain/rooms.mud")
        room = tc.get_room("wheelhouse")
        assert room is not None
        assert room.name == "wheelhouse"

    def test_get_room_returns_none_for_missing(self):
        tc = TerrainCore("/tmp/terrain/rooms.mud")
        room = tc.get_room("nonexistent_room")
        assert room is None

    def test_compile_single_room(self):
        tc = TerrainCore("/tmp/terrain/rooms.mud")
        scene = tc.compile("engine_room")
        assert scene is not None
        assert scene["room"] == "engine_room"

    def test_compile_all(self):
        tc = TerrainCore("/tmp/terrain/rooms.mud")
        scenes = tc.compile_all()
        assert len(scenes) == 5


# ============================================================================
# TESTS — CLI output
# ============================================================================

class TestCliOutput:
    def test_terrain_core_cli_runs(self):
        result = subprocess.run(
            ["python3", "/tmp/terrain/terrain_core.py", "/tmp/terrain/rooms.mud", "-o", "/tmp/test_scene.json"],
            capture_output=True,
            text=True,
            cwd="/tmp/terrain"
        )
        assert result.returncode == 0
        assert "Loaded" in result.stdout
        assert "Wrote" in result.stdout

    def test_output_file_exists(self):
        # Run CLI first
        subprocess.run(
            ["python3", "/tmp/terrain/terrain_core.py", "/tmp/terrain/rooms.mud", "-o", "/tmp/test_scene.json"],
            capture_output=True,
            cwd="/tmp/terrain"
        )
        assert os.path.exists("/tmp/test_scene.json")

    def test_output_file_is_valid_json(self):
        # Run CLI first
        subprocess.run(
            ["python3", "/tmp/terrain/terrain_core.py", "/tmp/terrain/rooms.mud", "-o", "/tmp/test_scene.json"],
            capture_output=True,
            cwd="/tmp/terrain"
        )
        with open("/tmp/test_scene.json", "r") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_output_json_has_meta_rooms_exits(self):
        # Run CLI first
        subprocess.run(
            ["python3", "/tmp/terrain/terrain_core.py", "/tmp/terrain/rooms.mud", "-o", "/tmp/test_scene.json"],
            capture_output=True,
            cwd="/tmp/terrain"
        )
        with open("/tmp/test_scene.json", "r") as f:
            data = json.load(f)
        assert "meta" in data
        assert "rooms" in data
        assert "exits" in data

    def test_output_json_has_five_rooms(self):
        # Run CLI first
        subprocess.run(
            ["python3", "/tmp/terrain/terrain_core.py", "/tmp/terrain/rooms.mud", "-o", "/tmp/test_scene.json"],
            capture_output=True,
            cwd="/tmp/terrain"
        )
        with open("/tmp/test_scene.json", "r") as f:
            data = json.load(f)
        assert len(data["rooms"]) == 5

    def test_output_meta_has_room_count(self):
        subprocess.run(
            ["python3", "/tmp/terrain/terrain_core.py", "/tmp/terrain/rooms.mud", "-o", "/tmp/test_scene.json"],
            capture_output=True,
            cwd="/tmp/terrain"
        )
        with open("/tmp/test_scene.json", "r") as f:
            data = json.load(f)
        assert data["meta"]["roomCount"] == 5

    def test_output_exits_graph_populated(self):
        subprocess.run(
            ["python3", "/tmp/terrain/terrain_core.py", "/tmp/terrain/rooms.mud", "-o", "/tmp/test_scene.json"],
            capture_output=True,
            cwd="/tmp/terrain"
        )
        with open("/tmp/test_scene.json", "r") as f:
            data = json.load(f)
        assert len(data["exits"]) == 5
        assert "wheelhouse" in data["exits"]
        assert "engine_room" in data["exits"]


# ============================================================================
# TESTS — compare with generated scene.json
# ============================================================================

class TestSceneJsonMatches:
    def test_scene_json_exists(self):
        assert os.path.exists("/tmp/terrain/scene.json")

    def test_scene_json_valid(self):
        with open("/tmp/terrain/scene.json", "r") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_scene_json_has_meta(self):
        with open("/tmp/terrain/scene.json", "r") as f:
            data = json.load(f)
        assert "meta" in data

    def test_scene_json_has_rooms(self):
        with open("/tmp/terrain/scene.json", "r") as f:
            data = json.load(f)
        assert "rooms" in data

    def test_scene_json_has_exits(self):
        with open("/tmp/terrain/scene.json", "r") as f:
            data = json.load(f)
        assert "exits" in data

    def test_scene_json_room_count(self):
        with open("/tmp/terrain/scene.json", "r") as f:
            data = json.load(f)
        assert data["meta"]["roomCount"] == 5

    def test_scene_json_matches_cli_output(self):
        # CLI output should match pre-generated scene.json
        subprocess.run(
            ["python3", "/tmp/terrain/terrain_core.py", "/tmp/terrain/rooms.mud", "-o", "/tmp/test_scene.json"],
            capture_output=True,
            cwd="/tmp/terrain"
        )
        with open("/tmp/terrain/scene.json", "r") as f:
            expected = json.load(f)
        with open("/tmp/test_scene.json", "r") as f:
            actual = json.load(f)
        assert expected["meta"]["roomCount"] == actual["meta"]["roomCount"]
        assert set(expected["rooms"].keys()) == set(actual["rooms"].keys())