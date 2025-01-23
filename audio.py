import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os
from time import sleep
import threading

stop_loop = False

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
        self.uri = uri
        self.start = time_to_ms(start) if start else start
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

def list_artist_albums():
    sp = connect_to_spotify()
    # example code from spotipy documentation
    # but with dallahan
    dallahan_uri = 'spotify:artist:1MfVe0OhbAVIhlXv5yrOUo'
    results = sp.artist_albums(dallahan_uri, album_type='album')
    albums = results['items']
    while results['next']:
        results = sp.next(results)
        albums.extend(results['items'])

    for album in albums:
        print(album['name'])

def play_track(track):
    sp = connect_to_spotify()
    sp.start_playback(uris=[track.uri], position_ms=track.start)


def listen_for_input():
    global stop_loop
    while True:
        user_input = input("Press 'q' to quit: ").strip().lower()
        if user_input == "q":
            stop_loop = True
            break

def loop_track(track):
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

def main():
    # TODO: streamling getting the uri
    # open spotify search for tune name
    # then take in the whole url from "copy as url" option and strip off the end uri
    # save it in the tune database for the future.

    # I could also have an ncurses interface for playback

    john_dohertys = Track("spotify:track:3XDCKy6Z5lC9SP37doE9S5", start="11", end="32")
    loop_track(john_dohertys)

if __name__ == '__main__':
    main()

