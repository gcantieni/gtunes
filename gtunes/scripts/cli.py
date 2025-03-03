#!/usr/bin/env python3
# The frontend: command line interface for the app.

from gtunes import parse
from gtunes import scrape
from gtunes import db
from gtunes import audio
from dotenv import load_dotenv
from gtunes.tui import tui
from curses import wrapper
import argparse
import csv
import os
import sys
import subprocess
import json
import urllib.request
import re
import spotipy

CURSOR="gtn> "

# ===============
# General helpers
# ===============

# Accept timestamps in the format 1:30 where 1 is the minutes and 30 is the seconds
def _timestamp_to_seconds(timestamp):
    sum(x * int(t) for x, t in zip([60, 1], timestamp.split(":")))

# ================
# Tune subcommands
# ================

def _edit_and_save_tune_interactively(tune):
    print(tune)
    help_menu = """h: help, n: name, k: key, t: type, a: status,
r: add recording, c: comment, o: search spotify, 
p: print, s: save, q: quit"""
    print(help_menu)
    while True:
        opt = input(CURSOR)
        if opt == "n":
            tune.name = input("Name: ")
        elif opt == "k":
            tune.key = input("Key: ")
        elif opt == "t":
            tune.type = input("Type: ")
        elif opt == "c":
            tune.comments = input("Comment: ")
        elif opt == "a":
            tune.status = input("Status: ")
        elif opt == "r":
            _add_recording_to_tune_interactively(None, tune)
        elif opt == "o":
            save_data = _search_spotify_interactively(tune_name=tune.name)

            for rec_data in save_data:
                recording = db.Recording.create(url=rec_data["spot_id"], name=rec_data["name"], artist=rec_data["artist"])
                if not _add_recording_to_tune_interactively(recording, tune):
                    print("Done adding recordings")
                    break

        elif opt == "p":
            print(tune)
        elif opt == "h":
            print(help_menu)
        elif opt == "q":
            should_save = False
            print("Bye")
            break
        elif opt == "s":
            print(f"Saving {tune.name}")
            tune.save()
            break

def _add_recording_to_tune_interactively(recording: db.Recording, tune: db.Tune):
    """
    Associates a tune with a recording, and allows the user to specify a start and
    end time of that tune within the recording.

    Should be called with the database already open.
    
    Args:
        recording: If None, prompts user for interactive search
        tune: The tune to associate the recording with

    Returns:
        True on success and False otherwise
    """
    if not recording:
        rec, _ = db.select_recording(header="Associate this tune with a recording")
        if not rec:
            print("No recording selected. Exiting.")
            return False

    print(f"Recording: {rec}")

    recording_tune = db.RecordingTune(recording=recording, tune=tune)

    recording_tune.start_time_secs = _timestamp_to_seconds(input("Start time (MM:SS): "))
    recording_tune.end_time_secs = _timestamp_to_seconds(input("End time (MM:SS): "))

    print("Saving tune data")
    recording_tune.save()

    return True

def tune_edit(args):
    ret = 0
    db.open_db()
    tune, _ = db.select_tune(header="Select tune to edit")
    if not tune:
        print("Tune not found.")
        ret = 1
    else:
        _edit_and_save_tune_interactively(tune)
    db.close_db()
    return ret

def tune_add(args):
    db.open_db()

    this_tune = db.Tune()
    # Defaults
    this_tune.status = 1

    _edit_and_save_tune_interactively(this_tune)

    db.close_db()

def tune_list(args):
    db.open_db()
    sel = db.Tune.select()
    print(f"Listing tunes.\nConditions:{"" if not args.name else " Name=" + args.name}\
{"" if not args.type else " Type=" + args.type}{"" if not args.status else " Status=" + args.status}")

    if args.name is not None:
        sel = sel.where(db.Tune.name == args.name)
    if args.type:
        sel = sel.where(db.Tune.type == args.type)
    if args.status:
        sel = sel.where(db.Tune.status == args.status)

    for tune in sel:
        print(tune)

def tune_abc(args):
    db.open_db()
    tune, _ = db.select_tune("Choose a tune to get the abc of.")

    if not tune.abc:
        _add_first_abc_setting_to_tune(tune)
    else:
        print("Using stored abc setting")

    filename = tune.name.replace(" ", "-")

    _convert_abc_to_svg(tune.abc, filename)

    db.close_db()

def _search_spotify_interactively(tune_ts_id: str = None, tune_name: str = None, existing_tune : db.Tune = None):
    sp = audio.connect_to_spotify()

    if existing_tune is not None:
        if existing_tune.ts_id:
            tune_ts_id = existing_tune.ts_id
        elif existing_tune.name:
            tune_name = existing_tune.name

    if tune_ts_id is not None:
        queue = scrape.scrape_recording_data_async(tune_id=tune_ts_id)
    elif tune_name is not None:
        queue = scrape.scrape_recording_data_async(tune_name=tune_name)
    else:
        print("Error: Supplied neither tune name not thesession id")
        return []

    saved_track_data = []
    while True:
        scrape_data = queue.get()
        if scrape_data is None:
            break
        album_name = scrape_data["album_name"]
        alb = audio.spot_search_albums(album_name, sp, artist_name=scrape_data['artist_name'])
        if alb:
            print(f"Album: {album_name}, track tunes: {scrape_data["track_tunes"]}")
            track_data = audio.spot_play_nth_album_track(alb['id'], scrape_data['track_number'], sp)

            if not track_data:
                print(f"No track data for album {album_name}, skipping")
                continue

            print(f"Track name: {track_data['name']}")

            user_input = input("s: save, n: next q: quit > ")
            if user_input == "s":
                # TODO: see if we already have a recording matching this one
                # where name and artist are the same
                #if db.Recording.select().where(db.Recording.name == scrape_data["name"])
                start_time_seconds = _timestamp_to_seconds(input("Start time (MM:SS): "))
                end_time_time_seconds = _timestamp_to_seconds(input("End time (MM:SS): "))
                save_data = scrape_data
                save_data = track_data["name"]
                save_data["start_time_seconds"] = start_time_seconds
                save_data["end_time_seconds"]  = end_time_time_seconds
                save_data["album_name"] = album_name
                save_data["spot_album_id"] = alb['id']
                save_data["spot_id"] = track_data["id"]
                saved_track_data.append(save_data)
            elif user_input == "q":
                print("bye")
                break
            elif user_input == "n":
                continue
    print("Done playing albums.")
    if saved_track_data:
        print(f"Save data: {saved_track_data}")
        db.open_db()

        for recording in saved_track_data:
            print(f"Saving new recording {recording}")
            audio.play_track(recording["spot_id"])
            if input("Confirm? (y/n) "):
                db.Recording.create(name=saved_track_data["name"], url=saved_track_data["spot_id"], source=db.Source.SPOTIFY)
                print("Saved to recording database")
            else:
                print("Not saving this recording")
                continue
        db.close_db()


    return saved_track_data

def tune_spot(args):
    _search_spotify_interactively(tune_name=args.name)

# Scrapes the session for abc, and adds it to the tune with the specified name.
def _add_first_abc_setting_to_tune(tune):
    print(f"Searching the session for abc for {tune.name}...")
    abc_settings = scrape.get_abc_by_name(tune.name)

    tune.abc = abc_settings[0]

def _convert_abc_to_svg(abc_string, output_file_name):
    tmp_name = "tmp.abc"
    with open(tmp_name, "w+") as tmpfile:
        tmpfile.write(abc_string)

    # -g means svg, one tune per file
    subprocess.run(["abcm2ps", "-g", tmp_name, "-O", output_file_name])

def _ac_request(action, **params):
    return {'action': action, 'params': params, 'version': 6}

def _ac_invoke(action, **params):
    requestJson = json.dumps(_ac_request(action, **params)).encode('utf-8')
    response = json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8765', requestJson)))
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] is not None:
        raise Exception(response['error'])
    return response['result']

# Returns the abc_string but with no title field
def _remove_title_from_abc(abc_string):
    out_str = ""
    for line in abc_string.split("\n"):
        if re.match(r"^T:.*", line):
            print(f"Skipping line with title in it: {line}")
        else:
            out_str += line + "\n"
    
    return out_str

def tune_flash(args):
    db.open_db()

    tune, _ = db.select_tune("Choose tune to put on flashcard")

    if not tune:
        print("No tune selected.")
        return 1

    if not tune.abc:
        _add_first_abc_setting_to_tune(tune)
    else:
        print("Using stored abc for tune.")

    tune_name_for_file = tune.name.replace(" ", "-")
    
    # Remove the name for the abc so that the flashcard doesn't give away the tune name.
    _convert_abc_to_svg(_remove_title_from_abc(tune.abc), tune_name_for_file)

    file_name = tune_name_for_file + "001.svg" # For some reason abcm2svg appends "001" to the filename
    file_path = os.path.abspath(file_name)

    load_dotenv()
    deck_name = os.getenv("GTUNES_ANKI_DECK", "GTunes")
    _ac_invoke('createDeck', deck=deck_name) # This won't do anything if deck was already created earlier

    _ac_invoke("addNote", note={
        "deckName": deck_name,
        "modelName": "Basic",
        "fields": {
            "Front": tune.name,
            "Back": "",
        },
        "picture": [{
            "path": file_path,
            "filename": file_name,
            "fields": [
                "Back"
            ]
        }]
    })

    if not tune.status or tune.status <= 2:
        should_bump = input("Bump tune status to 3 now that it's in the flashcard deck? (y/n) ")
        if should_bump == "y":
            print("Tune acquired!")
            tune.status = 3

    db.close_db()
    
# =============
# Parse command
# =============

def parse_(args):
    parser = parse.TuneListParser(args.infile)
    parser.parse()
    parser.print_tunes()

# ==============
# Export command
# ==============

def export(args):
    if args.c:
        output_file_name = "gtunes.csv"
        print(f"Writing tunes to CSV file {output_file_name}")

        with open(output_file_name, 'w') as csvfile:
            tunewriter = csv.writer(csvfile)
            db.open_db()
            tunewriter.writerow(["id", "name", "type", "status", "key", "comments"])

            for tune in db.Tune.select():
                tunewriter.writerow([tune.id, tune.name, tune.type, tune.status, tune.key, tune.comments])
            
            db.close_db()
    else:
        print("Error: no export option specified")

# ===========
# Set command
# ===========

def set_add(args):
    pass

# =============
# Flash command
# =============

def rec_add(args):
    """
    Add a recording to the tune database.
    After adding, the user will be prompted if they want to associate it with
    an existing tune.

    Args:
        args.url: Either a filepath, a Spotify URL, or a Youtube URL
    """
    ret = 0
    load_dotenv()
    data_dir = os.getenv("GTUNES_DATA_DIR", os.path.join("gtunes", "data"))
    # TODO: implement local storage
    recs_dir = os.path.join(data_dir, "recs")
    db.open_db()
    this_rec = None
    # https://open.spotify.com/track/3dEbGOSpPkqa5p2Jrx9fkS?si=ec31a1a68cb3489e
    if re.match(r"^https://open.spotify.com/track.*", args.url):
        print("Detected spotify")

        sp = audio.connect_to_spotify()
        track_data = sp.track(args.url)
        artist = track_data["artists"][0]["name"]
        album = track_data["album"]["name"]
        name = track_data["name"]
        print(f"Found Spotify track {name} off album {album} by {artist}.")

        existing_rec = db.Recording.select().where(db.Recording.url == args.url).get_or_none()
        if existing_rec:
            print("Already have this recording in the database:")
            print(existing_rec)
        else:
            this_rec = db.Recording(name=name, url=args.url, source=db.Source.SPOTIFY, album=album, artist=artist)

    # https://www.youtube.com/watch?v=zHqC__xzSkI
    elif re.match(r"^https://www.youtube.com.*", args.url):
        print("Detected YouTube")
        id = args.url.split("v=")[1].split("&")[0]
        print("ID: " + id)
    else:
        print("Interpreting as file path")
        if not os.path.exists(args.url):
            print(f"Error: path '{args.url}' doesn't exist")
            ret = 1
        else:
            pass

    if this_rec:
        print("Saving recording")
        this_rec.save()

        y_or_n = input("Add existing tune to this recording? ")

        if y_or_n == "y":
            tune, _ = db.select_tune()
            if not tune:
                print("Must have existing tune to associate with recording.")
            else:
                start_time_seconds = _timestamp_to_seconds(input("Start time (MM:SS): "))
                end_time_time_seconds = _timestamp_to_seconds(input("End time (MM:SS): "))

                db.RecordingTune.create(tune=tune, recording=this_rec,
                                        start_time_secs=start_time_seconds, end_time_secs=end_time_time_seconds)
                
                print(f"Tune {tune} now associated with {this_rec}. Proceeding...")

        print("Done saving recording")

    db.close_db()
    return ret

def rec_ls(args):
    db.open_db()
    sel = db.Recording.select()
    print("Listing recordings.")

    for recording in sel:
        print(recording)
    
    db.close_db()


def main():
    parser = argparse.ArgumentParser(description="Add and manipulate traditional tunes.")

    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # Create the parent parser with common arguments
    parent_parser = argparse.ArgumentParser(add_help=False)  # Don't add help to avoid duplication
    parent_parser.add_argument("-l", type=str, default="tunes", dest="list_location", help="List location")

    # Create parsers for subcommands

    # Tune subparser
    parser_tune = subparsers.add_parser("tune", help="Manage tunes")
    subparser_tune = parser_tune.add_subparsers(required=True)

    parser_tune_add = subparser_tune.add_parser("add", help="Add a tune")
    parser_tune_add.set_defaults(func=tune_add)

    parser_tune_list = subparser_tune.add_parser("ls", parents=[parent_parser], help="List tunes")
    parser_tune_list.set_defaults(func=tune_list)
    parser_tune_list.add_argument("-n", dest="name", help="Name of tune")
    parser_tune_list.add_argument("-t", dest="type", help="Type of tune (jig, reel, etc.)")
    parser_tune_list.add_argument("-s", dest="status", help="Status of tune. How well the tune is known, int from 1-5.")

    parser_tune_edit = subparser_tune.add_parser("edit", help="Edit a tune")
    parser_tune_edit.set_defaults(func=tune_edit)

    parser_spot = subparser_tune.add_parser("spot", help="Scrape albums of thesession.org by name and search for them on spotify.")
    parser_spot.set_defaults(func=tune_spot)
    parser_spot.add_argument("name", help="Name of the tune.")

    parser_flash = subparser_tune.add_parser("flash", help="Make tune flashcards")
    parser_flash.set_defaults(func=tune_flash)

    parser_abc = subparser_tune.add_parser("abc", help="Find and save abc notation for a tune")
    parser_abc.set_defaults(func=tune_abc)
    parser_abc.add_argument("-f", action="store_true", help="Use the first abc without confirming")


    # Rec subparser
    parser_rec = subparsers.add_parser("rec", help="Manage recordings")
    rec_subparser = parser_rec.add_subparsers(required=True)

    parser_rec_add = rec_subparser.add_parser("add", help="Add new recording")
    parser_rec_add.add_argument("url", help="File, Spotify, or YouTube url of the recording")
    parser_rec_add.set_defaults(func=rec_add)

    parser_rec_ls = rec_subparser.add_parser("ls", help="List recordings")
    parser_rec_ls.set_defaults(func=rec_ls)

    # Set subparser
    parser_set = subparsers.add_parser("set", help="Manage sets of tunes")
    subparser_set = parser_set.add_subparsers(required=True)
    parser_set_add = subparser_set.add_parser("add", help="Add a set of tunes. composed of tunes in your tune database")
    parser_set_add.set_defaults(func=set_add)

    # Parse subparser
    parser_parse = subparsers.add_parser("parse", parents=[parent_parser], help="Add list")
    parser_parse.set_defaults(func=parse_)
    parser_parse.add_argument("infile", help="The path to the tune list to parse")
    parser_parse.add_argument("-o", dest="outfile", help="The name of the output file (db will be appended)")

    # Export subparser
    parser_export = subparsers.add_parser("export", help="Export tune database to different formats.")
    parser_export.set_defaults(func=export)
    parser_export.add_argument("-c", help="Export to csv", action="store_true")

    args = parser.parse_args()
    if args.command:
        args.func(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    sys.exit(main())