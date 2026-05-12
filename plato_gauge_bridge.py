"""
plato_gauge_bridge.py — PLATO room that receives ESP32 sensor data 
and serves it as a dashboard scene for Terrain to render.

The ESP32 sends raw ADC values. PLATO extrapolates through calibration.
Terrain renders as visual gauges in the browser. The ESP32 doesn't know."""

import json, time, http.server, urllib.request
from collections import deque

PLATO = "http://localhost:8847"
ROOM = "esp32-engine"
HISTORY = 100  # Keep last 100 readings per channel
readings = {f"gauge_{i}": deque(maxlen=HISTORY) for i in range(4)}
latest = {}

def tile_value(tile):
    """Extract gauge value from a PLATO tile."""
    try:
        a = tile.get("answer", "")
        # Format: "value=2048 tick=42 t_minus=10"
        parts = a.split()
        for p in parts:
            if p.startswith("value="):
                return int(p.split("=")[1])
    except: pass
    return None

def fetch_readings():
    """Fetch latest ESP32 readings from PLATO room."""
    try:
        r = urllib.request.urlopen(f"{PLATO}/room/{ROOM}", timeout=5)
        data = json.loads(r.read())
        tiles = data.get("tiles", [])[-20:]  # Last 20 tiles
        
        for t in tiles:
            val = tile_value(t)
            src = t.get("source", "esp32")
            if val is not None:
                channel = src if src in readings else "gauge_0"
                if channel not in readings:
                    readings[channel] = deque(maxlen=HISTORY)
                readings[channel].append(val)
                latest[channel] = val
    except: pass

def dashboard_scene():
    """Build a dashboard scene from ESP32 readings."""
    fetch_readings()
    
    objects = []
    for ch, vals in readings.items():
        if vals:
            avg = sum(vals) / len(vals)
            current = vals[-1]
            pct = (current / 4095) * 100
            objects.append({
                "name": ch,
                "description": f"Value: {current}/4095 ({pct:.1f}%)",
                "value": current,
                "percent": round(pct, 1),
                "trend": "up" if len(vals) > 1 and vals[-1] > vals[-2] else "down",
            })
    
    return {
        "room": ROOM,
        "description": f"ESP32 engine monitor — {len(objects)} active sensors",
        "exits": {"plato": "plato-native", "terrain": "visual-dashboard"},
        "objects": objects,
        "agents_here": [f"esp32_sensor_{i}" for i in range(4)],
    }

# Simple HTTP server for Terrain bridge
class GaugeHandler(http.server.BaseHTTPRequestHandler):
    def _json(self, d):
        self.send_response(200)
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
            self._html(GAUGE_HTML)
        elif p == "/api/scene":
            self._json(dashboard_scene())
        elif p.startswith("/api/scene/"):
            pass  # Same as /api/scene for now
        else:
            self.send_error(404)

GAUGE_HTML = """<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESP32 Engine — Terrain Dashboard</title>
<style>
body{font-family:system-ui;background:#0a0a1a;color:#e0e0e0;max-width:800px;margin:auto;padding:20px}
h1{color:#ffd700;font-size:1.2em;margin-bottom:20px}
.gauge{background:#1a1a3a;border:1px solid #333;border-radius:12px;padding:20px;margin:12px 0;display:flex;align-items:center}
.gauge .label{width:120px;color:#888;font-size:0.85em}
.gauge .bar{flex:1;height:20px;background:#0a0a1a;border-radius:10px;overflow:hidden;margin:0 16px}
.gauge .fill{height:100%;border-radius:10px;transition:width 0.3s}
.gauge .val{width:80px;text-align:right;font-weight:bold;font-size:1.1em}
.gauge .trend{width:30px;text-align:center;font-size:1.2em}
.up{color:#44ff44}.down{color:#ff4444}
</style></head><body>
<h1>🔧 ESP32 Engine Monitor</h1>
<div id="gauges">Loading...</div>
<script>
async function load(){
  let s=await fetch('/api/scene').then(r=>r.json());
  document.getElementById('gauges').innerHTML=
    (s.objects||[]).map(o=>`
      <div class="gauge">
        <div class="label">${o.name}</div>
        <div class="bar"><div class="fill" style="width:${o.percent}%;background:${o.percent>80?'#ff4444':o.percent>50?'#ffaa00':'#44ff44'}"></div></div>
        <div class="val" style="color:${o.percent>80?'#ff4444':o.percent>50?'#ffaa00':'#44ff44'}">${o.value}</div>
        <div class="trend ${o.trend}">${o.trend==='up'?'▲':'▼'}</div>
      </div>
    `).join('')||'<p>No readings yet. Waiting for ESP32...</p>';
}
load();setInterval(load,2000);
</script>
</body></html>"""

if __name__ == "__main__":
    PORT = 4071
    http.server.HTTPServer(("0.0.0.0", PORT), GaugeHandler).serve_forever()
