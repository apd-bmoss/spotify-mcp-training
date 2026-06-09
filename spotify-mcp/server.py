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
    spotify("/me/player/play", method="PUT", body={"uris": [uri]})
    return "▶ Playing track."

def main():
    run_oauth_flow()