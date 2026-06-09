import json
import urllib.parse

import httpx

from auth import get_valid_token, run_oauth_flow

def spotify(path: str, method: str = "GET", body: dict | None = None) -> dict | None:
    with httpx.Client() as client:
        resp = client.request(
            method,
            f"https://api.spotify.com/v1{path}",
            headers={
                "Authorization": f"Bearer {get_valid_token()}",
                "Content-Type": "application/json",
            },
            json=body,
        )
    if resp.status_code == 204:
        return None
    resp.raise_for_status()
    return resp.json()

def search_tracks(query: str) -> str:
    """Search for tracks on Spotify."""
    data = spotify(f"/search?q={urllib.parse.quote(query)}&type=track&limit=5")
    tracks = [
        {"name": t["name"], "artist": t["artists"][0]["name"], "album": t["album"]["name"], "uri": t["uri"]}
        for t in data["tracks"]["items"]
    ]
    return json.dumps(tracks, indent=2)

def play_track(uri: str) -> str:
    """Play a track by Spotify URI (e.g. spotify:track:4uLU6hMCjMI75M1A2tKUQC)."""
    # First try the normal path: Spotify will start/resume on the active device.
    try:
        spotify("/me/player/play", method="PUT", body={"uris": [uri]})
        return "▶ Playing track."
    except Exception:
        # If there is no active device, pick an available one and transfer playback.
        devices_resp = spotify("/me/player/devices", method="GET")
        devices = devices_resp.get("devices", []) if isinstance(devices_resp, dict) else []

        # Prefer the first controllable device with an ID.
        device_id = next((d.get("id") for d in devices if d.get("id")), None)
        device_name = next((d.get("name") for d in devices if d.get("id")), None)

        if not device_id:
            raise RuntimeError(
                "No available Spotify device found. Open Spotify on a device first."
            )

        # Transfer playback to that device, then start the track there.
        spotify("/me/player", method="PUT", body={"device_ids": [device_id], "play": False})
        spotify(f"/me/player/play?device_id={device_id}", method="PUT", body={"uris": [uri]})

        return f"▶ Playing track on {device_name or 'Spotify device'}."

def main():
    run_oauth_flow()

if __name__ == "__main__":
    main()
