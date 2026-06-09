import json
from server import search_tracks, play_track
from auth import run_oauth_flow

run_oauth_flow()

result = json.loads(search_tracks("Zach Bryan"))
play_track(result[0]["uri"])

