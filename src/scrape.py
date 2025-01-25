#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup

debug=False

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

def get_abc_by_name(name, interactive=False):
    tunes = query_the_sessions(name)
    if len(tunes) == 0:
        return None
    return get_abc(tunes[0]['id'])

# TODO: get recordings for tune
# go to thesession.org/tune/<tuneid>/recording
# for each of those recordings, go to
# thesession.org/recordings/<recordingid>
# find <ol class="manifest-inventory">
# iterate through the sub <li> attributes
# find <a-preview data-tune-id="<tuneid>">
# return the recording name, artist, and track number
# this can then be used to find the album on e.g. Spotify
# and play the corresponding piece.
def find_track_number(recording_id, tune_id):
    response = requests.get(f"https://thesession.org/recordings/{recording_id}")
    soup = BeautifulSoup(response.text, 'html.parser')

    track_number = None
    tune_number = None
    tracks = soup.find_all("li", class_="manifest-item")
    for i, track in enumerate(tracks, 1):
        track_tunes = track.find_all("a-preview")
        for j, tt in enumerate(track_tunes, 1):
            if int(tt["data-tuneid"]) == tune_id:
                print(f"Found tune track {i}. It is number {j} in the set.")
                track_number = i
                tune_number = j
    return track_number, tune_number

def scrape_recordings(tune_id):
    response = requests.get(f"https://thesession.org/tunes/{tune_id}/recordings")
    soup = BeautifulSoup(response.text, 'html.parser')

    recording_links = soup.find_all("a", class_="manifest-item-title")
    
    output = {}
    for li in recording_links:
        name = li.text
        href = li["href"]
        # e.g. /recordings/3192?tune_id=3210
        rec_id = href.split("?")[0].split("/")[2]

        track_number, tune_number = find_track_number(rec_id, tune_id)

        output[name] = {"track_number": track_number, "tune_number": tune_number}

    print(output)

def main():
    # abc_settings = get_abc_by_name("the lark in the morning")
    # for setting in abc_settings:
    #     print(setting + "\n")
    scrape_recordings(3210)
    # find_track_number(7614, 3210)

if __name__ == '__main__':
    main()



