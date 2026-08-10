"""
test_edge_cases.py — Edge case and bug regression tests.

Covers edge cases discovered during code audit:
- "none" literal in Objects/Occupants fields
- Empty/whitespace input handling
- Exit parsing edge cases (whitespace, trailing commas, missing arrows)
- Missing file handling in TerrainCore
- Material/shape inference with empty strings
- Multi-line description parsing
- Object-only files (no rooms)
- Description lines containing directive keywords
- Compiled scene structural integrity
"""

import pytest
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from terrain_core import (
    parse_mud_room, parse_mud_file, parse_object_def, load_mud_file,
    compile_room, compile_to_json, generate_scene, generate_all_scenes,
    infer_material, infer_shape, infer_size,
    TerrainCore, RoomDef, ObjectDef, CompiledScene,
    MATERIAL_MAP, SHAPE_MAP, SIZE_SCALE, ROOM_THEMES,
)


# ============================================================================
# BUG REGRESSION: "none" literal in Objects/Occupants
# ============================================================================

class TestNoneLiteral:
    """'Occupants: none' and 'Objects: none' should produce empty lists, not ['none']."""

    def test_occupants_none_produces_empty_list(self):
        room = parse_mud_room("Room: test\nDescription: Test\nOccupants: none")
        assert room.occupants == []

    def test_objects_none_produces_empty_list(self):
        room = parse_mud_room("Room: test\nDescription: Test\nObjects: none")
        assert room.objects == []

    def test_occupants_NONE_case_insensitive(self):
        room = parse_mud_room("Room: test\nDescription: Test\nOccupants: NONE")
        assert room.occupants == []

    def test_occupants_None_case_insensitive(self):
        room = parse_mud_room("Room: test\nDescription: Test\nOccupants: None")
        assert room.occupants == []

    def test_objects_NONE_case_insensitive(self):
        room = parse_mud_room("Room: test\nDescription: Test\nObjects: NONE")
        assert room.objects == []

    def test_occupants_none_no_phantom_agent_in_scene(self):
        """Verify that 'Occupants: none' doesn't create a phantom agent."""
        room = parse_mud_room("Room: test\nDescription: Test\nOccupants: none")
        scene = compile_room(room, {})
        scene_dict = compile_to_json(scene)
        assert scene_dict["agents"] == []

    def test_objects_none_no_phantom_object_in_scene(self):
        """Verify that 'Objects: none' doesn't create a phantom object."""
        room = parse_mud_room("Room: test\nDescription: Test\nObjects: none")
        scene = compile_room(room, {})
        scene_dict = compile_to_json(scene)
        assert scene_dict["objects"] == []

    def test_occupants_with_real_names_still_works(self):
        room = parse_mud_room("Room: test\nDescription: Test\nOccupants: agent1, agent2")
        assert room.occupants == ["agent1", "agent2"]

    def test_objects_with_real_names_still_works(self):
        room = parse_mud_room("Room: test\nDescription: Test\nObjects: obj1, obj2")
        assert room.objects == ["obj1", "obj2"]


# ============================================================================
# EDGE CASES: Empty / whitespace input
# ============================================================================

class TestEmptyInput:
    def test_parse_empty_string(self):
        room = parse_mud_room("")
        assert room.name == "unknown"
        assert room.description == ""

    def test_parse_whitespace_only(self):
        room = parse_mud_room("   \n   \n   ")
        assert room.name == "unknown"

    def test_parse_file_empty_string(self):
        rooms, objects = parse_mud_file("")
        assert rooms == []
        assert objects == {}

    def test_parse_file_whitespace_only(self):
        rooms, objects = parse_mud_file("  \n  \n  ")
        assert rooms == []
        assert objects == {}

    def test_parse_object_def_empty(self):
        obj = parse_object_def("")
        assert obj.name == "unknown"

    def test_compile_room_with_minimal_roomdef(self):
        room = RoomDef(name="void", description="")
        scene = compile_room(room, {})
        assert scene.room == "void"


# ============================================================================
# EDGE CASES: Exit parsing
# ============================================================================

class TestExitParsing:
    def test_exit_extra_whitespace_around_arrow(self):
        room = parse_mud_room(
            "Room: test\nDescription: Test\n"
            "Exits: north  ->  room1 ,  south ->room2"
        )
        assert room.exits["north"] == "room1"
        assert room.exits["south"] == "room2"

    def test_exit_no_arrow_ignored(self):
        room = parse_mud_room(
            "Room: test\nDescription: Test\nExits: north room1"
        )
        assert room.exits == {}

    def test_exit_trailing_comma(self):
        room = parse_mud_room(
            "Room: test\nDescription: Test\nExits: north -> room1,"
        )
        assert room.exits == {"north": "room1"}

    def test_exit_single_direction(self):
        room = parse_mud_room(
            "Room: test\nDescription: Test\nExits: port -> dock"
        )
        assert len(room.exits) == 1
        assert room.exits["port"] == "dock"

    def test_exit_empty_exits_field(self):
        room = parse_mud_room(
            "Room: test\nDescription: Test\nExits:"
        )
        assert room.exits == {}


# ============================================================================
# EDGE CASES: Objects parsing
# ============================================================================

class TestObjectsParsing:
    def test_objects_trailing_comma(self):
        room = parse_mud_room(
            "Room: test\nDescription: Test\nObjects: obj1, obj2,"
        )
        assert room.objects == ["obj1", "obj2"]

    def test_objects_single_object(self):
        room = parse_mud_room(
            "Room: test\nDescription: Test\nObjects: only_one"
        )
        assert room.objects == ["only_one"]

    def test_objects_empty_field(self):
        room = parse_mud_room(
            "Room: test\nDescription: Test\nObjects:"
        )
        assert room.objects == []


# ============================================================================
# EDGE CASES: TerrainCore error handling
# ============================================================================

class TestTerrainCoreErrors:
    def test_missing_file_raises_filenotfound(self):
        with pytest.raises(FileNotFoundError):
            TerrainCore("/nonexistent/path/file.mud")

    def test_missing_file_message_includes_path(self):
        try:
            TerrainCore("/nonexistent/path/file.mud")
        except FileNotFoundError as e:
            assert "/nonexistent/path/file.mud" in str(e)

    def test_compile_nonexistent_room_returns_none(self):
        tc = TerrainCore()
        assert tc.compile("nonexistent") is None

    def test_get_nonexistent_room_returns_none(self):
        tc = TerrainCore()
        assert tc.get_room("nonexistent") is None

    def test_empty_terrain_core_lists(self):
        tc = TerrainCore()
        assert tc.list_rooms() == []
        assert tc.compile_all() == {}


# ============================================================================
# EDGE CASES: Material inference
# ============================================================================

class TestMaterialInference:
    def test_empty_description_returns_default(self):
        mat = infer_material("")
        assert mat["color"] == "#888888"
        assert mat["metalness"] == 0.0
        assert mat["roughness"] == 0.5

    def test_metal_keyword(self):
        mat = infer_material("a metal surface")
        assert mat["metalness"] == 0.9

    def test_wood_keyword(self):
        mat = infer_material("wooden plank")
        assert mat["roughness"] == 0.8

    def test_water_keyword_has_opacity(self):
        mat = infer_material("water surface")
        assert "opacity" in mat

    def test_brass_keyword(self):
        mat = infer_material("brass fitting")
        assert mat["metalness"] == 0.85

    def test_first_match_wins(self):
        """When multiple material keywords present, first in MATERIAL_MAP wins."""
        mat = infer_material("metal and wood")
        assert mat["metalness"] == 0.9  # metal wins (first in dict)

    def test_all_material_keywords_present(self):
        """Verify all MATERIAL_MAP keywords are detectable."""
        for keyword in MATERIAL_MAP:
            mat = infer_material(f"test {keyword} test")
            # Should not be the default
            assert mat != {"color": "#888888", "metalness": 0.0, "roughness": 0.5}


# ============================================================================
# EDGE CASES: Shape inference
# ============================================================================

class TestShapeInference:
    def test_empty_strings_return_box(self):
        assert infer_shape("", "") == "box"

    def test_engine_in_name(self):
        assert infer_shape("port_engine", "") == "cylinder"

    def test_anchor_in_name(self):
        assert infer_shape("anchor", "") == "cone"

    def test_rope_in_description(self):
        assert infer_shape("", "a rope") == "cylinder"

    def test_unknown_returns_box(self):
        assert infer_shape("unknown_thing", "mystery") == "box"


# ============================================================================
# EDGE CASES: Size inference
# ============================================================================

class TestSizeInference:
    def test_default_is_medium(self):
        assert infer_size("", "") == 1.0

    def test_tiny(self):
        assert infer_size("tiny_thing", "") == 0.25

    def test_huge(self):
        assert infer_size("", "it's huge") == 2.5

    def test_massive(self):
        assert infer_size("", "massive object") == 3.0


# ============================================================================
# EDGE CASES: Multi-file parsing
# ============================================================================

class TestMultiFileParsing:
    def test_only_objects_no_rooms(self):
        content = "Object: test_obj\nType: prop\nShape: box"
        rooms, objects = parse_mud_file(content)
        assert len(rooms) == 0
        assert "test_obj" in objects
        assert objects["test_obj"].shape == "box"

    def test_multiple_rooms_consecutive_blanks(self):
        content = (
            "Room: a\nDescription: Test\n\n\n\n"
            "Room: b\nDescription: Test2"
        )
        rooms, objects = parse_mud_file(content)
        assert len(rooms) == 2

    def test_room_followed_by_object(self):
        content = (
            "Room: test_room\nDescription: A room.\n\n"
            "Object: test_obj\nType: prop\nShape: sphere"
        )
        rooms, objects = parse_mud_file(content)
        assert len(rooms) == 1
        assert len(objects) == 1
        assert rooms[0].name == "test_room"
        assert "test_obj" in objects

    def test_object_followed_by_room(self):
        content = (
            "Object: first_obj\nType: prop\nShape: box\n\n"
            "Room: test_room\nDescription: A room."
        )
        rooms, objects = parse_mud_file(content)
        assert len(rooms) == 1
        assert len(objects) == 1

    def test_orphan_lines_attached_to_room(self):
        """Lines without a directive prefix get appended to current section."""
        content = "Room: test\nDescription: Test\nSome orphan line\n"
        rooms, objects = parse_mud_file(content)
        assert len(rooms) == 1


# ============================================================================
# EDGE CASES: Description parsing
# ============================================================================

class TestDescriptionParsing:
    def test_description_with_colons(self):
        room = parse_mud_room(
            "Room: test\nDescription: The room: has colons: in it."
        )
        assert "has colons" in room.description

    def test_multi_line_description_collects_all(self):
        room = parse_mud_room(
            "Room: test\nDescription: First line.\n"
            "Second line.\nThird line.\nExits: north -> room1"
        )
        assert "First line." in room.description
        assert "Second line." in room.description
        assert "Third line." in room.description

    def test_multi_line_description_stops_at_exits(self):
        room = parse_mud_room(
            "Room: test\nDescription: First line.\n"
            "Second line.\nExits: north -> room1"
        )
        assert "Exits:" not in room.description
        assert "north" not in room.description


# ============================================================================
# EDGE CASES: Object definition parsing
# ============================================================================

class TestObjectDefParsing:
    def test_full_object_def(self):
        text = (
            "Object: anchor\nType: prop\nShape: cylinder\n"
            "Color: #445566\nSize: medium\nMaterial: iron\n"
            "Description: A rusted anchor.\nGlow: true\nEmissive: #ff0000"
        )
        obj = parse_object_def(text)
        assert obj.name == "anchor"
        assert obj.obj_type == "prop"
        assert obj.shape == "cylinder"
        assert obj.color == "#445566"
        assert obj.size == "medium"
        assert obj.material == "iron"
        assert obj.glow is True
        assert obj.emissive == "#ff0000"

    def test_object_glow_various_true_values(self):
        for val in ("true", "True", "yes", "YES", "1"):
            obj = parse_object_def(f"Object: test\nGlow: {val}")
            assert obj.glow is True, f"Glow: {val} should be True"

    def test_object_glow_false_values(self):
        for val in ("false", "no", "0", "", "maybe"):
            obj = parse_object_def(f"Object: test\nGlow: {val}")
            assert obj.glow is False, f"Glow: {val} should be False"

    def test_object_with_only_name(self):
        obj = parse_object_def("Object: lonely")
        assert obj.name == "lonely"
        assert obj.obj_type == "prop"
        assert obj.shape == "box"


# ============================================================================
# EDGE CASES: Compiled scene structure
# ============================================================================

class TestCompiledSceneStructure:
    def test_four_walls_always_generated(self):
        """Every room should have exactly 4 walls."""
        room = RoomDef(name="test", description="Test room")
        scene = compile_room(room, {})
        assert len(scene.walls) == 4

    def test_ceiling_always_present(self):
        room = RoomDef(name="test", description="Test room")
        scene = compile_room(room, {})
        assert scene.ceiling is not None

    def test_ambient_and_point_lights(self):
        room = RoomDef(name="test", description="Test room")
        scene = compile_room(room, {})
        # At least ambient + main point light
        assert len(scene.lights) >= 2

    def test_exit_lights_added(self):
        room = RoomDef(
            name="test", description="Test",
            exits={"north": "other", "south": "another"}
        )
        scene = compile_room(room, {})
        # ambient + main + 2 exit lights
        assert len(scene.lights) >= 4

    def test_objects_have_positions(self):
        room = RoomDef(
            name="test", description="Test",
            objects=["a", "b", "c"]
        )
        scene = compile_room(room, {})
        for obj in scene.objects:
            assert "position" in obj
            assert "x" in obj.position if hasattr(obj, 'position') else "x" in obj["position"]

    def test_unknown_theme_falls_back_to_default(self):
        room = RoomDef(name="mystery", description="???", theme="nonexistent")
        scene = compile_room(room, {})
        assert scene.theme["accent"] == "#ffd700"

    def test_description_based_theme_inference_engine(self):
        room = RoomDef(
            name="unknown", description="The engine throbs with diesel",
            theme="default"
        )
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        assert d["theme"]["accent"] == "#4488ff"

    def test_description_based_theme_inference_harbor(self):
        room = RoomDef(
            name="unknown", description="A busy harbor with docked vessels",
            theme="default"
        )
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        assert d["theme"]["accent"] == "#ffd700"

    def test_description_based_theme_inference_wheelhouse(self):
        room = RoomDef(
            name="unknown", description="The wheel and navigation bridge",
            theme="default"
        )
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        assert d["theme"]["accent"] == "#44ffff"

    def test_description_based_theme_inference_deck(self):
        room = RoomDef(
            name="unknown", description="The aft deck and stern area",
            theme="default"
        )
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        assert d["theme"]["accent"] == "#44ffaa"

    def test_all_room_themes_have_required_keys(self):
        for theme_name, theme_dict in ROOM_THEMES.items():
            assert "bg" in theme_dict
            assert "fg" in theme_dict
            assert "accent" in theme_dict
            assert "floor" in theme_dict
            assert "ambient" in theme_dict

    def test_all_size_scales_defined(self):
        for size_name, scale in SIZE_SCALE.items():
            assert isinstance(scale, float)
            assert scale > 0

    def test_compiled_scene_is_dataclass(self):
        room = RoomDef(name="test", description="Test")
        scene = compile_room(room, {})
        assert isinstance(scene, CompiledScene)


# ============================================================================
# EDGE CASES: Exit directions in compiled scene
# ============================================================================

class TestCompiledExits:
    def test_cardinal_directions_have_positions(self):
        room = RoomDef(
            name="test", description="Test",
            exits={"north": "n", "south": "s", "east": "e", "west": "w"}
        )
        scene = compile_room(room, {})
        scene_dict = compile_to_json(scene)
        assert len(scene_dict["exits"]) == 4
        for exit in scene_dict["exits"]:
            assert "position" in exit
            assert "x" in exit["position"]
            assert "z" in exit["position"]

    def test_boat_directions_have_positions(self):
        room = RoomDef(
            name="test", description="Test",
            exits={"port": "p", "starboard": "s", "forward": "f", "aft": "a"}
        )
        scene = compile_room(room, {})
        assert len(scene.exits) == 4

    def test_unknown_direction_has_default_position(self):
        room = RoomDef(
            name="test", description="Test",
            exits={"wormhole": "galaxy"}
        )
        scene = compile_room(room, {})
        scene_dict = compile_to_json(scene)
        assert len(scene_dict["exits"]) == 1
        assert scene_dict["exits"][0]["position"]["x"] == 0
        assert scene_dict["exits"][0]["position"]["z"] == 0

    def test_all_standard_exit_directions_valid(self):
        """Test every direction in the exit_positions/exit_angles dicts."""
        directions = [
            "north", "south", "east", "west",
            "northwest", "northeast", "southwest", "southeast",
            "up", "down",
            "forward", "fore", "ahead",
            "aft", "aftward", "astern", "backward", "back",
            "port", "portward",
            "starboard", "stbd",
            "forward_up", "fore_up",
            "forward_down", "fore_down",
            "aft_up", "aftward_up",
            "aft_down", "aftward_down",
            "in", "out", "below", "upward",
        ]
        for d in directions:
            room = RoomDef(
                name="test", description="Test",
                exits={d: "target"}
            )
            scene = compile_room(room, {})
            assert len(scene.exits) == 1, f"Direction '{d}' failed"


# ============================================================================
# EDGE CASES: JSON serialization
# ============================================================================

class TestJsonSerialization:
    def test_compiled_scene_json_has_no_circular_refs(self):
        import json
        room = RoomDef(
            name="test", description="Test",
            exits={"north": "other"},
            objects=["thing"],
            occupants=["agent"]
        )
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        json_str = json.dumps(d)  # Should not raise
        assert len(json_str) > 0

    def test_all_values_are_json_serializable(self):
        import json
        room = RoomDef(
            name="test", description="Test with metal walls.",
            exits={"north": "other"},
            objects=["engine", "tool"],
            occupants=["bot"]
        )
        objects = {
            "engine": ObjectDef(name="engine", shape="cylinder", size="huge", material="metal"),
            "tool": ObjectDef(name="tool", shape="box", size="small", material="steel", glow=True, emissive="#ff0000"),
        }
        scene = compile_room(room, objects)
        d = compile_to_json(scene)
        # Deep serialize every value
        json.dumps(d)  # If this doesn't raise, all values are serializable

    def test_pi_values_serialized_as_floats(self):
        """Verify math.pi values in rotation fields are JSON-safe."""
        import json
        room = RoomDef(name="test", description="Test")
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        # Floor rotation should have -pi/2
        assert d["floor"]["rotation"]["x"] == -1.5707963267948966
        json.dumps(d["floor"]["rotation"])
