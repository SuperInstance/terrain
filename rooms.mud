# Fishing Vessel "Cocapn" — MUD Room Definitions
# 5 rooms matching the vessel room navigator
# Run: python3 terrain_core.py rooms.mud

Room: wheelhouse
Description: The wheelhouse is the nerve center of the vessel. Navigation electronics line the console in careful rows. A magnetic compass sits port of the helm. Radar and chartplotter displays cast pale light across polished teak trim. The large windows offer 270-degree visibility over the bow and decks.
Theme: wheelhouse
Floor: wood
Exits: aft -> aft_cockpit, down -> galley
Objects: helm_wheel, radar_display, compass_rose, nav_charts, radio_console, gpsReceiver, spotlight_control
Occupants: captain

Room: galley
Description: The galley is compact but efficient. A small propane stove sits beneath timber cabinets. The sink pumps seawater or fresh depending on the valve setting. Teak fiddled benches line the table where crew take meals. Through the porthole, grey sky and sea blur together.
Theme: wheelhouse
Floor: wood
Exits: up -> wheelhouse, aft -> aft_cockpit
Objects: propane_stove, sink_pump, galley_table, icebox, water_tank, coffee_maker
Occupants: none

Room: foredeck
Description: The foredeck is the business end of the boat. Reinforced deck plating bears the anchor chain and rope bins. Safety rails line the gunwales. The windlass handles anchor duties while bait tanks murmur with circulating seawater. Salt crusts the hawse pipes where anchor rode runs.
Theme: aft_deck
Floor: deck
Exits: aft -> aft_cockpit, below -> engine_room
Objects: windlass, anchor_chain, bait_tank, rope_bin, hawse_pipe, cleat_forward
Occupants: deckhand

Room: engine_room
Description: The engine room thrums with diesel power. Twin engines drive the stern drive. The generator hums beneath the workbench where tools hang in careful order. Fuel lines bundle along the starboard bulkhead leading to the main tanks. Oil smell and heat define this working space.
Theme: engine_room
Floor: metal
Exits: up -> foredeck, forward -> aft_cockpit
Objects: port_engine, stbd_engine, generator, fuel_lines, tool_rack, oil_filter, battery_bank
Occupants: engineer_bot

Room: aft_cockpit
Description: The aft cockpit is where the catch comes aboard. Scuppers drain seawater over the stern. Reinforced deck plates bear the weight of catch boxes and equipment. The transom door leads to swim platform when docked. Control station for stern drive and trim tabs.
Theme: aft_deck
Floor: deck
Exits: forward -> foredeck, forward_up -> wheelhouse, forward_down -> galley, in -> engine_room
Objects: stern_drive, trim_tabs, fishfinder, downrigger_posts, bait_well, transom_sump
Occupants: deckhand, cargo_robot

# ============================================================================
# OBJECT DEFINITIONS
# ============================================================================

Object: helm_wheel
Type: prop
Shape: torus
Color: #8b6914
Size: large
Material: wood
Description: Polished mahogany helm wheel, eight spokes, brass hub gleaming.

Object: radar_display
Type: screen
Shape: box
Color: #1a2a3a
Size: medium
Material: metal
Glow: true
Emissive: #44aaff
Description: Maritime radar display, phosphor green sweep showing targets.

Object: compass_rose
Type: prop
Shape: plane
Color: #c9a227
Size: medium
Material: brass
Description: Ship's compass in brass binnacle, gimbaled, eight cardinal points marked.

Object: nav_charts
Type: screen
Shape: box
Color: #1a3a2a
Size: small
Material: metal
Glow: true
Emissive: #44ff88
Description: Chartplotter screen showing vessel position on nautical charts.

Object: radio_console
Type: equipment
Shape: box
Color: #2a2a2a
Size: medium
Material: metal
Glow: true
Emissive: #446688
Description: VHF radio console, channel 16 guarded, hailer and foghorn buttons.

Object: gpsReceiver
Type: equipment
Shape: box
Color: #1a1a1a
Size: small
Material: metal
Description: GPS receiver with WAAS correction, displays lat/lon and COG.

Object: spotlight_control
Type: equipment
Shape: box
Color: #333333
Size: small
Material: metal
Description: Remote spotlight control, joystick for pan and tilt.

Object: propane_stove
Type: appliance
Shape: box
Color: #888888
Size: medium
Material: metal
Description: Two-burner propane stove, gimballed for sea angle, broiler below.

Object: sink_pump
Type: equipment
Shape: cylinder
Color: #666666
Size: small
Material: metal
Description: Manual pump sink, lever action, seawater or fresh water selectable.

Object: galley_table
Type: furniture
Shape: box
Color: #6b4423
Size: large
Material: teak
Description: Teak fiddled table, benches each side, secured for sea conditions.

Object: icebox
Type: storage
Shape: box
Color: #aaaaaa
Size: medium
Material: metal
Description: Top-opening icebox, baffled liner, drains overboard.

Object: water_tank
Type: storage
Shape: cylinder
Color: #aaaaaa
Size: large
Material: metal
Description: Fresh water tank, 200 liter capacity, gauge visible through sight tube.

Object: coffee_maker
Type: appliance
Shape: box
Color: #222222
Size: small
Material: metal
Description: Simple drip coffee maker, 12V powered, secured to counter.

Object: windlass
Type: machinery
Shape: cylinder
Color: #555555
Size: large
Material: metal
Description: Anchor windlass, bronze drum, chain gypsy, foot switch controls.

Object: anchor_chain
Type: pipe
Shape: cylinder
Color: #445566
Size: huge
Material: iron
Description: Galvanized anchor chain, short link, marked every fathom.

Object: bait_tank
Type: storage
Shape: box
Color: #4488aa
Size: large
Material: metal
Description: Live bait tank with circulating seawater pump, hinged lid.

Object: rope_bin
Type: storage
Shape: box
Color: #6a5a4a
Size: medium
Material: wood
Description: Rope bin with braided nylon line, different sizes and lengths.

Object: hawse_pipe
Type: pipe
Shape: cylinder
Color: #555555
Size: small
Material: metal
Description: Hawse pipe where anchor rode exits to chain Locker.

Object: cleat_forward
Type: prop
Shape: cylinder
Color: #888888
Size: medium
Material: metal
Description: Raised deck cleat, forged steel, bolted through deck plate.

Object: port_engine
Type: engine
Shape: cylinder
Color: #445566
Size: huge
Material: metal
Description: Port diesel engine, turbocharged, 350hp, dry exhaust elbow glowing orange.

Object: stbd_engine
Type: engine
Shape: cylinder
Color: #445566
Size: huge
Material: metal
Description: Starboard diesel engine, twin to port, synchronized throttle.

Object: generator
Type: engine
Shape: box
Color: #556677
Size: large
Material: metal
Description: Onan generator set, 8kW, diesel-powered, sound-shielded housing.

Object: fuel_lines
Type: pipe
Shape: cylinder
Color: #aa4422
Size: medium
Material: metal
Description: Bundled fuel lines, USCG approved, run to main tanks and filters.

Object: tool_rack
Type: storage
Shape: box
Color: #666655
Size: medium
Material: metal
Description: Wall-mounted tool rack, wrenches and screwdrivers in order.

Object: oil_filter
Type: filter
Shape: cylinder
Color: #888866
Size: small
Material: metal
Description: Spin-on oil filter, spare filters stored below.

Object: battery_bank
Type: storage
Shape: box
Color: #222222
Size: large
Material: metal
Description: House bank, four 6V deep cycle, sealed, on-off switch visible.

Object: stern_drive
Type: engine
Shape: cylinder
Color: #445566
Size: huge
Material: metal
Description: Stern drive unit, bravo three, propellers forward of rudders.

Object: trim_tabs
Type: equipment
Shape: plane
Color: #555555
Size: medium
Material: metal
Description: Lenco trim tabs, port and starboard, switch panel at helm.

Object: fishfinder
Type: screen
Shape: box
Color: #1a2a3a
Size: medium
Material: metal
Glow: true
Emissive: #44ffff
Description: Color sonar fishfinder, transducer through hull, shows bottom and fish.

Object: downrigger_posts
Type: machinery
Shape: cylinder
Color: #666655
Size: large
Material: metal
Description: Dual downrigger mounts, rod holders each side, release clips.

Object: bait_well
Type: storage
Shape: box
Color: #4488aa
Size: medium
Material: metal
Description: Live bait well, recirculating pump, divided sections.

Object: transom_sump
Type: equipment
Shape: box
Color: #555555
Size: small
Material: metal
Description: Transom sump box, shower drain and washdown pump.