import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os
from time import sleep
import threading
import time
from Levenshtein import distance


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

def play_track(track_uri, sp, retries=3, delay=7, position_ms=0):
    for _ in range(retries):
        try:
            sp.start_playback(uris=[track_uri], position_ms=position_ms)
        except spotipy.exceptions.SpotifyException as e:
            if e.reason == "NO_ACTIVE_DEVICE":
                print("Unable to determine which device to play on. Try briefly pressing play on target device.")
                print(f"Trying again in {delay} seconds")
                time.sleep(delay)
            else:
                raise e


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
    return 1 - (distance("Some Album Title", "Some Album Ttle") / max(len("Some Album Title"), len("Some Album Ttle")))

# search for album_name
# compare title similarity using the Levenshtein algorithm
def spot_search_albums(album_name, sp):
    results = sp.search(album_name, type='album')

    for alb in results['albums']['items']:
        result_name = alb['name']
        if levenshtein_string_similarity(album_name, result_name) > .8:
            return alb

    return None

# returns the track data of the track being played
def spot_play_nth_album_track(spot_album_id, track_num, sp):
    tracks = sp.album_tracks(spot_album_id)['items']
    if track_num < 1 or track_num > len(tracks):
        print(f"Track index must be between 1 and {len(tracks)}. Got {track_num}")
        return None

    track_uri = tracks[track_num - 1]['uri']

    play_track(track_uri, sp)

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

            play_track(track, sp)
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

    # I could also have an ncurses interface for playback

    sp = connect_to_spotify()
    # john_dohertys = Track("spotify:track:3XDCKy6Z5lC9SP37doE9S5", start="11", end="32")
    # loop_track(john_dohertys, sp)

    search_for_track("John Dohertys", sp)

if __name__ == '__main__':
    main()

