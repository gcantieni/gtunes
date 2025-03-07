#!/usr/bin/env python3

import requests
import queue
import threading
from dataclasses import dataclass
from bs4 import BeautifulSoup
import logging

debug=False
TUNE_DELIMITER = " / "

def print_debug(debug_str):
    global debug
    if debug:
        print(debug_str)

def query_the_sessions(tune_name):
    global debug
    ret = []
    split_name = [word.lower() for word in tune_name.split()]
    url = f"https://thesession.org/tunes/search?q={split_name.pop(0)}"

    for word in split_name:
        url += f"+{word}"

    response = requests.get(url)

    soup = BeautifulSoup(response.text, 'html.parser')

    tune_items = soup.find_all('li', class_='manifest-item')

    if len(tune_items) == 0:
        print_debug(f"Did not find any tunes to match tune name {tune_name}")

        return {"name": None, "id": None}

    print_debug(f"Found {len(tune_items)} tunes matching your query.")
    for tune_data in tune_items:
        # print(tune_data.prettify())

        id = tune_data.find("a-preview").get("data-tuneid")
        name_and_alt = tune_data.find_all('a')
        name = name_and_alt[0] if len(name_and_alt) == 1 else \
            f"{name_and_alt[0]} {name_and_alt[1]}"
        
        ret.append({"name" : name, "id": id})

    return ret

        

def get_abc(tune_id, should_print=False):
    url = f"https://thesession.org/tunes/{tune_id}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    divs = soup.find_all('div', class_='notes')

    return [div.text.strip() for div in divs]

def _get_tune_id(tune_name):
    tunes = query_the_sessions(tune_name)
    # TODO: if this doesn't find anything it actually returns "{'name': None, 'id': None}"
    if len(tunes) == 0:
        return None
    id = tunes[0]['id']

    return int(id)

def get_abc_by_name(name, interactive=False):
    return get_abc(_get_tune_id(name))

# some inherently brittle logic to extract the album data:
# the Albums are in an ordered list "manifest-inventory". each list item
# has an internal link, a-preview, pointing to the tunes of the track.
# This has an internal "data-tunid" which we can compare to our input tune_id to
# find the appropriate track. 
def find_track_number(recording_id, tune_id):
    print_debug(f"Finding track number for recording_id={recording_id} and tune_id={tune_id}")
    response = requests.get(f"https://thesession.org/recordings/{recording_id}")
    soup = BeautifulSoup(response.text, 'html.parser')

    track_number = None
    tune_number = None
    tracks = soup.find_all("li", class_="manifest-item")
    target_track = None
    for i, track in enumerate(tracks, 1):
        track_tunes = track.find_all("a-preview")
        for j, tt in enumerate(track_tunes, 1):
            if int(tt["data-tuneid"]) == tune_id:
                track_number = i
                tune_number = j
                target_track = track
                break

    set_string = ""
    if target_track:
        track_tune_links = target_track.find_all("a")
        for a in track_tune_links:
            set_string += a.text + TUNE_DELIMITER
        set_string = set_string[:-len(TUNE_DELIMITER)] # Remove the last delimiter


    return { "track_number": track_number, "tune_number": tune_number, "track_string": set_string }
    
@dataclass
class ScrapeRecordingData:
    album_name: str
    track_number: int
    tune_number: int
    track_tunes: str
    artist_name: str

def scrape_recording_data(tune_name: str = None, tune_id: str = None, limit: int = None, 
                          data_queue: queue.Queue = None, stop_event: threading.Event = None) -> queue.Queue | list:
    """
    For a given tune name or id (one required)
     - scrape the page of all recordings of that tune from the session
     - return all tune data gleaned TheSession
    
    Args:
        tune_name: name of the tune
        tune_id: TheSession id of the tune (more accurate, otherwise the first result
            from search will be used)
        limit: optionally limit the number
        data_queue: optionally return ScrapRecordingData to the input queue instead of
            returning it as a list at the end
        stop_event: optionally stop this function part way through if being run in a thread
    
    Returns:
        Either a list of ScrapeRecordingData, or None if a queue is being used.
    """
    logging.debug(f"tune_name={tune_name}, limit={limit}, data_queue={data_queue}, stop_event={stop_event}")

    if not tune_name and not tune_id:
        print("Must specify either tune name or tune id")
    
    if not tune_id:
        tune_id = _get_tune_id(tune_name)
    
    print(f"Scraping album data for tune {tune_name if tune_name else "with id " + tune_id}...")

    response = requests.get(f"https://thesession.org/tunes/{tune_id}/recordings")
    soup = BeautifulSoup(response.text, 'html.parser')

    # Each recording list
    recording_list_items = soup.find_all("li", class_="manifest-item")

    logging.debug(f"len(recording_list_items)={len(recording_list_items)}")

    max_items = len(recording_list_items) if not limit else min(len(recording_list_items), limit)
    output = []

    logging.debug(f"Limiting to max_items={max_items}")

    for i in range(max_items):
        if stop_event is not None:
            if stop_event.is_set():
                logging.debug("Stop event detected")
                break
            else:
                logging.debug("not stopped")

        li = recording_list_items[i]

        album_link = li.find("a", class_="manifest-item-title")

        name = album_link.text

        # the id is inside an href of the form: /recordings/3192?tune_id=3210
        href = album_link["href"]
        album_id = int(href.split("?")[0].split("/")[2])

        # the Artist is in the same list item under a span "bill-cost", perhaps
        # because this html was reused from some commircial template. each one is
        # a link
        artist_name = li.find("span", class_="bill-item-cost").find("a").text

        # Unfortunately, in order to find the track number we need to scrape the
        # album page itself. this could be solved by using irishtunes.info which
        # has the album data and track number on the same page.
        track_data = find_track_number(album_id, tune_id)

        entry = ScrapeRecordingData(album_name=name, 
                                    track_number=track_data["track_number"], 
                                    tune_number=track_data["tune_number"],
                                    track_tunes=track_data["track_string"],
                                    artist_name=artist_name)

        if data_queue:
            logging.debug("Putting entry to queue")
            data_queue.put(entry)
        else:
            output.append(entry)
    if data_queue:
        data_queue.put(None) # Tell the thread we're done.

    return output

def main():
    find_track_number(3613, 62)

if __name__ == '__main__':
    main()



