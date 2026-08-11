"""
test_nautical_and_compilation.py — Tests for nautical direction system,
object compilation edge cases, and multi-room scene generation.

Covers gaps found during overnight audit:
- Nautical exit directions (port, starboard, fore, aft, etc.)
- Exit angles and positions for all direction types
- Object compilation with explicit ObjectDef vs inferred
- Glow/emissive material handling
- Multi-room file parsing with mixed rooms + objects
- CompiledScene dataclass field access
- TerrainCore API: load, list, compile, compile_all
- CLI/scene generation helpers
- Material inference edge cases (multiple keywords, empty string)
- Shape inference from nautical object names
"""

import pytest
import os
import sys
import json
import math

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from terrain_core import (
    parse_mud_room, parse_mud_file, parse_object_def, load_mud_file,
    compile_room, compile_to_json, generate_scene, generate_all_scenes,
    infer_material, infer_shape, infer_size,
    TerrainCore, RoomDef, ObjectDef, CompiledScene,
    MATERIAL_MAP, SHAPE_MAP, SIZE_SCALE, ROOM_THEMES,
    generate_all_scenes,
)


# ============================================================================
# NAUTICAL DIRECTIONS
# ============================================================================

class TestNauticalDirections:
    """Ships use port/starboard/fore/aft, not just cardinal directions."""

    NAUTICAL_ROOM = """Room: wheelhouse
Description: The nerve center of the vessel.
Exits: port -> galley, starboard -> side_deck, fore -> bow, aft -> cabin
Objects: none
Occupants: none
"""

    def test_nautical_exits_parsed(self):
        room = parse_mud_room(self.NAUTICAL_ROOM)
        assert "port" in room.exits
        assert "starboard" in room.exits
        assert "fore" in room.exits
        assert "aft" in room.exits

    def test_port_exit_has_correct_angle(self):
        room = parse_mud_room(self.NAUTICAL_ROOM)
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        port_exit = [e for e in d["exits"] if e["direction"] == "port"][0]
        assert port_exit["rotation"]["y"] == pytest.approx(math.pi / 2)

    def test_starboard_exit_has_correct_angle(self):
        room = parse_mud_room(self.NAUTICAL_ROOM)
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        stbd_exit = [e for e in d["exits"] if e["direction"] == "starboard"][0]
        assert stbd_exit["rotation"]["y"] == pytest.approx(-math.pi / 2)

    def test_fore_exit_position(self):
        room = parse_mud_room(self.NAUTICAL_ROOM)
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        fore_exit = [e for e in d["exits"] if e["direction"] == "fore"][0]
        # Fore should be at negative Z (forward in Three.js convention)
        assert fore_exit["position"]["z"] < 0

    def test_aft_exit_position(self):
        room = parse_mud_room(self.NAUTICAL_ROOM)
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        aft_exit = [e for e in d["exits"] if e["direction"] == "aft"][0]
        # Aft should be at positive Z
        assert aft_exit["position"]["z"] > 0

    def test_stbd_abbreviation(self):
        room = parse_mud_room("Room: test\nDescription: Test\nExits: stbd -> bow")
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        stbd = [e for e in d["exits"] if e["direction"] == "stbd"][0]
        assert stbd["rotation"]["y"] == pytest.approx(-math.pi / 2)

    def test_forward_aft_combinations(self):
        """forward_up, aft_down, etc. should compile."""
        room = parse_mud_room(
            "Room: test\nDescription: Test\n"
            "Exits: forward_up -> flybridge, aft_down -> hold"
        )
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        directions = [e["direction"] for e in d["exits"]]
        assert "forward_up" in directions
        assert "aft_down" in directions

    def test_all_nautical_exits_have_glow(self):
        """Exits should glow to be visible."""
        room = parse_mud_room(self.NAUTICAL_ROOM)
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        for exit in d["exits"]:
            assert exit["glow"] is True

    def test_all_nautical_exits_have_target(self):
        room = parse_mud_room(self.NAUTICAL_ROOM)
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        targets = {e["direction"]: e["target"] for e in d["exits"]}
        assert targets["port"] == "galley"
        assert targets["starboard"] == "side_deck"
        assert targets["fore"] == "bow"
        assert targets["aft"] == "cabin"


# ============================================================================
# OBJECT COMPILATION
# ============================================================================

class TestObjectCompilation:
    """Test object compilation with various ObjectDef configurations."""

    def test_object_with_explicit_glow(self):
        """Glow objects should have emissive material."""
        room = RoomDef(name="test", description="Test room", objects=["beacon"])
        obj = ObjectDef(name="beacon", shape="sphere", color="#ffff00", glow=True, emissive="#ff0000")
        scene = compile_room(room, {"beacon": obj})
        d = compile_to_json(scene)
        beacon = d["objects"][0]
        assert beacon["material"].get("emissive") == "#ff0000"
        assert beacon["material"].get("emissiveIntensity") == 1.0

    def test_object_without_glow_has_no_emissive(self):
        room = RoomDef(name="test", description="Test room", objects=["crate"])
        obj = ObjectDef(name="crate", shape="box", color="#8b4513", glow=False)
        scene = compile_room(room, {"crate": obj})
        d = compile_to_json(scene)
        crate = d["objects"][0]
        assert "emissive" not in crate["material"] or crate["material"].get("emissive") == "#000000"

    def test_object_size_scales(self):
        """Size mapping should affect scale."""
        room = RoomDef(name="test", description="Test", objects=["big", "small"])
        big = ObjectDef(name="big", size="huge")
        small = ObjectDef(name="small", size="tiny")
        scene = compile_room(room, {"big": big, "small": small})
        d = compile_to_json(scene)
        sizes = {o["name"]: o for o in d["objects"]}
        assert sizes["big"]["scale"]["x"] == SIZE_SCALE["huge"]
        assert sizes["small"]["scale"]["x"] == SIZE_SCALE["tiny"]

    def test_object_material_inference_from_description(self):
        """When material is 'default', infer from description.
        
        Note: MATERIAL_MAP iterates in insertion order. 'steel' (idx 1) 
        comes before 'rusty' (idx 5), so 'A rusty steel pipe' matches 
        'steel' first. This is first-match-wins behavior.
        """
        room = RoomDef(name="test", description="Test", objects=["pipe"])
        obj = ObjectDef(name="pipe", material="default", description="A rusty steel pipe")
        scene = compile_room(room, {"pipe": obj})
        d = compile_to_json(scene)
        pipe = d["objects"][0]
        # First match in MATERIAL_MAP iteration: 'steel' beats 'rusty'
        # But note: obj_def.color (#888888) overrides the material color via {**material, "color": color}
        # So we check metalness/roughness from steel, not color
        assert pipe["material"]["metalness"] == MATERIAL_MAP["steel"]["metalness"]
        assert pipe["material"]["roughness"] == MATERIAL_MAP["steel"]["roughness"]

    def test_object_explicit_material_overrides_inference(self):
        """When material is explicitly set, use it directly.
        
        Note: compile_room does {**material, "color": color} where color
        is obj_def.color (default #888888). So material properties
        (metalness/roughness) come from inference, but color is overridden
        by the ObjectDef.color field.
        """
        room = RoomDef(name="test", description="Test", objects=["pillar"])
        obj = ObjectDef(name="pillar", material="brass", description="A wooden pillar")
        scene = compile_room(room, {"pillar": obj})
        d = compile_to_json(scene)
        pillar = d["objects"][0]
        # metalness/roughness from brass inference
        assert pillar["material"]["metalness"] == MATERIAL_MAP["brass"]["metalness"]
        assert pillar["material"]["roughness"] == MATERIAL_MAP["brass"]["roughness"]
        # Color comes from obj_def.color (default), not material
        assert pillar["material"]["color"] == "#888888"

    def test_object_description_passed_to_scene(self):
        """ObjectDef descriptions should appear in scene output."""
        room = RoomDef(name="test", description="Test", objects=["wheel"])
        obj = ObjectDef(name="wheel", description="The ship's wheel, worn smooth by years of use")
        scene = compile_room(room, {"wheel": obj})
        d = compile_to_json(scene)
        wheel = d["objects"][0]
        assert "ship's wheel" in wheel["description"]

    def test_inferred_object_description_is_empty(self):
        """Objects without explicit definitions should have empty descriptions."""
        room = RoomDef(name="test", description="Test", objects=["mystery_obj"])
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        obj = d["objects"][0]
        assert obj["description"] == ""

    def test_multiple_objects_dont_overlap_positions(self):
        """Objects should be distributed in a grid, not stacked."""
        room = RoomDef(name="test", description="Test",
                       objects=["a", "b", "c", "d", "e", "f"])
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        positions = [(o["position"]["x"], o["position"]["z"]) for o in d["objects"]]
        # No two objects should share the same position
        assert len(set(positions)) == len(positions)


# ============================================================================
# MATERIAL INFERENCE EDGE CASES
# ============================================================================

class TestMaterialInference:
    def test_empty_string_returns_default(self):
        mat = infer_material("")
        assert mat["color"] == "#888888"

    def test_multiple_keywords_picks_first_match(self):
        """When multiple material keywords appear, the first in MATERIAL_MAP wins."""
        desc = "steel and wood mixed together"
        mat = infer_material(desc)
        # "steel" comes before "wood" in MATERIAL_MAP iteration order (dict preserves insertion)
        # Actually, MATERIAL_MAP is iterated in insertion order. Let's check which comes first.
        keys = list(MATERIAL_MAP.keys())
        steel_idx = keys.index("steel")
        wood_idx = keys.index("wood")
        expected_key = keys[min(steel_idx, wood_idx)]
        assert mat["color"] == MATERIAL_MAP[expected_key]["color"]

    def test_case_insensitive_matching(self):
        mat = infer_material("SHINY STEEL SURFACE")
        assert mat["metalness"] == 0.95  # steel properties

    def test_unknown_material_returns_default(self):
        mat = infer_material("a strange alien substance")
        assert mat["color"] == "#888888"

    def test_all_material_keywords_recognized(self):
        """Every keyword in MATERIAL_MAP should be detected."""
        for keyword, props in MATERIAL_MAP.items():
            mat = infer_material(f"made of {keyword}")
            assert mat["color"] == props["color"], f"Failed for keyword: {keyword}"


# ============================================================================
# SHAPE INFERENCE
# ============================================================================

class TestShapeInference:
    def test_engine_infers_cylinder(self):
        assert infer_shape("port_engine", "The main engine") == "cylinder"

    def test_fuel_infers_cylinder(self):
        assert infer_shape("fuel_tank", "Fuel storage") == "cylinder"

    def test_anchor_infers_cone(self):
        assert infer_shape("anchor", "Ship's anchor") == "cone"

    def test_rope_infers_cylinder(self):
        assert infer_shape("mooring_rope", "Thick rope") == "cylinder"

    def test_pipe_infers_cylinder(self):
        assert infer_shape("coolant_pipe", "Coolant pipe") == "cylinder"

    def test_unknown_returns_box(self):
        assert infer_shape("mystery_thing", "Something unknown") == "box"

    def test_shape_from_description_not_name(self):
        """Shape inference should also check description."""
        assert infer_shape("artifact", "It's a perfect sphere") == "sphere"

    def test_shape_from_description_torus(self):
        assert infer_shape("ring", "A torus-shaped object") == "torus"


# ============================================================================
# SIZE INFERENCE
# ============================================================================

class TestSizeInference:
    def test_tiny_keyword(self):
        assert infer_size("bolt", "a tiny bolt") == 0.25

    def test_small_keyword(self):
        assert infer_size("valve", "small valve") == 0.5

    def test_large_keyword(self):
        assert infer_size("tank", "large tank") == 1.5

    def test_huge_keyword(self):
        assert infer_size("engine", "huge engine") == 2.5

    def test_massive_keyword(self):
        assert infer_size("hull", "massive hull section") == 3.0

    def test_default_medium(self):
        assert infer_size("box", "ordinary box") == 1.0


# ============================================================================
# MULTI-ROOM FILE PARSING
# ============================================================================

class TestMultiRoomParsing:
    MULTI_ROOM = """
Room: engine_room
Description: The engine room thrums with power.
Exits: north -> wheelhouse
Objects: engine, tools
Occupants: engineer
Theme: engine_room

Object: engine
Type: prop
Shape: cylinder
Color: #445566
Size: large
Material: metal
Description: The main diesel engine.

Object: tools
Type: prop
Shape: box
Color: #8b4513
Size: small
Description: A toolbox.

Room: wheelhouse
Description: The bridge.
Exits: south -> engine_room
Objects: helm
Occupants: captain
Theme: wheelhouse
"""

    def test_parses_two_rooms(self):
        rooms, objects = parse_mud_file(self.MULTI_ROOM)
        assert len(rooms) == 2

    def test_parses_two_objects(self):
        rooms, objects = parse_mud_file(self.MULTI_ROOM)
        assert len(objects) == 2
        assert "engine" in objects
        assert "tools" in objects

    def test_room_names_correct(self):
        rooms, _ = parse_mud_file(self.MULTI_ROOM)
        names = [r.name for r in rooms]
        assert "engine_room" in names
        assert "wheelhouse" in names

    def test_object_definitions_intact(self):
        _, objects = parse_mud_file(self.MULTI_ROOM)
        assert objects["engine"].shape == "cylinder"
        assert objects["engine"].size == "large"
        assert objects["tools"].shape == "box"

    def test_generate_all_scenes_produces_both(self):
        rooms, objects = parse_mud_file(self.MULTI_ROOM)
        scenes = generate_all_scenes(rooms, objects)
        assert "engine_room" in scenes
        assert "wheelhouse" in scenes
        assert scenes["engine_room"]["room"] == "engine_room"


# ============================================================================
# TERRAIN CORE API
# ============================================================================

class TestTerrainCoreAPI:
    def test_empty_core_has_no_rooms(self):
        tc = TerrainCore()
        assert tc.list_rooms() == []

    def test_empty_compile_all_returns_empty(self):
        tc = TerrainCore()
        assert tc.compile_all() == {}

    def test_compile_nonexistent_returns_none(self):
        tc = TerrainCore()
        assert tc.compile("nonexistent") is None

    def test_get_room_nonexistent_returns_none(self):
        tc = TerrainCore()
        assert tc.get_room("phantom") is None

    def test_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            TerrainCore("/nonexistent/path.mud")

    def test_core_with_temp_file(self, tmp_path):
        mud_file = tmp_path / "test.mud"
        mud_file.write_text(
            "Room: galley\nDescription: The galley.\n"
            "Exits: north -> bridge\nObjects: none\nOccupants: none\n"
        )
        tc = TerrainCore(str(mud_file))
        assert "galley" in tc.list_rooms()
        scene = tc.compile("galley")
        assert scene is not None
        assert scene["room"] == "galley"


# ============================================================================
# COMPILED SCENE STRUCTURE
# ============================================================================

class TestCompiledSceneStructure:
    def test_compiled_scene_is_dataclass(self):
        room = RoomDef(name="test", description="Test")
        scene = compile_room(room, {})
        assert isinstance(scene, CompiledScene)
        assert hasattr(scene, "floor")
        assert hasattr(scene, "walls")
        assert hasattr(scene, "ceiling")
        assert hasattr(scene, "lights")
        assert hasattr(scene, "camera")

    def test_four_walls_always_generated(self):
        room = RoomDef(name="test", description="Test")
        scene = compile_room(room, {})
        assert len(scene.walls) == 4

    def test_ceiling_always_present(self):
        room = RoomDef(name="test", description="Test")
        scene = compile_room(room, {})
        assert scene.ceiling is not None

    def test_camera_has_fov(self):
        room = RoomDef(name="test", description="Test")
        scene = compile_room(room, {})
        assert "fov" in scene.camera

    def test_lights_include_ambient_and_point(self):
        room = RoomDef(name="test", description="Test")
        scene = compile_room(room, {})
        light_types = [l["type"] for l in scene.lights]
        assert "ambient" in light_types
        assert "point" in light_types

    def test_exit_lights_added(self):
        """Each exit should add a point light."""
        room = RoomDef(
            name="test", description="Test",
            exits={"north": "hallway", "south": "lobby"}
        )
        scene = compile_room(room, {})
        # 2 ambient+main + 2 exit lights = 4 total
        assert len(scene.lights) >= 4

    def test_to_json_is_serializable(self):
        room = RoomDef(name="test", description="Test", objects=["box"])
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        # Should not raise
        json.dumps(d)


# ============================================================================
# THEME DETECTION
# ============================================================================

class TestThemeDetection:
    def test_engine_theme_from_description(self):
        """Room with engine keywords in description should get engine_room theme."""
        room = RoomDef(name="test", description="The diesel engine room throbs", theme="default")
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        # Engine room theme has blue accent
        assert d["theme"]["accent"] == ROOM_THEMES["engine_room"]["accent"]

    def test_harbor_theme_from_description(self):
        room = RoomDef(name="test", description="The harbor dock bustles with vessels", theme="default")
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        assert d["theme"]["accent"] == ROOM_THEMES["harbor"]["accent"]

    def test_wheelhouse_theme_from_description(self):
        room = RoomDef(name="test", description="The navigation bridge helm", theme="default")
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        assert d["theme"]["accent"] == ROOM_THEMES["wheelhouse"]["accent"]

    def test_explicit_theme_overrides_inference(self):
        room = RoomDef(name="test", description="The diesel engine throbs", theme="dojo")
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        assert d["theme"]["accent"] == ROOM_THEMES["dojo"]["accent"]

    def test_unknown_theme_falls_to_default(self):
        room = RoomDef(name="test", description="A void", theme="alien_ship")
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        assert d["theme"]["accent"] == ROOM_THEMES["default"]["accent"]

    def test_theme_name_prefix_bug_documented(self):
        """DOCUMENTED BUG: Room name prefix theme lookup is unreachable.
        
        compile_room line: theme_key = room.theme if room.theme in ROOM_THEMES
        else room.name.split('_')[0]
        
        When theme='default', 'default' IS in ROOM_THEMES, so theme_key
        = 'default'. The else branch (name prefix lookup) never fires.
        
        Room 'forge_main' with theme='default' gets default theme, not forge.
        This test documents the bug so it's visible if someone fixes it.
        """
        room = RoomDef(name="forge_main", description="A generic room", theme="default")
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        # BUG: should be forge accent but gets default because the name-prefix
        # lookup is unreachable when theme='default'
        assert d["theme"]["accent"] == ROOM_THEMES["default"]["accent"]
        
        # If this test starts failing, someone fixed the bug. Update accordingly.
        # The fix would be: check name prefix BEFORE checking if theme is in ROOM_THEMES,
        # or add a separate name_prefix check when theme == 'default'.


# ============================================================================
# AGENT POSITIONING
# ============================================================================

class TestAgentPositioning:
    def test_multiple_agents_distributed(self):
        room = RoomDef(name="test", description="Test",
                       occupants=["a", "b", "c", "d", "e"])
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        positions = [(a["position"]["x"], a["position"]["z"]) for a in d["agents"]]
        assert len(set(positions)) == len(positions)

    def test_agent_has_gold_color(self):
        room = RoomDef(name="test", description="Test", occupants=["bot"])
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        assert d["agents"][0]["color"] == "#ffd700"

    def test_agent_scale_is_humanoid(self):
        """Agents should have humanoid-ish proportions."""
        room = RoomDef(name="test", description="Test", occupants=["bot"])
        scene = compile_room(room, {})
        d = compile_to_json(scene)
        agent = d["agents"][0]
        assert agent["scale"]["y"] > agent["scale"]["x"]  # taller than wide
