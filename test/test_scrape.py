import gtunes.scrape as scrape
import queue
from threading import Event, Thread

def test_scrape_recording_data():
    result = scrape.scrape_recording_data(tune_name="The Ashplant", limit=1)
    assert isinstance(result, list)
    assert len(result) == 1
    item = result[0]
    assert item is not None
    assert item.album_name is not None
    assert item.artist_name is not None
    assert item.track_number is not None
    assert item.track_tunes is not None
    assert item.tune_number is not None

def test_threaded_scrape_can_be_interrupted():
    """
    A basic test of the queue functionality
    """

    my_queue = queue.Queue()
    my_event = Event()
    my_thread = Thread(
        target=scrape.scrape_recording_data,
        kwargs={
            "tune_name": "The Ashplant",
            "data_queue": my_queue,
            "stop_event": my_event
        })
    my_thread.start()
    
    item: scrape.ScrapeRecordingData = my_queue.get()
    assert item is not None
    assert item.album_name is not None
    assert item.artist_name is not None
    assert item.track_number is not None
    assert item.track_tunes is not None
    assert item.tune_number is not None

    my_event.set()
    my_queue.get(timeout=5)

    my_thread.join()
    
