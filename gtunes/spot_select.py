import logging
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, ListView, Static, ListItem, Checkbox
from textual.containers import Horizontal
import gtunes.audio as audio
import gtunes.scrape as scrape
import threading
import queue

class SpotTrack(ListItem):
    def __init__(self, spot_data: audio.SpotTuneTrackData):
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
        self._sp = audio.connect_to_spotify()
        self._selected_item = None
        self._list_widget = None
        self._stop_event = threading.Event() # Signals thread termination
        
        self._done_with_startup = False
        self._done_with_startup_event = threading.Event() # Set 
        self._output = output

        self._scrape_data_queue = None
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
                    audio.spot_play_track(highlighted_child.spot_data.track_uri, self._sp, retries=0, log_fn=self.notify)
                else:
                    audio.spot_pause_track(highlighted_child.spot_data.track_uri, self._sp)

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
        while True:
            if self._stop_event.is_set():
                logging.debug("Stop event is set")
                break
            else:
                logging.debug("Stop event not set")
            scrape_data: scrape.ScrapeRecordingData = queue.get()
            if scrape_data is None:
                break

            spot_album_data = audio.spot_search_albums(scrape_data.album_name, self._sp, artist_name=scrape_data.artist_name)
            if not spot_album_data:
                continue

            spot_data = audio.SpotTuneTrackData(album_name=spot_album_data["name"], 
                                          track_number=scrape_data.track_number, 
                                          track_tunes=scrape_data.track_tunes,
                                          album_uri=spot_album_data["uri"],
                                          artist_name=scrape_data.artist_name)

            spot_track_data = audio.spot_get_nth_album_track(spot_data.album_uri, spot_data.track_number, self._sp)

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
        self._scrape_data_queue = queue.Queue()
        logging.debug("Starting scraping thread")
        self._scraping_thread = threading.Thread(target=scrape.scrape_recording_data,
                                        kwargs={
                                            "tune_name": self._tune_name,
                                            "data_queue": self._scrape_data_queue,
                                            "stop_event": self._stop_event})
        self._scraping_thread.start()

        # Start queue reader thread.
        logging.debug("Starting queue reader thread")
        self._queue_reader_thread = threading.Thread(target=self.read_tracks_from_queue, args=[self._scrape_data_queue])
        self._queue_reader_thread.start()


    async def on_unmount(self) -> None:
        logging.debug("Setting stop event")
        self._stop_event.set()
        if self._scraping_thread.is_alive():
            logging.debug("Joining scraping thread")
            self._scraping_thread.join(2)
        else:
            logging.debug("Scraping thread is not live")

        #logging.debug("Trying to send None to queue with timeout")
        #self._scrape_data_queue.put(None, timeout = 0.5)
        if self._queue_reader_thread.is_alive():
            logging.debug("Joining queue reader")
            self._queue_reader_thread.join(2)
        else:
            logging.debug("Queue thread is not live")

def select_spotify_track(tune_name: str) -> list:
    output = []
    app = SpotApp(tune_name, output)
    app.run()

    return output

if __name__ == "__main__":
    select_spotify_track()

