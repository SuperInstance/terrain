"""
test_parser.py — Tests for MUD room parser.
"""

import pytest
from terrain_core import parse_mud_room, parse_mud_file, load_mud_file, RoomDef


# ============================================================================
# FIXTURES
# ============================================================================

FULL_ROOM = """Room: engine_room
Description: The engine room thrums with diesel power. Twin engines drive the stern drive.
Exits: north -> wheelhouse, down -> galley
Objects: port_engine, stbd_engine, tool_rack
Occupants: engineer_bot
Theme: engine_room
"""

MINIMAL_ROOM = """Room: storage_locker
Description: A small storage locker with bare walls.
"""

EMPTY_DESC_ROOM = """Room: empty_room
Description:
Exits:
Objects:
Occupants:
"""

MULTI_LINE_DESC = """Room: galley
Description: The galley is compact but efficient. A small propane stove sits beneath timber cabinets. The sink pumps seawater or fresh depending on the valve setting. Teak fiddled benches line the table where crew take meals.
Exits: up -> wheelhouse, aft -> aft_cockpit
Objects: propane_stove, sink_pump, galley_table
Occupants: none
"""

SINGLE_EXIT = """Room: foredeck
Description: The foredeck is the business end of the boat.
Exits: aft -> aft_cockpit
Objects: windlass, anchor_chain
Occupants: deckhand
"""

OBJECTS_COMMAS = """Room: wheelhouse
Description: The wheelhouse is the nerve center.
Exits: aft -> aft_cockpit
Objects: helm_wheel, radar_display, compass_rose, nav_charts, gpsReceiver
Occupants: captain
"""


# ============================================================================
# TESTS — parse_mud_room
# ============================================================================

class TestParseMudRoom:
    def test_parse_full_room(self):
        room = parse_mud_room(FULL_ROOM)
        assert room.name == "engine_room"
        assert "diesel" in room.description
        assert "north" in room.exits
        assert room.exits["north"] == "wheelhouse"
        assert "down" in room.exits
        assert room.exits["down"] == "galley"
        assert "port_engine" in room.objects
        assert "stbd_engine" in room.objects
        assert "tool_rack" in room.objects
        assert "engineer_bot" in room.occupants
        assert room.theme == "engine_room"

    def test_parse_minimal_room(self):
        room = parse_mud_room(MINIMAL_ROOM)
        assert room.name == "storage_locker"
        assert "storage locker" in room.description
        assert room.exits == {}
        assert room.objects == []
        assert room.occupants == []

    def test_parse_empty_description(self):
        room = parse_mud_room(EMPTY_DESC_ROOM)
        assert room.name == "empty_room"
        assert room.description == ""
        assert room.exits == {}
        assert room.objects == []
        assert room.occupants == []

    def test_parse_multi_line_description(self):
        room = parse_mud_room(MULTI_LINE_DESC)
        assert room.name == "galley"
        assert "propane stove" in room.description
        assert "seawater" in room.description
        assert "Teak fiddled benches" in room.description
        assert len(room.objects) == 3

    def test_parse_single_exit(self):
        room = parse_mud_room(SINGLE_EXIT)
        assert room.name == "foredeck"
        assert len(room.exits) == 1
        assert "aft" in room.exits
        assert room.exits["aft"] == "aft_cockpit"

    def test_parse_objects_comma_separated(self):
        room = parse_mud_room(OBJECTS_COMMAS)
        assert len(room.objects) == 5
        assert "helm_wheel" in room.objects
        assert "radar_display" in room.objects
        assert "compass_rose" in room.objects
        assert "nav_charts" in room.objects
        assert "gpsReceiver" in room.objects

    def test_parse_multiple_exits(self):
        room = parse_mud_room(FULL_ROOM)
        assert len(room.exits) == 2
        assert "north" in room.exits
        assert "down" in room.exits

    def test_parse_occupants(self):
        room = parse_mud_room(FULL_ROOM)
        assert "engineer_bot" in room.occupants
        # "none" literal is valid - means no agents (parsed as string "none")
        room2 = parse_mud_room(MULTI_LINE_DESC)
        assert "none" in room2.occupants

    def test_room_def_dataclass_fields(self):
        room = parse_mud_room(FULL_ROOM)
        assert isinstance(room, RoomDef)
        assert hasattr(room, 'name')
        assert hasattr(room, 'description')
        assert hasattr(room, 'exits')
        assert hasattr(room, 'objects')
        assert hasattr(room, 'occupants')
        assert hasattr(room, 'theme')


# ============================================================================
# TESTS — parse_mud_file
# ============================================================================

class TestParseMudFile:
    def test_parse_rooms_mud_returns_tuple(self):
        content = FULL_ROOM + "\n\n" + MINIMAL_ROOM
        rooms, objects = parse_mud_file(content)
        assert isinstance(rooms, list)
        assert isinstance(objects, dict)

    def test_parse_multiple_rooms_returns_list(self):
        content = FULL_ROOM + "\n\n" + MINIMAL_ROOM + "\n\n" + SINGLE_EXIT
        rooms, objects = parse_mud_file(content)
        assert len(rooms) == 3

    def test_parsed_rooms_have_names(self):
        content = FULL_ROOM + "\n\n" + MINIMAL_ROOM
        rooms, objects = parse_mud_file(content)
        names = [r.name for r in rooms]
        assert "engine_room" in names
        assert "storage_locker" in names

    def test_empty_content_returns_empty_lists(self):
        rooms, objects = parse_mud_file("")
        assert rooms == []
        assert objects == {}


# ============================================================================
# TESTS — load_mud_file (file I/O)
# ============================================================================

class TestLoadMudFile:
    def test_load_rooms_mud_five_rooms(self):
        rooms, objects = load_mud_file("/tmp/terrain/rooms.mud")
        assert len(rooms) == 5
        names = [r.name for r in rooms]
        assert "wheelhouse" in names
        assert "galley" in names
        assert "foredeck" in names
        assert "engine_room" in names
        assert "aft_cockpit" in names

    def test_load_rooms_has_exits(self):
        rooms, objects = load_mud_file("/tmp/terrain/rooms.mud")
        for room in rooms:
            assert isinstance(room.exits, dict)

    def test_load_rooms_has_objects(self):
        rooms, objects = load_mud_file("/tmp/terrain/rooms.mud")
        for room in rooms:
            assert isinstance(room.objects, list)

    def test_objects_dict_populated(self):
        rooms, objects = load_mud_file("/tmp/terrain/rooms.mud")
        assert len(objects) > 0
        assert "helm_wheel" in objects or any("helm" in k for k in objects)