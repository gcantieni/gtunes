import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os
from time import sleep
import threading
import time
from Levenshtein import distance
import re
from dataclasses import dataclass
from gtunes import db

@dataclass
class SpotTuneTrackData():
    """
    Wraps pieces of spotify data as they relate to a tune.
    """
    album_name: str = ""
    track_number: int = 0
    track_uri: str = ""
    album_uri: str = ""
    track_tunes: str = ""
    track_name: str = ""
    artist_name: str = ""
    tune: db.Tune = None


def print_debug(debug_str):
    should_debug = False
    if should_debug:
        print(debug_str)

def time_to_ms(time_str):
    if time_str.find(":") != -1:
        minutes, seconds = map(int, time_str.split(':'))
    else:
        minutes = 0
        seconds = int(time_str)
    return (minutes * 60 * 1000) + (seconds * 1000)

class Track:
    """An audio track."""
    def __init__(self, uri, start=None, end=None):
        self.uri = "spotify:track:" + uri
        self.start = time_to_ms(start) if start else 0
        self.end = time_to_ms(end) if end else end

def connect_to_spotify():
    load_dotenv()

    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")

    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id,
                                                   client_secret=client_secret,
                                                   redirect_uri=redirect_uri,
                                                   scope="user-modify-playback-state user-read-playback-state"))
    
    return sp

def spot_play_track(track_uri, sp, retries=3, delay=7, position_ms=0, log_fn = print) -> None:
    for _ in range(retries + 1):
        try:
            sp.start_playback(uris=[track_uri], position_ms=position_ms)

        except spotipy.exceptions.SpotifyException as e:
            if e.reason == "NO_ACTIVE_DEVICE":
                log_fn("Unable to determine which device to play on. Try briefly pressing play on target device.")
                log_fn(f"Trying again in {delay} seconds")
                time.sleep(delay)
            else:
                raise e
            
def spot_pause_track(track_uri: str, sp: spotipy.Spotify) -> None:
    sp.pause_playback()


def listen_for_input():
    global stop_loop
    while True:
        user_input = input("Press 'q' to quit: ").strip().lower()
        if user_input == "q":
            stop_loop = True
            break

stop_loop = False

def loop_track(track, sp):
    sp = connect_to_spotify()
    sp.start_playback(uris=[track.uri], position_ms=track.start)

    # Function to listen for user input
    if track.end:
        print("Looping track:")

        input_thread = threading.Thread(target=listen_for_input, daemon=True)
        input_thread.start()

        while True:
            playback = sp.current_playback()
            if not playback or stop_loop: #or not playback['is_playing']:
                break  # Exit if playback stops

            progress = playback['progress_ms']
            if progress >= track.end:
                # Restart playback at the loop start time
                sp.start_playback(uris=[track.uri], position_ms=track.start)
            sleep(0.5)  # Check playback position every 500ms

def _print_results(results):
    for i in range(len(results)):
        r = results[i]
        print(f"{i}: {r['name']} by {r['artists'][0]['name']}")

def _print_help_prompt():
    print("<int>: play track, a: accept track, s10: start at 10, e20 end at 20, p print tunes, q quit, h help: ")

def levenshtein_string_similarity(string1, string2):
    dist = 1 - (distance(string1, string2) / max(len(string1), len(string2)))
    print_debug(f"Distance between {string1} and {string2} is {dist}")
    return dist


def spot_search_albums(album_name: str, sp: spotipy.Spotify, artist_name: str = None) -> dict | None:
    """
    Search for album_name and compare title similarity using the Levenshtein algorithm.
    If artist name is passed in, it will also compare that using Levenshtein.
    It will try to detect multiple artists and compare each of them individually to each artist
    who made a given album.
    """
    results = sp.search(album_name, type='album')

    for alb in results['albums']['items']:
        result_name = alb['name']
        if levenshtein_string_similarity(album_name, result_name) > .8:
            if not artist_name:
                return alb
            
            # Split artist_name string on common deliminters
            for arg_artist in re.split("and|[&,]", artist_name, flags=re.IGNORECASE):
                # For now we have "big hammer" approach of: if any spotify artist matches any
                # passed in artist, that's enough. This could be refined in the future.
                for spot_artist in alb['artists']:
                    if levenshtein_string_similarity(arg_artist, spot_artist['name']) > .8:
                        return alb
    return None

# returns the track data of the track being played
def spot_play_nth_album_track(spot_album_id, track_num, sp):
    tracks = sp.album_tracks(spot_album_id)['items']
    if track_num < 1 or track_num > len(tracks):
        print(f"Track index must be between 1 and {len(tracks)}. Got {track_num}")
        return None

    track = spot_get_nth_album_track(spot_album_id, track_num, sp)

    spot_play_track(track["uri"], sp)

    return track

def spot_get_nth_album_track(spot_album_id: str, track_num: int, sp: spotipy.Spotify) -> dict:
    tracks = sp.album_tracks(spot_album_id)['items']
    if track_num < 1 or track_num > len(tracks):
        print(f"Track index must be between 1 and {len(tracks)}. Got {track_num}")
        return None
    
    return tracks[track_num - 1]

def search_for_track(track_name, sp):
    results = sp.search(track_name)
    results = results['tracks']['items'] # I don't care much about anything but the track data

    _print_results(results)
    _print_help_prompt()

    save_track = False
    track = None
    while True:
        t = input("tune> ").strip().lower()
        try:
            t = int(t)

            selected_result = results[t]
            print(f"Playing {selected_result['name']}")
            track = Track(selected_result['id'])

            spot_play_track(track, sp)
        except ValueError:
            if t == "a":
                save_track = True
                break
            elif t == "q":
                save_track = False
                break
            elif t == "h":
                _print_help_prompt()
                continue
            elif t == "p":
                _print_results(results)
                continue
            elif t[0] == "s":
                t = t[1:]
                try:
                    start = int(t)
                    print(f"Setting start time to {start}")
                    track.start = start
                except ValueError:
                    print(f"Invalid start time {t}")
            elif t[0] == "e":
                t = t[1:]
                try:
                    end = int(t)
                    print(f"Setting end time to {end}")
                    track.end = start
                except ValueError:
                    print(f"Invalid end time {t}")
    if not save_track:
        print("you've chosen not to save track")
    else:
        print("you've chosen to save track. would you like to loop it?")

        i = input("y/n")
        if i == "y":
            loop_track(track, sp)
        else:
            print("so long~")


def main():
    # save it in the tune database for the future.

    sp = connect_to_spotify()
    # john_dohertys = Track("spotify:track:3XDCKy6Z5lC9SP37doE9S5", start="11", end="32")
    # loop_track(john_dohertys, sp)

    album = spot_search_albums("Fortune Favours The Merry", sp, artist_name="Peter Horan And Gerry Harrington")
    # {'album_type': 'album', 'total_tracks': 17, 'available_markets': ['AR', 'AU', 'AT', 'BE', 'BO', 'BR', 'BG', 'CA', 'CL', 'CO', 'CR', 'CY', 'CZ', 'DK', 'DO', 'DE', 'EC', 'EE', 'SV', ...], 'external_urls': {'spotify': 'https://open.spotify.com/album/48NVzBxwF0acp8AWHFGtSq'}, 'href': 'https://api.spotify.com/v1/albums/48NVzBxwF0acp8AWHFGtSq', 'id': '48NVzBxwF0acp8AWHFGtSq', 'images': [{...}, {...}, {...}], 'name': 'Fortune Favours the Merry', 'release_date': '2016-06-29', 'release_date_precision': 'day', 'type': 'album', 'uri': 'spotify:album:48NVzBxwF0acp8AWHFGtSq', 'artists': [{...}, {...}]}

    track = spot_get_nth_album_track(album["uri"], 1, sp)
    # {'artists': [{...}, {...}], 'available_markets': ['AR', 'AU', 'AT', 'BE', 'BO', 'BR', 'BG', 'CA', 'CL', 'CO', 'CR', 'CY', 'CZ', 'DK', 'DO', 'DE', 'EC', 'EE', 'SV', ...], 'disc_number': 1, 'duration_ms': 221040, 'explicit': False, 'external_urls': {'spotify': 'https://open.spotify.com/track/0CC5hvN9G0Q4VoEDfoYogn'}, 'href': 'https://api.spotify.com/v1/tracks/0CC5hvN9G0Q4VoEDfoYogn', 'id': '0CC5hvN9G0Q4VoEDfoYogn', 'name': 'The Gold Ring / The Rambling Pitchfork', 'preview_url': None, 'track_number': 1, 'type': 'track', 'uri': 'spotify:track:0CC5hvN9G0Q4VoEDfoYogn', 'is_local': False}

    print(track)

if __name__ == '__main__':
    main()

