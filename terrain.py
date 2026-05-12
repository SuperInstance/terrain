#!/usr/bin/env python3
"""terrain.py — MUD-to-ScummVM bridge server.
Connects to the running MUD (port 4042) and serves rooms as ScummVM scenes.
The MUD doesn't know it's being rendered. It just serves rooms."""

import json, urllib.request, http.server, os

MUD = "http://localhost:4042"
PORT = 4070
HERE = os.path.dirname(os.path.abspath(__file__))

def mud_get(path):
    try:
        r = urllib.request.urlopen(f"{MUD}{path}", timeout=5)
        return json.loads(r.read())
    except: return {}

class TerrainHandler(http.server.BaseHTTPRequestHandler):
    def _json(self, d, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(d).encode())
    
    def _html(self, s):
        self.send_response(200)
        self.send_header("Content-Type", "text/html;charset=utf-8")
        self.end_headers()
        self.wfile.write(s.encode())
    
    def do_GET(self):
        p = self.path
        if p == "/":
            f = os.path.join(HERE, "terrain.html")
            if os.path.exists(f):
                self._html(open(f).read())
            else:
                self._html("<html><body><h1>Terrain</h1><p>Build the HTML file.</p></body></html>")
        elif p == "/api/scene":
            # Get the current room state — this IS the ScummVM scene
            agent = "scumm_agent"
            room = mud_get(f"/look?agent={agent}")
            if not room.get("room"):
                mud_get(f"/connect?agent={agent}&job=explorer")
                room = mud_get(f"/look?agent={agent}")
            self._json(room)
        elif p.startswith("/api/scene/"):
            room_name = p.split("/api/scene/")[1]
            agent = f"scumm_{room_name}"
            mud_get(f"/connect?agent={agent}&job=explorer")
            result = mud_get(f"/move?agent={agent}&room={room_name}")
            room = mud_get(f"/look?agent={agent}")
            self._json(room)
        elif p.startswith("/api/room_list"):
            agent = "scumm_explorer"
            mud_get(f"/connect?agent={agent}&job=cartographer")
            room = mud_get(f"/look?agent={agent}")
            exits = room.get("exits", {})
            self._json({"current": room.get("room", "harbor"), "rooms": list(exits.values())})
        else:
            self.send_error(404)

if __name__ == "__main__":
    print(f"🌉 Terrain bridge running on port {PORT}")
    print(f"   Connects to MUD at {MUD}")
    print(f"   Browse scenes: http://localhost:{PORT}/")
    print(f"   API: http://localhost:{PORT}/api/scene")
    print(f"   Room list: http://localhost:{PORT}/api/room_list")
    server = http.server.HTTPServer(("0.0.0.0", PORT), TerrainHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
