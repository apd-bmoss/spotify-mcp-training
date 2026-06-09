import base64
import os
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event, Thread

import httpx
from dotenv import load_dotenv

load_dotenv()  # loads .env if it exists, does nothing if it doesn't

CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID") or os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET") or os.getenv("SPOTIFY_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in .env or environment")
                       
REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = " ".join([
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
])

_tokens: dict = {"access_token": None, "refresh_token": None, "expires_at": 0}


def _credentials() -> str:
    return base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()


def _exchange_code(code: str) -> None:
    resp = httpx.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {_credentials()}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI},
    )
    resp.raise_for_status()
    data = resp.json()
    _tokens["access_token"] = data["access_token"]
    _tokens["refresh_token"] = data["refresh_token"]
    _tokens["expires_at"] = time.time() + data["expires_in"]


def _refresh_access_token() -> None:
    resp = httpx.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {_credentials()}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "refresh_token", "refresh_token": _tokens["refresh_token"]},
    )
    resp.raise_for_status()
    data = resp.json()
    _tokens["access_token"] = data["access_token"]
    _tokens["expires_at"] = time.time() + data["expires_in"]


def run_oauth_flow() -> None:
    """Open browser, spin up a local callback server, wait for the code."""
    auth_done = Event()

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            code = urllib.parse.parse_qs(
                urllib.parse.urlparse(self.path).query
            ).get("code", [None])[0]
            if code:
                _exchange_code(code)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Authenticated! You can close this tab.")
                auth_done.set()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 8888), CallbackHandler)
    Thread(target=server.serve_forever, daemon=True).start()

    auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
    })
    print("Opening Spotify login in your browser...")
    webbrowser.open(auth_url)
    auth_done.wait(timeout=120)
    server.shutdown()
    print("Authentication complete.")


def get_valid_token() -> str:
    """Return a valid access token, refreshing if needed."""
    if not _tokens["access_token"]:
        run_oauth_flow()
    if time.time() > _tokens["expires_at"] - 30:
        _refresh_access_token()
    return _tokens["access_token"]
