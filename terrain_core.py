#!/usr/bin/env python3
"""
terrain_core.py — MUD-to-Three.js scene compiler.

Parses MUD room definitions (text format) and compiles them into
Three.js scene JSON. The output drives the 3D web renderer.

MUD room text format:
    Room: engine_room
    Description: The engine room throbs with heat. Twin diesels rumble.
    Exits: north -> wheelhouse, up -> aft_deck
    Objects: port_engine, stbd_engine, tool_rack, fuel_lines
    Occupants: none

Objects reference defined prototypes:
    Object: anchor
    Type: prop
    Shape: cylinder
    Color: #445566
    Size: medium
    Description: A rusted anchor, salt-worn and listing to port.

The compiler maps descriptions to 3D materials:
- "metal", "steel", "iron" → metallic PBR
- "wood", "plank", "teak" → wood texture
- "water", "wet", "pool" → reflective surface
- "stone", "rock", "concrete" → rough stone
- "glow", "neon", "light" → emissive materials
"""

import json, re, os, math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ObjectDef:
    name: str
    obj_type: str = "prop"
    shape: str = "box"
    color: str = "#888888"
    size: str = "medium"
    material: str = "default"
    description: str = ""
    position: Tuple[float, float, float] = (0, 0, 0)
    glow: bool = False
    emissive: str = "#000000"

@dataclass
class RoomDef:
    name: str
    description: str
    exits: Dict[str, str] = field(default_factory=dict)
    objects: List[str] = field(default_factory=list)
    occupants: List[str] = field(default_factory=list)
    theme: str = "default"
    ambient_light: str = "#404060"
    floor_material: str = "stone"
    wall_material: str = "stone"

@dataclass
class CompiledScene:
    """Three.js-ready scene JSON structure."""
    room: str
    description: str
    theme: Dict[str, str]
    floor: Dict
    walls: List[Dict]
    ceiling: Optional[Dict]
    objects: List[Dict]
    agents: List[Dict]
    exits: List[Dict]
    lights: List[Dict]
    camera: Dict

# ============================================================================
# MATERIAL MAPPING
# ============================================================================

# Maps description keywords to Three.js PBR material properties
MATERIAL_MAP = {
    # Metals
    "metal":      {"color": "#8899aa", "metalness": 0.9, "roughness": 0.2},
    "steel":      {"color": "#99aabb", "metalness": 0.95, "roughness": 0.15},
    "iron":       {"color": "#556677", "metalness": 0.85, "roughness": 0.3},
    "copper":     {"color": "#b87333", "metalness": 0.8, "roughness": 0.25},
    "brass":      {"color": "#c9a227", "metalness": 0.85, "roughness": 0.2},
    "rusty":      {"color": "#8b4513", "metalness": 0.6, "roughness": 0.7},
    # Woods
    "wood":       {"color": "#8b6914", "metalness": 0.0, "roughness": 0.8},
    "teak":       {"color": "#6b4423", "metalness": 0.0, "roughness": 0.7},
    "plank":      {"color": "#a0784a", "metalness": 0.0, "roughness": 0.75},
    "deck":       {"color": "#7a5c3a", "metalness": 0.0, "roughness": 0.85},
    # Liquids / wet
    "water":      {"color": "#1a3a5a", "metalness": 0.1, "roughness": 0.1, "opacity": 0.7},
    "wet":        {"color": "#3a5a7a", "metalness": 0.2, "roughness": 0.15},
    "pool":       {"color": "#1a4a6a", "metalness": 0.1, "roughness": 0.1},
    # Stone / concrete
    "stone":      {"color": "#6a6a6a", "metalness": 0.0, "roughness": 0.9},
    "rock":       {"color": "#5a5a5a", "metalness": 0.0, "roughness": 0.95},
    "concrete":   {"color": "#7a7a7a", "metalness": 0.0, "roughness": 0.85},
    "brick":      {"color": "#8a4a3a", "metalness": 0.0, "roughness": 0.9},
    # Emissive / glow
    "glow":       {"color": "#ffff88", "emissive": "#ffff44", "emissiveIntensity": 1.0},
    "neon":       {"color": "#ff44ff", "emissive": "#ff00ff", "emissiveIntensity": 1.5},
    "light":      {"color": "#ffffcc", "emissive": "#ffffaa", "emissiveIntensity": 1.0},
    "ember":      {"color": "#ff6622", "emissive": "#ff4400", "emissiveIntensity": 0.8},
    # Fabrics / soft
    "fabric":     {"color": "#8888aa", "metalness": 0.0, "roughness": 0.95},
    "canvas":     {"color": "#c8b8a8", "metalness": 0.0, "roughness": 0.9},
    "rope":       {"color": "#b8a888", "metalness": 0.0, "roughness": 0.85},
}

# Shape prototypes (Three.js geometry names)
SHAPE_MAP = {
    "box": "BoxGeometry",
    "cylinder": "CylinderGeometry",
    "sphere": "SphereGeometry",
    "cone": "ConeGeometry",
    "torus": "TorusGeometry",
    "plane": "PlaneGeometry",
    "prop": "BoxGeometry",
    "engine": "CylinderGeometry",
    "tool": "BoxGeometry",
    "fuel": "CylinderGeometry",
}

# Size to scale mapping
SIZE_SCALE = {
    "tiny": 0.25,
    "small": 0.5,
    "medium": 1.0,
    "large": 1.5,
    "huge": 2.5,
}

# Theme definitions for room types
ROOM_THEMES = {
    "harbor":     {"bg": "#1a2a3a", "fg": "#2a4a6a", "accent": "#ffd700", "floor": "deck", "ambient": "#203040"},
    "forge":      {"bg": "#2a1a0a", "fg": "#4a2a0a", "accent": "#ff6644", "floor": "stone", "ambient": "#301510"},
    "dojo":       {"bg": "#1a1a2a", "fg": "#2a2a4a", "accent": "#44ff88", "floor": "wood", "ambient": "#151530"},
    "engine_room":{"bg": "#1a1a1a", "fg": "#2a2a2a", "accent": "#4488ff", "floor": "metal", "ambient": "#252525"},
    "wheelhouse": {"bg": "#0a1a2a", "fg": "#1a3a4a", "accent": "#44ffff", "floor": "wood", "ambient": "#102030"},
    "aft_deck":   {"bg": "#0a2a3a", "fg": "#1a4a5a", "accent": "#44ffaa", "floor": "deck", "ambient": "#153040"},
    "tide-pool":  {"bg": "#0a1a2a", "fg": "#1a3a5a", "accent": "#44ffaa", "floor": "stone", "ambient": "#0a2030"},
    "archives":   {"bg": "#1a1a1a", "fg": "#2a2a2a", "accent": "#44aaff", "floor": "stone", "ambient": "#151520"},
    "arena":      {"bg": "#2a0a0a", "fg": "#4a1a1a", "accent": "#ff4444", "floor": "stone", "ambient": "#301010"},
    "default":    {"bg": "#0a0a1a", "fg": "#1a1a3a", "accent": "#ffd700", "floor": "stone", "ambient": "#101020"},
}

# ============================================================================
# PARSER
# ============================================================================

def parse_mud_room(text: str) -> RoomDef:
    """Parse a MUD room text block into a RoomDef.
    
    Supported format:
        Room: name
        Description: text (can span multiple lines until blank line)
        Exits: north -> room1, south -> room2
        Objects: obj1, obj2, obj3
        Occupants: agent1, agent2
        Theme: harbor
    """
    room = RoomDef(name="unknown", description="")
    
    lines = text.strip().split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith("Room:"):
            room.name = line.split(":", 1)[1].strip()
            
        elif line.startswith("Description:"):
            # Collect multi-line description until blank line or new directive
            desc_lines = [line.split(":", 1)[1].strip()]
            i += 1
            while i < len(lines) and lines[i].strip() and not any(lines[i].strip().startswith(p) for p in ["Exits:", "Objects:", "Occupants:", "Theme:", "Object:"]):
                desc_lines.append(lines[i].strip())
                i += 1
            room.description = " ".join(desc_lines)
            continue  # Don't increment i at end
            
        elif line.startswith("Exits:"):
            exits_str = line.split(":", 1)[1].strip()
            for part in exits_str.split(","):
                part = part.strip()
                if "->" in part:
                    direction, target = part.split("->", 1)
                    room.exits[direction.strip()] = target.strip()
                    
        elif line.startswith("Objects:"):
            objs_str = line.split(":", 1)[1].strip()
            if objs_str.lower() == "none":
                room.objects = []
            else:
                room.objects = [o.strip() for o in objs_str.split(",") if o.strip()]
            
        elif line.startswith("Occupants:"):
            occ_str = line.split(":", 1)[1].strip()
            if occ_str.lower() == "none":
                room.occupants = []
            else:
                room.occupants = [o.strip() for o in occ_str.split(",") if o.strip()]
            
        elif line.startswith("Theme:"):
            room.theme = line.split(":", 1)[1].strip()
            
        elif line.startswith("Floor:"):
            room.floor_material = line.split(":", 1)[1].strip()
            
        elif line.startswith("Ambient:"):
            room.ambient_light = line.split(":", 1)[1].strip()
            
        i += 1
    
    return room

def parse_object_def(text: str) -> ObjectDef:
    """Parse an Object definition block."""
    obj = ObjectDef(name="unknown")
    
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith("Object:"):
            obj.name = line.split(":", 1)[1].strip()
        elif line.startswith("Type:"):
            obj.obj_type = line.split(":", 1)[1].strip()
        elif line.startswith("Shape:"):
            obj.shape = line.split(":", 1)[1].strip()
        elif line.startswith("Color:"):
            obj.color = line.split(":", 1)[1].strip()
        elif line.startswith("Size:"):
            obj.size = line.split(":", 1)[1].strip()
        elif line.startswith("Material:"):
            obj.material = line.split(":", 1)[1].strip()
        elif line.startswith("Description:"):
            obj.description = line.split(":", 1)[1].strip()
        elif line.startswith("Glow:"):
            obj.glow = line.split(":", 1)[1].strip().lower() in ("true", "yes", "1")
        elif line.startswith("Emissive:"):
            obj.emissive = line.split(":", 1)[1].strip()
            
    return obj

def parse_mud_file(content: str) -> Tuple[List[RoomDef], Dict[str, ObjectDef]]:
    """Parse a complete MUD file with rooms and objects.
    
    Returns (rooms, object_definitions).
    """
    rooms = []
    objects = {}
    current_section = ""
    current_text = []
    
    for line in content.split('\n'):
        if line.strip() == "":
            # Empty line might end a section
            if current_section and current_text:
                if current_section.startswith("Object:"):
                    obj = parse_object_def("\n".join(current_text))
                    objects[obj.name] = obj
                elif current_section == "room":
                    room = parse_mud_room("\n".join(current_text))
                    rooms.append(room)
                current_text = []
            current_section = ""
            continue
            
        if line.startswith("Room:"):
            # Flush previous section
            if current_section.startswith("Object:"):
                obj = parse_object_def("\n".join(current_text))
                objects[obj.name] = obj
            elif current_section == "room" and current_text:
                room = parse_mud_room("\n".join(current_text))
                rooms.append(room)
            
            current_section = "room"
            current_text = [line]
            
        elif line.startswith("Object:"):
            # Flush previous room section
            if current_section == "room" and current_text:
                room = parse_mud_room("\n".join(current_text))
                rooms.append(room)
            
            current_section = line
            current_text = [line]
            
        else:
            current_text.append(line)
    
    # Flush last sections
    if current_section.startswith("Object:"):
        obj = parse_object_def("\n".join(current_text))
        objects[obj.name] = obj
    elif current_section == "room" and current_text:
        room = parse_mud_room("\n".join(current_text))
        rooms.append(room)
    
    return rooms, objects

def load_mud_file(path: str) -> Tuple[List[RoomDef], Dict[str, ObjectDef]]:
    """Load and parse a MUD room file."""
    with open(path, 'r') as f:
        return parse_mud_file(f.read())

# ============================================================================
# MATERIAL INFERENCE
# ============================================================================

def infer_material(description: str) -> Dict:
    """Infer material properties from room/object description.
    
    Scans description for keywords and returns Three.js material params.
    """
    desc_lower = description.lower()
    
    # Start with default
    material = {"color": "#888888", "metalness": 0.0, "roughness": 0.5}
    
    for keyword, props in MATERIAL_MAP.items():
        if keyword in desc_lower:
            material = props.copy()
            break
    
    return material

def infer_shape(name: str, description: str) -> str:
    """Infer shape from name and description."""
    combined = f"{name} {description}".lower()
    
    # Check name first
    if "engine" in name.lower():
        return "cylinder"
    if "fuel" in name.lower():
        return "cylinder"
    if "anchor" in name.lower():
        return "cone"
    if "tool" in name.lower():
        return "box"
    if "rack" in name.lower():
        return "box"
    if "rope" in name.lower():
        return "cylinder"
    if "pipe" in name.lower():
        return "cylinder"
    if "tank" in name.lower():
        return "cylinder"
    if "winch" in name.lower():
        return "cylinder"
    if "boom" in name.lower():
        return "cylinder"
    if "mast" in name.lower():
        return "cylinder"
    
    # Check description
    for keyword, shape in [
        ("engine", "cylinder"),
        ("cylinder", "cylinder"),
        ("sphere", "sphere"),
        ("round", "sphere"),
        ("cone", "cone"),
        ("torus", "torus"),
        ("rope", "cylinder"),
        ("pipe", "cylinder"),
    ]:
        if keyword in combined:
            return shape
    
    return "box"

def infer_size(name: str, description: str) -> float:
    """Infer scale from name and description."""
    combined = f"{name} {description}".lower()
    
    for keyword, scale in [
        ("tiny", 0.25), ("small", 0.5),
        ("large", 1.5), ("huge", 2.5),
        ("massive", 3.0),
    ]:
        if keyword in combined:
            return scale
    
    # Default medium
    return 1.0

# ============================================================================
# SCENE COMPILATION
# ============================================================================

def compile_room(room: RoomDef, objects: Dict[str, ObjectDef] = None) -> CompiledScene:
    """Compile a RoomDef into a Three.js-ready scene JSON."""
    objects = objects or {}
    
    # Get theme
    theme_key = room.theme if room.theme in ROOM_THEMES else room.name.split("_")[0]
    theme = ROOM_THEMES.get(theme_key, ROOM_THEMES["default"]).copy()
    
    # Infer theme from description if not explicitly set
    if room.theme == "default":
        desc_lower = room.description.lower()
        if any(k in desc_lower for k in ["engine", "motor", "diesel"]):
            theme = ROOM_THEMES["engine_room"].copy()
        elif any(k in desc_lower for k in ["harbor", "dock", "vessel", "boat"]):
            theme = ROOM_THEMES["harbor"].copy()
        elif any(k in desc_lower for k in ["wheel", "navig", "bridge", "helm"]):
            theme = ROOM_THEMES["wheelhouse"].copy()
        elif any(k in desc_lower for k in ["deck", "aft", "stern"]):
            theme = ROOM_THEMES["aft_deck"].copy()
    
    # Room dimensions (width, height, depth)
    room_width = 20
    room_height = 8
    room_depth = 20
    
    # Build floor
    floor_mat = infer_material(room.floor_material)
    floor = {
        "type": "mesh",
        "geometry": {"type": "PlaneGeometry", "width": room_width, "height": room_depth},
        "material": {**floor_mat, "side": 2},
        "position": {"x": 0, "y": 0, "z": 0},
        "rotation": {"x": -math.pi / 2, "y": 0, "z": 0},
        "receiveShadow": True
    }
    
    # Build walls (4 walls, slight height offset)
    walls = []
    wall_configs = [
        {"id": "north", "pos": [0, room_height/2, -room_depth/2], "rot": [0, 0, 0], "w": room_width, "h": room_height},
        {"id": "south", "pos": [0, room_height/2, room_depth/2], "rot": [0, math.pi, 0], "w": room_width, "h": room_height},
        {"id": "east", "pos": [room_width/2, room_height/2, 0], "rot": [0, -math.pi/2, 0], "w": room_depth, "h": room_height},
        {"id": "west", "pos": [-room_width/2, room_height/2, 0], "rot": [0, math.pi/2, 0], "w": room_depth, "h": room_height},
    ]
    
    wall_mat = infer_material(room.wall_material)
    for wc in wall_configs:
        walls.append({
            "type": "mesh",
            "geometry": {"type": "PlaneGeometry", "width": wc["w"], "height": wc["h"]},
            "material": {**wall_mat, "side": 0},
            "position": {"x": wc["pos"][0], "y": wc["pos"][1], "z": wc["pos"][2]},
            "rotation": {"x": wc["rot"][0], "y": wc["rot"][1], "z": wc["rot"][2]},
        })
    
    # Build ceiling
    ceiling = {
        "type": "mesh",
        "geometry": {"type": "PlaneGeometry", "width": room_width, "height": room_depth},
        "material": {**wall_mat, "side": 1, "color": "#303040"},
        "position": {"x": 0, "y": room_height, "z": 0},
        "rotation": {"x": math.pi / 2, "y": 0, "z": 0},
    }
    
    # Build objects
    scene_objects = []
    for obj_name in room.objects:
        # Look up object definition
        if obj_name in objects:
            obj_def = objects[obj_name]
            shape = SHAPE_MAP.get(obj_def.shape, "BoxGeometry")
            color = obj_def.color
            material = infer_material(obj_def.material) if obj_def.material != "default" else infer_material(obj_def.description)
            if obj_def.glow:
                material["emissive"] = obj_def.emissive
                material["emissiveIntensity"] = 1.0
            scale = SIZE_SCALE.get(obj_def.size, 1.0)
        else:
            # Infer from name + description
            shape = SHAPE_MAP.get(infer_shape(obj_name, room.description), "BoxGeometry")
            color = "#8899aa"
            material = infer_material(room.description)
            scale = infer_size(obj_name, room.description)
        
        scene_objects.append({
            "type": "mesh",
            "name": obj_name,
            "description": obj_def.description if obj_name in objects else "",
            "geometry": {"type": shape},
            "material": {**material, "color": color},
            "scale": {"x": scale, "y": scale, "z": scale},
            "position": {
                "x": (len(scene_objects) % 5 - 2) * 3,
                "y": scale / 2,
                "z": (len(scene_objects) // 5) * 3 - 5
            },
        })
    
    # Build agents
    scene_agents = []
    for i, agent_name in enumerate(room.occupants):
        scene_agents.append({
            "type": "agent",
            "name": agent_name,
            "color": "#ffd700",
            "position": {
                "x": (i % 3 - 1) * 4,
                "y": 1.5,
                "z": (i // 3) * 3 - 3
            },
            "scale": {"x": 0.8, "y": 1.8, "z": 0.8},
        })
    
    # Build exits (walkable doorways to other rooms)
    scene_exits = []
    exit_angles = {
        # Cardinal
        "north": 0, "south": math.pi, "east": -math.pi/2, "west": math.pi/2,
        "northwest": math.pi/4, "northeast": -math.pi/4,
        "southwest": 3*math.pi/4, "southeast": -3*math.pi/4,
        "up": 0, "down": math.pi,
        # Boat directions
        "forward": 0, "fore": 0, "ahead": 0,
        "aft": math.pi, "aftward": math.pi, "astern": math.pi, "backward": math.pi, "back": math.pi,
        "port": math.pi/2, "portward": math.pi/2,
        "starboard": -math.pi/2, "stbd": -math.pi/2,
        "forward_up": 0, "fore_up": 0,
        "forward_down": 0, "fore_down": 0,
        "aft_up": math.pi, "aftward_up": math.pi,
        "aft_down": math.pi, "aftward_down": math.pi,
        "in": 0, "out": math.pi,
        "below": math.pi, "upward": 0,
    }

    exit_positions = {
        # Cardinal
        "north": [0, 2, -room_depth/2 + 1],
        "south": [0, 2, room_depth/2 - 1],
        "east": [room_width/2 - 1, 2, 0],
        "west": [-room_width/2 + 1, 2, 0],
        # Boat directions
        "forward": [0, 2, -room_depth/2 + 1],
        "fore": [0, 2, -room_depth/2 + 1],
        "ahead": [0, 2, -room_depth/2 + 1],
        "aft": [0, 2, room_depth/2 - 1],
        "aftward": [0, 2, room_depth/2 - 1],
        "astern": [0, 2, room_depth/2 - 1],
        "backward": [0, 2, room_depth/2 - 1],
        "back": [0, 2, room_depth/2 - 1],
        "port": [-room_width/2 + 1, 2, 0],
        "portward": [-room_width/2 + 1, 2, 0],
        "starboard": [room_width/2 - 1, 2, 0],
        "stbd": [room_width/2 - 1, 2, 0],
        "forward_up": [0, 2, -room_depth/2 + 1],
        "fore_up": [0, 2, -room_depth/2 + 1],
        "forward_down": [0, 2, -room_depth/2 + 1],
        "fore_down": [0, 2, -room_depth/2 + 1],
        "aft_up": [0, 2, room_depth/2 - 1],
        "aftward_up": [0, 2, room_depth/2 - 1],
        "aft_down": [0, 2, room_depth/2 - 1],
        "aftward_down": [0, 2, room_depth/2 - 1],
        "in": [0, 2, 0],
        "out": [0, 2, 0],
        "below": [0, 2, 0],
        "upward": [0, 2, 0],
    }
    
    for direction, target_room in room.exits.items():
        pos = exit_positions.get(direction, [0, 2, 0])
        angle = exit_angles.get(direction, 0)
        scene_exits.append({
            "type": "exit",
            "direction": direction,
            "target": target_room,
            "position": {"x": pos[0], "y": pos[1], "z": pos[2]},
            "rotation": {"y": angle},
            "size": {"width": 3, "height": 4},
            "color": theme["accent"],
            "glow": True,
        })
    
    # Build lights
    lights = [
        {"type": "ambient", "color": theme.get("ambient", "#404060"), "intensity": 0.4},
        {"type": "point", "color": theme["accent"], "intensity": 0.8,
         "position": {"x": 0, "y": 6, "z": 0}, "distance": 30},
    ]
    
    # Add directional lights from exits
    for exit in scene_exits:
        lights.append({
            "type": "point",
            "color": exit["color"],
            "intensity": 0.3,
            "position": exit["position"],
            "distance": 10,
        })
    
    # Camera position
    camera = {
        "position": {"x": 0, "y": 4, "z": 8},
        "lookAt": {"x": 0, "y": 1, "z": 0},
        "fov": 60,
    }
    
    return CompiledScene(
        room=room.name,
        description=room.description,
        theme={"bg": theme["bg"], "fg": theme["fg"], "accent": theme["accent"]},
        floor=floor,
        walls=walls,
        ceiling=ceiling,
        objects=scene_objects,
        agents=scene_agents,
        exits=scene_exits,
        lights=lights,
        camera=camera,
    )

def compile_to_json(scene: CompiledScene) -> Dict:
    """Convert CompiledScene to JSON-serializable dict for Three.js."""
    result = {
        "room": scene.room,
        "description": scene.description,
        "theme": scene.theme,
        "floor": scene.floor,
        "walls": scene.walls,
        "ceiling": scene.ceiling,
        "objects": scene.objects,
        "agents": scene.agents,
        "exits": scene.exits,
        "lights": scene.lights,
        "camera": scene.camera,
    }
    return result

# ============================================================================
# API SERVER
# ============================================================================

class TerrainCore:
    """Core terrain compiler with optional HTTP server."""
    
    def __init__(self, mud_file: str = None, objects_file: str = None):
        self.rooms: List[RoomDef] = []
        self.objects: Dict[str, ObjectDef] = {}
        self.room_map: Dict[str, RoomDef] = {}
        
        if mud_file:
            if not os.path.exists(mud_file):
                raise FileNotFoundError(f"MUD file not found: {mud_file}")
            self.load_mud(mud_file, objects_file)
    
    def load_mud(self, mud_file: str, objects_file: str = None):
        """Load MUD rooms and objects from files."""
        rooms, objects = load_mud_file(mud_file)
        self.rooms = rooms
        self.objects = objects
        self.room_map = {r.name: r for r in rooms}
        
        if objects_file:
            with open(objects_file, 'r') as f:
                _, extra_objs = parse_mud_file(f.read())
                self.objects.update(extra_objs)
    
    def get_room(self, name: str) -> Optional[RoomDef]:
        """Get a room by name."""
        return self.room_map.get(name)
    
    def list_rooms(self) -> List[str]:
        """List all room names."""
        return list(self.room_map.keys())
    
    def compile(self, room_name: str) -> Optional[Dict]:
        """Compile a room to Three.js scene JSON."""
        room = self.get_room(room_name)
        if not room:
            return None
        scene = compile_room(room, self.objects)
        return compile_to_json(scene)
    
    def compile_all(self) -> Dict[str, Dict]:
        """Compile all rooms to scene JSON."""
        return {name: self.compile(name) for name in self.room_map}

# ============================================================================
# CLI + MAIN
# ============================================================================

def generate_scene(room: RoomDef, objects: Dict[str, ObjectDef] = None) -> Dict:
    """Generate scene dict from a RoomDef (exported API)."""
    scene = compile_room(room, objects)
    return compile_to_json(scene)

def generate_all_scenes(rooms: List[RoomDef], objects: Dict[str, ObjectDef] = None) -> Dict[str, Dict]:
    """Generate all room scenes as a dict keyed by room name."""
    return {r.name: generate_scene(r, objects) for r in rooms}

def main():
    """CLI entry point: parse MUD file and output scene.json."""
    import argparse
    parser = argparse.ArgumentParser(description='MUD to Three.js scene compiler')
    parser.add_argument('mud_file', help='MUD rooms file')
    parser.add_argument('-o', '--output', default='scene.json', help='Output JSON file')
    parser.add_argument('-r', '--room', help='Compile single room only')
    args = parser.parse_args()

    rooms, objects = load_mud_file(args.mud_file)
    print(f"Loaded {len(rooms)} rooms, {len(objects)} objects from {args.mud_file}")

    if args.room:
        scenes = {args.room: None}
        for r in rooms:
            if r.name == args.room:
                scenes[args.room] = generate_scene(r, objects)
                break
        if scenes[args.room] is None:
            print(f"Room '{args.room}' not found. Available: {[r.name for r in rooms]}")
            return
    else:
        scenes = generate_all_scenes(rooms, objects)

    output = {
        'meta': {
            'source': args.mud_file,
            'roomCount': len(scenes),
        },
        'rooms': scenes,
        'exits': {},  # exit graph for navigation
    }


    # Build exit graph
    for r in rooms:
        output['exits'][r.name] = {
            direction: target for direction, target in r.exits.items()
        }

    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Wrote {args.output} with {len(scenes)} room scenes")

# ============================================================================
# STANDALONE SERVER
# ============================================================================

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] not in ('--server', 'server'):
        main()
    else:
        import http.server

        PORT = 4072
        MUD_FILE = os.path.join(os.path.dirname(__file__), "rooms.mud")

        class TerrainCoreHandler(http.server.BaseHTTPRequestHandler):
            compiler = TerrainCore(MUD_FILE if os.path.exists(MUD_FILE) else None)

            def _json(self, d, code=200):
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(d).encode())

            def do_GET(self):
                p = self.path
                if p == "/":
                    self._json({"status": "terrain_core", "rooms": self.compiler.list_rooms()})
                elif p == "/rooms":
                    self._json({"rooms": self.compiler.list_rooms()})
                elif p.startswith("/scene/"):
                    room_name = p.split("/scene/")[1]
                    scene = self.compiler.compile(room_name)
                    if scene:
                        self._json(scene)
                    else:
                        self._json({"error": "room not found"}, 404)
                elif p == "/all":
                    self._json(self.compiler.compile_all())
                else:
                    self.send_error(404)

        print(f"🔮 Terrain Core compiler running on port {PORT}")
        print(f"   MUD file: {MUD_FILE}")
        print(f"   API: http://localhost:{PORT}/scene/{{room_name}}")
        print(f"   All rooms: http://localhost:{PORT}/all")
        http.server.HTTPServer(("0.0.0.0", PORT), TerrainCoreHandler).serve_forever()