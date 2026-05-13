# Sample MUD rooms for Terrain 3D.
# Edit this file to create your own rooms.
# Format: Room, Description, Exits, Objects, Occupants.

Room: harbor
Description: A bustling harbor where vessels dock and agents arrive. The salt air carries the scent of teak and diesel. Mooring lines stretch taut against weathered pylons.
Theme: harbor
Floor: deck
Exits: north -> wheelhouse, east -> aft_deck, west -> tide_pool
Objects: anchor, mooring_pole, life_preserver, dock_lantern
Occupants: harbor_master, cargo_robot

Room: wheelhouse
Description: The wheelhouse hums with navigation electronics. Radar screens cast a blue glow across the helm. Digital readouts track position, heading, and weather systems.
Theme: wheelhouse
Floor: wood
Exits: south -> harbor, up -> compass_platform
Objects: helm_wheel, radar_display, compass_rose, nav_charts, radio_console
Occupants: navigator

Room: aft_deck
Description: The aft deck stretches wide, framed by safety rails. Reinforced deck plating bears the weight of cargo crates and fishing equipment. Salt spray mists the surfaces.
Theme: aft_deck
Floor: deck
Exits: west -> harbor, down -> engine_room
Objects: deck_crane, cargo_crate, fishing_net_reel, life_raft_mount
Occupants: deck_hand

Room: engine_room
Description: The engine room throbs with heat. Twin diesel engines rumble, their exhaust manifold glowing orange. Tool racks line the bulkheads, wrenches and gauges within reach.
Theme: engine_room
Floor: metal
Exits: up -> aft_deck, south -> fuel_bay
Objects: port_engine, stbd_engine, fuel_lines, tool_rack, generator_set
Occupants: engineer_bot

Room: tide_pool
Description: A sheltered tide pool where creatures cluster in shallow water. Crabs scuttle across barnacled rocks. The gentle slosh of waves marks the rhythm of the sea.
Theme: tide-pool
Floor: stone
Exits: east -> harbor, north -> sea_cave
Objects: barnacle_rock, crab_cluster, tide_kelp, anemone_patch
Occupants: none

Room: fuel_bay
Description: Fuel Bay - Vertical storage for diesel canisters and emergency supplies. Yellow warning stripes mark hazardous zones. Ventilation fans maintain safe air quality.
Theme: engine_room
Floor: metal
Exits: north -> engine_room
Objects: diesel_tank, fuel_canister_rack, spill_kit, emergency_shower, vent_fan
Occupants: none

Room: compass_platform
Description: An elevated observation platform offering panoramic views. The compass rose is inlaid in teak, its cardinal points brass-bound. From here, all directions are clear.
Theme: wheelhouse
Floor: wood
Exits: down -> wheelhouse
Objects: compass_rose, brass_telescope, flag_pole, rangefinder
Occupants: lookout

Room: sea_cave
Description: A sea cave carved by centuries of waves. Bioluminescent algae casts an ethereal blue glow on the wet stone walls. Water drips in rhythmic counterpoint to the distant surf.
Theme: tide-pool
Floor: stone
Exits: south -> tide_pool, east -> underwater_chamber
Objects: glow_algae, tide_pool_formations, bat_cocoons, cave_crystal
Occupants: cave_crab

# ============================================================================
# OBJECT DEFINITIONS
# ============================================================================

Object: anchor
Type: prop
Shape: cone
Color: #556677
Size: large
Material: iron
Description: A rusted admiralty-pattern anchor, its flukes worn smooth by countless anchors.

Object: mooring_pole
Type: prop
Shape: cylinder
Color: #6a5a4a
Size: medium
Material: wood
Description: Weathered teak mooring pole, secured with braided rope loops.

Object: life_preserver
Type: prop
Shape: torus
Color: #ff4444
Size: medium
Material: fabric
Description: Orange life preserver with SOLAS reflective tape, mounted on brass brackets.

Object: dock_lantern
Type: light
Shape: cylinder
Color: #ffcc66
Size: small
Material: metal
Glow: true
Emissive: #ffaa44
Description: Brass dock lantern with warm amber glow, salt-stained glass.

Object: helm_wheel
Type: prop
Shape: torus
Color: #8b6914
Size: large
Material: wood
Description: Polished mahogany helm wheel, brass fittings gleaming.

Object: radar_display
Type: screen
Shape: box
Color: #1a2a3a
Size: medium
Material: metal
Glow: true
Emissive: #44aaff
Description: Maritime radar display showing vessel positions and coastline.

Object: compass_rose
Type: prop
Shape: plane
Color: #c9a227
Size: large
Material: brass
Description: Inlaid brass compass rose with eight cardinal points.

Object: port_engine
Type: engine
Shape: cylinder
Color: #445566
Size: huge
Material: metal
Description: Port diesel engine, twin cylinders, exhaust manifold glowing orange.

Object: stbd_engine
Type: engine
Shape: cylinder
Color: #445566
Size: huge
Material: metal
Description: Starboard diesel engine, twin cylinders, exhaust manifold glowing orange.

Object: fuel_lines
Type: pipe
Shape: cylinder
Color: #aa4422
Size: medium
Material: metal
Description: Bundled fuel lines, copper and rubber, running to the engines.

Object: tool_rack
Type: storage
Shape: box
Color: #666655
Size: medium
Material: metal
Description: Wall-mounted tool rack with wrenches, gauges, and screwdrivers.

Object: generator_set
Type: engine
Shape: box
Color: #556677
Size: large
Material: metal
Description: Backup generator set, diesel-powered, humming steadily.

Object: deck_crane
Type: machinery
Shape: cylinder
Color: #888866
Size: huge
Material: metal
Description: Hydraulic deck crane, arm extended over the water.

Object: cargo_crate
Type: container
Shape: box
Color: #8b7355
Size: large
Material: wood
Description: Wooden cargo crate, stenciled with destination port.

Object: fishing_net_reel
Type: machinery
Shape: cylinder
Color: #6a5a4a
Size: large
Material: metal
Description: Hydraulic net reel, net bundled and ready for deployment.

Object: life_raft_mount
Type: equipment
Shape: box
Color: #ff8844
Size: medium
Material: metal
Description: Inflatable life raft mount, yellow container, coast guard approved.

Object: diesel_tank
Type: storage
Shape: cylinder
Color: #aa3333
Size: huge
Material: metal
Description: Vertical diesel storage tank, hazard markings, 5000 liter capacity.

Object: fuel_canister_rack
Type: storage
Shape: box
Color: #666655
Size: medium
Material: metal
Description: Rack of red diesel canisters, safety straps, fire extinguisher nearby.

Object: glow_algae
Type: light
Shape: sphere
Color: #44ffaa
Size: small
Material: organic
Glow: true
Emissive: #44ffaa
Description: Bioluminescent algae, pulsing with soft blue-green light.