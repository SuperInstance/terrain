"""
test_field_shadow.py — the field shadow: POSTed by the bridge, served by
terrain_core, applied live by index.html — and NEVER compiled into truth.
"""

import http.server
import json
import os
import sys
import threading
import urllib.error
import urllib.request

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from terrain_core import FIELD_SHADOW, make_server
from elephant_bridge import elephant_to_scene, poll_once


@pytest.fixture()
def core_server():
    """terrain_core's server on an ephemeral port."""
    server = make_server(port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()
    FIELD_SHADOW.clear()


@pytest.fixture()
def field_server():
    """A fake elephant roomd serving one warm field."""
    field = {
        "warmth": 0.62,
        "dials": {"mood": 0.8, "panic": 0.0, "presence": 0.9,
                  "joke_landing": 0.85, "volume": 0.7},
    }

    class FieldHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps(field).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), FieldHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def _post(url, payload):
    data = json.dumps(payload).encode("utf-8") if not isinstance(payload, bytes) else payload
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, json.loads(r.read().decode())


def _get(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return r.status, json.loads(r.read().decode())


# ============================================================================
# POST -> GET round-trip
# ============================================================================

def test_field_starts_empty(core_server):
    status, served = _get(f"{core_server}/field")
    assert status == 200
    assert served == {}


def test_post_get_roundtrip(core_server):
    deltas = elephant_to_scene({
        "warmth": 0.6,
        "dials": {"mood": 0.7, "panic": 0.2, "presence": 0.5},
    })
    status, body = _post(f"{core_server}/field", deltas)
    assert status == 200
    assert body["shadow"] is True

    status, served = _get(f"{core_server}/field")
    assert status == 200
    assert served == deltas


def test_post_replaces_latest_shadow(core_server):
    warm = elephant_to_scene({"warmth": 0.9, "dials": {}})
    cold = elephant_to_scene({"warmth": -0.9, "dials": {}})
    _post(f"{core_server}/field", warm)
    _post(f"{core_server}/field", cold)

    _, served = _get(f"{core_server}/field")
    assert served == cold
    assert served != warm


def test_invalid_field_json_rejected(core_server):
    _post(f"{core_server}/field", {"light": {"color": [1, 1, 1]}})  # prime the shadow
    with pytest.raises(urllib.error.HTTPError) as exc:
        _post(f"{core_server}/field", b"not json at all")
    assert exc.value.code == 400

    # the shadow keeps the last good value — a bad post never poisons it
    _, served = _get(f"{core_server}/field")
    assert served == {"light": {"color": [1, 1, 1]}}


# ============================================================================
# The shadow never touches the compiled truth
# ============================================================================

def test_shadow_never_touches_truth(core_server):
    scene_path = os.path.join(REPO_ROOT, "scene.json")
    with open(scene_path, "rb") as f:
        scene_bytes_before = f.read()

    _, rooms = _get(f"{core_server}/rooms")
    room_name = rooms["rooms"][0]
    _, scene_before = _get(f"{core_server}/scene/{room_name}")

    # a shadow crafted to LOOK like compiled scene data
    poison = elephant_to_scene({"warmth": -1.0, "dials": {"panic": 1.0}})
    poison["rooms"] = {room_name: {"description": "POISONED"}}
    poison["lights"] = [{"type": "point", "color": "#ff0000", "intensity": 9}]
    poison["theme"] = {"bg": "#ff0000"}
    _post(f"{core_server}/field", poison)

    _, scene_after = _get(f"{core_server}/scene/{room_name}")
    assert scene_after == scene_before
    assert "POISONED" not in json.dumps(scene_after)

    _, all_rooms = _get(f"{core_server}/all")
    assert "POISONED" not in json.dumps(all_rooms)

    with open(scene_path, "rb") as f:
        assert f.read() == scene_bytes_before


# ============================================================================
# The bridge: --poll mode, end to end
# ============================================================================

def test_bridge_poll_once_posts_shadow(field_server, core_server):
    deltas = poll_once(field_server, f"{core_server}/field")
    # a warm, laughing room renders amber-bright with a flicker
    assert deltas["light"]["color"][0] > deltas["light"]["color"][2]
    assert deltas["joke_flicker"] == 1.0

    _, served = _get(f"{core_server}/field")
    assert served == deltas
