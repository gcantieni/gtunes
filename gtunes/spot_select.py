from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, ListView, Static, ListItem, Checkbox
from textual.containers import Horizontal
from gtunes.audio import connect_to_spotify, spot_search_albums, spot_get_nth_album_track, \
    spot_play_track, spot_play_nth_album_track, spot_pause_track, SpotTuneTrackData
from gtunes.scrape import scrape_recording_data, ScrapeRecordingData
from gtunes.util import timestamp_to_seconds
import questionary
from gtunes import db
from time import sleep
from threading import Thread, Event
from queue import Queue

class SpotTrack(ListItem):
    def __init__(self, spot_data: SpotTuneTrackData):
        super().__init__()

        self.spot_data = spot_data

        self._checkbox = Checkbox("")
        self._track_info = Static(f"[b]{spot_data.track_name}[/b] by {spot_data.artist_name} on {spot_data.album_name}")
        self._horizontal_container = Horizontal(self._checkbox, self._track_info)
        self._is_playing = False

    def compose(self) -> ComposeResult:
        yield self._horizontal_container

    def on_mount(self) -> None:
        # Custom styling
        self._horizontal_container.styles.height = "auto"

    def should_save(self) -> bool:
        """
        Returns:
            True iff the SpotTrack checkbox is ticked
        """
        return self._checkbox.value
    
    def toggle_playback(self) -> bool:
        """
        Returns:
            True iff track is currently set to be playing
        """
        self._is_playing = not self._is_playing
        
        return self._is_playing

class SpotApp(App):
    """
    TUI to select spotify tracks to save to the database
    """
    BINDINGS = [("space", "play_track", "Play track"),
                ("s", "save_tracks", "Save tracks"),
                ("q", "quit", "Quit"),]

    CSS_PATH = "spot_select.css"  # Path to the external CSS file

    def __init__(self, tune_name: str, output: list):
        super().__init__()

        self._tune_name = tune_name
        self._sp = connect_to_spotify()
        self._selected_item = None
        self._list_widget = None
        self._stop_event = Event() # Signals thread termination
        self._output = output

        self._scraping_thread = None
        self._queue_reader_thread = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        self._list_widget = ListView()
        yield Header()
        yield Footer()
        yield self._list_widget

    # TODO: toggle play/paused with internal boolean is_playing
    # TODO: do this async so error can be displayed without blocking user input
    def action_play_track(self) -> None:
        if self._list_widget:
            highlighted_child = self._list_widget.highlighted_child
            if highlighted_child and isinstance(highlighted_child, SpotTrack):
                should_play = highlighted_child.toggle_playback()
                if should_play:
                    spot_play_track(highlighted_child.spot_data.track_uri, self._sp, retries=0, log_fn=self.notify)
                else:
                    spot_pause_track(highlighted_child.spot_data.track_uri, self._sp)

    def action_save_tracks(self) -> list:
        for spot_list_item in self._list_widget.children:
            if spot_list_item.should_save():
                self._output.append(spot_list_item.spot_data)

        self.exit(0)

    def add_track(self, track: SpotTrack):
        self._list_widget.append(track)
        self._list_widget.refresh()

    def read_tracks_from_queue(self, queue):
        """
        Reads from the queue of track data and use it to populate list of
        spotify tracks. This is intended to be run in its own thread.
        """
        while not self._stop_event.is_set():
            scrape_data: ScrapeRecordingData = queue.get()
            if scrape_data is None:
                break

            spot_album_data = spot_search_albums(scrape_data.album_name, self._sp, artist_name=scrape_data.artist_name)
            if not spot_album_data:
                continue

            spot_data = SpotTuneTrackData(album_name=spot_album_data["name"], 
                                          track_number=scrape_data.track_number, 
                                          track_tunes=scrape_data.track_tunes,
                                          album_uri=spot_album_data["uri"],
                                          artist_name=scrape_data.artist_name)

            spot_track_data = spot_get_nth_album_track(spot_data.album_uri, spot_data.track_number, self._sp)

            # Add track data
            spot_data.track_name = spot_track_data["name"]
            spot_data.track_uri = spot_track_data["uri"]

            try:
                self.call_from_thread(self.add_track,
                                      SpotTrack(spot_data))
            except RuntimeError as runtime_error:
                if "App is not running" in str(runtime_error):
                    break
                else:
                    raise runtime_error

    async def on_mount(self) -> None:
        # Ensure ListView items don't stretch
        self.query_one(ListView).styles.height = "auto"

        # Start background worker that fills the queue with albums data
        # corresponding to the tune in question.
        queue = Queue()
        self._scraping_thread = Thread(target=scrape_recording_data,
                                        kwargs={
                                            "tune_name": self._tune_name,
                                            "data_queue": queue,
                                            "stop_event": self._stop_event})

        # Start queue reader thread.
        self._queue_reader_thread = Thread(target=self.read_tracks_from_queue, args=[queue]).start()

    async def on_shutdown(self) -> None:
        self._stop_event.set()
        self._scraping_thread.join()
        self._queue_reader_thread.join()


def select_spotify_track(tune_name: str) -> list:
    output = []
    app = SpotApp(tune_name, output)
    app.run()

    return output

if __name__ == "__main__":
    select_spotify_track()

