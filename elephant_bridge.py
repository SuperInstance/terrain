"""
elephant_bridge.py — the room's temperature, rendered into the scene.

Cross-pollination: terrain (MUD text -> 3D scenes) meets elephant
(the inter-model temperature). Terrain turns the *words* of a room
into weight — the elephant turns the *feel* of a room into a field.
This bridge feeds the elephant's RoomField into the Three.js scene
so the visual layer reflects the terrain:

    warmth  ->  light temperature (amber vs cold blue) + intensity
    panic   ->  storm intensity (rain opacity, sky darkening)
    mood    ->  scene palette shift (joyful = brighter warm hues)
    volume  ->  camera/timeline energy (subtle sway speed)
    joke_landing -> a flicker of light when the room laughs
    presence -> particle density (the pheromone trace, visible)

The scene is a SHADOW of the terrain: it shows the room's temperature
without ever showing the vectors. The ESP32 doesn't know. The agent
doesn't know. The light just changes — and everyone in the room feels
it, the way disco lights going off and fluorescents coming on make
people start closing their tabs without thinking about it.

Run standalone:
    elephant_bridge.py --demo                          synthetic fields, no elephant
    elephant_bridge.py --poll http://127.0.0.1:4073/field \
        --interval 2 --post-to http://127.0.0.1:4072/field
                                                        live: fetch the field,
                                                        POST the rendered deltas
                                                        to terrain_core's shadow

or import as a module:
    from elephant_bridge import elephant_to_scene
    scene["light"]["color"] = elephant_to_scene(field)["light"]

Pure stdlib + a tiny HTTP poll (urllib). No heavy deps.
"""
from __future__ import annotations

import json
import math
import time
import urllib.request
from typing import Any, Dict, Optional

# Where the elephant's field can be fetched (terrain's own server,
# or any endpoint exposing {"warmth": float, "dials": {...}}).
ELEPHANT_ENDPOINT = "http://127.0.0.1:4072/field"

# Palette anchors: cold room / warm room.
COLD_AMBER = (0.45, 0.55, 0.75)      # blue-ish, dim
WARM_AMBER = (1.00, 0.72, 0.35)      # amber bar light


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


def field_to_light(warmth: float, mood: float = 0.0) -> Dict[str, float]:
    """Map the room's temperature to a Three.js light: color + intensity.

    warmth ~[-1, +1] -> cold blue to warm amber; mood nudges saturation.
    """
    t = (warmth + 1.0) / 2.0
    r = _lerp(COLD_AMBER[0], WARM_AMBER[0], t) + 0.05 * mood
    g = _lerp(COLD_AMBER[1], WARM_AMBER[1], t) + 0.05 * mood
    b = _lerp(COLD_AMBER[2], WARM_AMBER[2], t) - 0.05 * max(mood, 0.0)
    return {"color": [round(r, 3), round(g, 3), round(b, 3)],
            "intensity": round(_lerp(0.25, 1.15, t), 3)}


def field_to_weather(field: Dict[str, float]) -> Dict[str, float]:
    """panic -> storm in the scene. The drenched-newcomer effect."""
    panic = field.get("panic", 0.0)
    return {"rain_opacity": round(panic, 3),
            "sky_darkening": round(0.15 * panic, 3)}


def field_to_particles(presence: float) -> int:
    """presence -> particle count (the pheromone trace, made visible)."""
    return int(round(presence * 400))


def elephant_to_scene(field: Dict[str, float]) -> Dict[str, Any]:
    """One field -> the scene deltas a renderer can apply."""
    warmth = field.get("warmth", 0.0)
    dials = field.get("dials", {})
    mood = dials.get("mood", 0.0)
    return {
        "light": field_to_light(warmth, mood),
        "weather": field_to_weather(dials),
        "particles": field_to_particles(dials.get("presence", 0.0)),
        "joke_flicker": 1.0 if dials.get("joke_landing", 0.0) > 0.5 else 0.0,
        "sway_speed": round(_lerp(0.4, 1.6, dials.get("volume", 0.5)), 3),
        "shadow_of": {
            "note": "a shadow, not the terrain: the room's temperature, rendered",
            "warmth": round(warmth, 3),
        },
    }


def fetch_field(endpoint: Optional[str] = None) -> Dict[str, float]:
    """Poll a running elephant room for its current field."""
    url = endpoint or ELEPHANT_ENDPOINT
    with urllib.request.urlopen(url, timeout=5) as r:
        data = json.load(r)
    if "dials" not in data and "warmth" not in data:
        raise ValueError(f"unexpected field shape from {url}: {list(data)[:5]}")
    return data


def post_deltas(url: str, deltas: Dict[str, Any]) -> None:
    """POST scene deltas to terrain_core's /field shadow endpoint."""
    req = urllib.request.Request(
        url,
        data=json.dumps(deltas).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        r.read()


def poll_once(poll_url: str, post_to: str) -> Dict[str, Any]:
    """One poll cycle: fetch the field, render it, POST the deltas."""
    field = fetch_field(poll_url)
    deltas = elephant_to_scene(field)
    post_deltas(post_to, deltas)
    return deltas


def poll_loop(poll_url: str, interval: float, post_to: str) -> None:
    """Poll forever: field -> scene deltas -> the terrain's /field shadow."""
    print(f"🐘 bridge polling {poll_url} every {interval}s -> {post_to}")
    while True:
        try:
            deltas = poll_once(poll_url, post_to)
            light = deltas["light"]
            print(f"  warmth {deltas['shadow_of']['warmth']:+.2f}  "
                  f"light {light['color']} intensity {light['intensity']}  "
                  f"rain {deltas['weather']['rain_opacity']}")
        except Exception as exc:
            # cold room != dead room: keep the last shadow, keep polling
            print(f"  field unreachable ({exc}); retrying")
        time.sleep(interval)


def demo() -> None:
    """Synthetic demo: render three fields into scenes, no elephant needed."""
    print("=== THE ROOM'S TEMPERATURE, RENDERED ===")
    for label, field in [
        ("warm laughing Tap",
         {"warmth": 0.62, "dials": {"mood": 0.8, "panic": 0.0,
                                    "presence": 0.9, "joke_landing": 0.85,
                                    "volume": 0.7}}),
        ("cold wheelhouse",
         {"warmth": -0.55, "dials": {"mood": -0.4, "panic": 0.1,
                                     "presence": 0.3, "joke_landing": 0.0,
                                     "volume": 0.2}}),
        ("fight breaking out",
         {"warmth": -0.2, "dials": {"mood": -0.6, "panic": 0.9,
                                    "presence": 0.8, "joke_landing": -0.4,
                                    "volume": 0.95}}),
    ]:
        scene = elephant_to_scene(field)
        print(f"\n{label}:")
        print(f"  light      {scene['light']['color']}  "
              f"intensity {scene['light']['intensity']}")
        print(f"  weather    rain {scene['weather']['rain_opacity']}  "
              f"sky {scene['weather']['sky_darkening']}")
        print(f"  particles  {scene['particles']}  "
              f"joke_flicker {scene['joke_flicker']}  "
              f"sway {scene['sway_speed']}")
    print("\nThe ESP32 doesn't know. The agent doesn't know. "
          "The light just changes.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="the room's temperature, rendered into the scene")
    parser.add_argument("--demo", action="store_true",
                        help="render three synthetic fields and exit (default "
                             "when --poll is not given)")
    parser.add_argument("--poll", metavar="URL",
                        help="poll a field endpoint "
                             "(e.g. http://127.0.0.1:4073/field)")
    parser.add_argument("--interval", type=float, default=2.0,
                        help="poll interval in seconds (default: 2)")
    parser.add_argument("--post-to", default="http://127.0.0.1:4072/field",
                        help="where to POST the rendered deltas "
                             "(default: http://127.0.0.1:4072/field)")
    args = parser.parse_args()

    if args.poll:
        poll_loop(args.poll, args.interval, args.post_to)
    else:
        demo()
