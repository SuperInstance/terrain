"""
test_compiler.py — Tests for Three.js scene compiler.
"""

import pytest
from terrain_core import (
    compile_room, compile_to_json, generate_scene,
    RoomDef, ObjectDef, parse_mud_room, parse_mud_file
)


# ============================================================================
# FIXTURES
# ============================================================================

ENGINE_ROOM_MUD = """Room: engine_room
Description: The engine room thrums with diesel power. Twin engines drive the stern drive.
Exits: north -> wheelhouse, down -> galley
Objects: port_engine, stbd_engine, tool_rack, fuel_lines
Occupants: engineer_bot
Theme: engine_room
"""

WHEELHOUSE_MUD = """Room: wheelhouse
Description: The wheelhouse is the nerve center of the vessel.
Exits: aft -> aft_cockpit, down -> galley
Objects: helm_wheel, radar_display, compass_rose
Occupants: captain
Theme: wheelhouse
"""

MINIMAL_ROOM_MUD = """Room: storage
Description: Empty storage locker.
Exits:
Objects:
Occupants:
"""


# ============================================================================
# HELPER
# ============================================================================

def compile_mud(mud_text: str) -> dict:
    room = parse_mud_room(mud_text)
    scene = compile_room(room, {})
    return compile_to_json(scene)


# ============================================================================
# TESTS — compile_room
# ============================================================================

class TestCompileRoom:
    def test_compile_returns_expected_keys(self):
        scene = compile_mud(WHEELHOUSE_MUD)
        assert "room" in scene
        assert "description" in scene
        assert "theme" in scene
        assert "floor" in scene
        assert "walls" in scene
        assert "ceiling" in scene
        assert "objects" in scene
        assert "agents" in scene
        assert "exits" in scene
        assert "lights" in scene
        assert "camera" in scene

    def test_compile_room_name_in_output(self):
        scene = compile_mud(WHEELHOUSE_MUD)
        assert scene["room"] == "wheelhouse"

    def test_compile_description_in_output(self):
        scene = compile_mud(WHEELHOUSE_MUD)
        assert "nerve center" in scene["description"]

    def test_compile_theme_has_bg_fg_accent(self):
        scene = compile_mud(WHEELHOUSE_MUD)
        assert "bg" in scene["theme"]
        assert "fg" in scene["theme"]
        assert "accent" in scene["theme"]

    def test_compile_floor_has_geometry_and_material(self):
        scene = compile_mud(WHEELHOUSE_MUD)
        floor = scene["floor"]
        assert "geometry" in floor
        assert "material" in floor
        assert floor["geometry"]["type"] == "PlaneGeometry"

    def test_compile_walls_list_exists(self):
        scene = compile_mud(WHEELHOUSE_MUD)
        assert isinstance(scene["walls"], list)
        assert len(scene["walls"]) >= 4  # north, south, east, west

    def test_compile_ceiling_exists(self):
        scene = compile_mud(WHEELHOUSE_MUD)
        assert scene["ceiling"] is not None
        assert "geometry" in scene["ceiling"]

    def test_compile_exits_list(self):
        scene = compile_mud(WHEELHOUSE_MUD)
        assert isinstance(scene["exits"], list)
        assert len(scene["exits"]) == 2
        directions = [e["direction"] for e in scene["exits"]]
        assert "aft" in directions
        assert "down" in directions

    def test_compile_exits_have_target_room(self):
        scene = compile_mud(WHEELHOUSE_MUD)
        for exit in scene["exits"]:
            assert "target" in exit
            assert exit["target"] != ""

    def test_compile_lights_list(self):
        scene = compile_mud(WHEELHOUSE_MUD)
        assert isinstance(scene["lights"], list)
        assert len(scene["lights"]) >= 1

    def test_compile_camera_has_position(self):
        scene = compile_mud(WHEELHOUSE_MUD)
        camera = scene["camera"]
        assert "position" in camera
        assert "x" in camera["position"]
        assert "y" in camera["position"]
        assert "z" in camera["position"]

    def test_compile_objects_from_room_objects(self):
        scene = compile_mud(ENGINE_ROOM_MUD)
        # 4 objects in engine_room mud text
        assert len(scene["objects"]) == 4
        obj_names = [o["name"] for o in scene["objects"]]
        assert "port_engine" in obj_names
        assert "stbd_engine" in obj_names

    def test_compile_agents_from_occupants(self):
        scene = compile_mud(WHEELHOUSE_MUD)
        agents = scene["agents"]
        assert len(agents) == 1
        assert agents[0]["name"] == "captain"

    def test_compile_agent_has_position_and_color(self):
        scene = compile_mud(WHEELHOUSE_MUD)
        agent = scene["agents"][0]
        assert "position" in agent
        assert "color" in agent

    def test_compile_objects_have_scale(self):
        scene = compile_mud(ENGINE_ROOM_MUD)
        for obj in scene["objects"]:
            assert "scale" in obj

    def test_compile_exits_have_direction(self):
        scene = compile_mud(WHEELHOUSE_MUD)
        for exit in scene["exits"]:
            assert "direction" in exit

    def test_compile_exits_have_glow_flag(self):
        scene = compile_mud(WHEELHOUSE_MUD)
        for exit in scene["exits"]:
            assert "glow" in exit
            assert exit["glow"] is True


# ============================================================================
# TESTS — compile_to_json
# ============================================================================

class TestCompileToJson:
    def test_output_is_json_serializable(self):
        import json
        scene = compile_mud(WHEELHOUSE_MUD)
        # Should not raise
        json_str = json.dumps(scene)
        assert json_str is not None

    def test_output_is_dict(self):
        scene = compile_mud(WHEELHOUSE_MUD)
        assert isinstance(scene, dict)


# ============================================================================
# TESTS — generate_scene
# ============================================================================

class TestGenerateScene:
    def test_generate_scene_from_roomdef(self):
        room = RoomDef(
            name="test_room",
            description="A test room with metal walls.",
            exits={"north": "other_room"},
            objects=["engine"],
            occupants=["agent1"]
        )
        scene = generate_scene(room, {})
        assert scene["room"] == "test_room"
        assert "test room" in scene["description"]

    def test_generate_scene_with_objects_dict(self):
        objects = {
            "engine": ObjectDef(
                name="engine",
                obj_type="engine",
                shape="cylinder",
                color="#445566",
                size="huge"
            )
        }
        room = RoomDef(
            name="eng",
            description="Engine room",
            objects=["engine"]
        )
        scene = generate_scene(room, objects)
        assert len(scene["objects"]) == 1

    def test_empty_objects_and_occupants(self):
        room = RoomDef(name="empty", description="Empty room")
        scene = generate_scene(room, {})
        assert scene["objects"] == []
        assert scene["agents"] == []


# ============================================================================
# TESTS — theme inference
# ============================================================================

class TestThemeInference:
    def test_engine_room_theme_auto_inferred(self):
        room = parse_mud_room(ENGINE_ROOM_MUD)
        scene_dict = compile_to_json(compile_room(room, {}))
        # engine_room theme should be detected from description keywords
        assert scene_dict["theme"]["accent"] == "#4488ff"

    def test_wheelhouse_theme_set_explicitly(self):
        room = parse_mud_room(WHEELHOUSE_MUD)
        scene_dict = compile_to_json(compile_room(room, {}))
        # wheelhouse theme set explicitly
        assert scene_dict["theme"]["bg"] is not None


# ============================================================================
# TESTS — material inference
# ============================================================================

class TestMaterialInference:
    def test_floor_material_in_scene(self):
        room = parse_mud_room(ENGINE_ROOM_MUD)
        scene_dict = compile_to_json(compile_room(room, {}))
        assert "metalness" in scene_dict["floor"]["material"]

    def test_wall_material_in_scene(self):
        room = parse_mud_room(WHEELHOUSE_MUD)
        scene_dict = compile_to_json(compile_room(room, {}))
        for wall in scene_dict["walls"]:
            assert "material" in wall