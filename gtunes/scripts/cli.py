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
import shelve
import csv
import os
import sys
import subprocess
import json
import urllib.request

CURSOR="gtn> "

def tui_wrapper(args): # args isn't used
    wrapper(tui)

def _edit_and_save_tune_interactively(tune):
    print(tune)
    help_menu = """h: help, n: name, k: key, t: type, a: status,
r: recordings, c: comment, o: search spotify, 
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
            _add_recording(tune=tune)
        elif opt == "o":
            save_data = _search_spotify_interactively(tune_name=tune.name)

            for rec_data in save_data:
                if not _add_recording(tune=tune, spot_id=rec_data["spot_id"]):
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

def _add_recording(tune=None, spot_id=None):
    rec = db.Recording()
    rec.tune = tune
    rec.spot_id = spot_id
    print(rec)
    help_menu = """h: help, o: spotify_id, p: path, b: tune beginning time, e: tune ending time,
n: next (if in bulk import), s: save, q: quit"""

    print(help_menu)
    while True:
        opt = input(CURSOR)
        if opt == "h":
            print(help_menu)
        elif opt == "o":
            rec.spot_id = input("Spotify ID: ")
        elif opt == "b":
            rec.start_time_secs = int(input("Begin time: "))
        elif opt == "e":
            rec.end_time_secs = int(input("End time: "))
        elif opt == "s":
            print("Saving tune to the database")
            rec.save()
            break
        elif opt == "n":
            print("Skipping this recording")
            break
        elif opt == "q":
            return False
    return True


def edit(args):
    if args.n is not None:
        print("Non-interactive edit has not been implemented yet.")
    if not args.n:
        db.init_db()
        tune = db.select_tune(header="Select tune to edit")
        _edit_and_save_tune_interactively(tune)
        db.close_db()
    return 0

def add(args):
    if args.n is not None:
        print("Non-interactive add is not currently supported.")
        return 0
    
    db.init_db()

    this_tune = db.GTune()
    _edit_and_save_tune_interactively(this_tune)

    db.close_db()

def list(args):
    db.init_db()
    sel = db.GTune.select()
    print(f"Listing tunes.\nConditions:{"" if not args.name else " Name=" + args.name}\
{"" if not args.type else " Type=" + args.type}{"" if not args.status else " Status=" + args.status}")

    if args.name is not None:
        sel = sel.where(db.GTune.name == args.name)
    if args.type:
        sel = sel.where(db.GTune.type == args.type)
    if args.status:
        sel = sel.where(db.GTune.status == args.status)

    for tune in sel:
        print(tune)
    

def parse_(args):
    parser = parse.TuneListParser(args.infile)
    tunes = parser.parse()

    if args.outfile:
        path, ext = os.path.splitext(args.outfile)

        if ext == '.csv':
            with open(args.outfile, 'w') as csvfile:
                tunewriter = csv.writer(csvfile)
                print("Writing tunes to CSV file")
                tunewriter.writerow(["id", "name", "type", "status", "key", "comments"])
                for name, tune in tunes.items():
                    comments_str = ""
                    for c in tune.comments:
                        comments_str += c + "\n"
                    tunewriter.writerow([tune.id, tune.name, tune.type, tune.status, tune.key, comments_str])
        else: 
            with shelve.open(args.outfile) as shelf:
                for name in tunes:
                    shelf[name] = tunes[name]
        
            print(f"Saved {len(tunes)} tunes to {args.outfile}.db")
    else:
        parser.print_tunes()

def scrape_tunes(args):
    tune_abc = scrape.get_abc_by_name(args.tune_name)
    for abc in tune_abc:
        print(abc + "\n")

# Find recordings for a particular tune and TODO save them to the tune database.
def recs(args):
    scrape.scrape_recording_data(tune_name=args.tune)

def _search_spotify_interactively(tune_ts_id=None, tune_name=None):
    sp = audio.connect_to_spotify()
    scraped_albums = None
    if tune_ts_id is not None:
        queue = scrape.scrape_recording_data_async(tune_id=tune_ts_id)
    elif tune_name is not None:
        queue = scrape.scrape_recording_data_async(tune_name=tune_name, limit=15)
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
                save_data = scrape_data
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
    return saved_track_data

def spot(args):
    _search_spotify_interactively(tune_name=args.name)

def open_file(filepath):
    if sys.platform == "win32":  # Windows
        os.startfile(filepath)
    elif sys.platform == "darwin":  # macOS
        subprocess.run(["open", filepath])
    else:  # Linux
        subprocess.run(["xdg-open", filepath])

# Scrapes the session for abc, and adds it to the tune with the specified name.
def add_first_abc_setting_to_tune(tune):
    print(f"Searching the session for abc for {tune.name}...")
    abc_settings = scrape.get_abc_by_name(tune.name)

    tune.abc = abc_settings[0]

def convert_abc_to_svg(abc_string, output_file_name):
    with open("tmp.abc", "w+") as tmpfile:
        tmpfile.write(abc_string)

    # -g means svg, one tune per file
    subprocess.run(["abcm2ps", "-g", "tmp.abc", "-O", output_file_name])

def abc(args):
    db.init_db()
    tune = db.select_tune("Choose a tune to get the abc of.")

    if not tune.abc:
        add_first_abc_setting_to_tune(tune)
    else:
        print("Using stored abc setting")

    filename = tune.name.replace(" ", "-")

    convert_abc_to_svg(tune.abc, filename)

    db.close_db()

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
def remove_title_from_abc(abc_string):
    out_str = ""
    for line in abc_string:
        if line[:1] == "T:":
            print("Removing title")
        else:
            out_str = out_str.join(line)
    
    return out_str

def flash(args):
    db.init_db()

    tune = db.select_tune("Choose tune to put on flashcard")

    if not tune.abc:
        add_first_abc_setting_to_tune(tune)
    else:
        print("Using stored abc for tune.")

    tune_name_for_file = tune.name.replace(" ", "-")
    
    # Remove the name for the abc so that the flashcard doesn't give away the tune name.
    abc = remove_title_from_abc(tune.abc)

    convert_abc_to_svg(abc, tune_name_for_file)

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


def main():
    parser = argparse.ArgumentParser(description="Add and manipulate traditional tunes.")

    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # Create the parent parser with common arguments
    parent_parser = argparse.ArgumentParser(add_help=False)  # Don't add help to avoid duplication
    parent_parser.add_argument("-l", type=str, default="tunes", dest="list_location", help="List location")

    # Create parsers for subcommands

    edit_add_parent_parser = argparse.ArgumentParser(add_help=False)
    edit_add_parent_parser.add_argument("-n", type=str, help="Name of the tune. If this is not set, all other arguments will be ignored and the tune will be resolved interactively.")
    edit_add_parent_parser.add_argument("-t", type=str, dest="type", help="Type of tune (jig, reel, etc.)")
    edit_add_parent_parser.add_argument("-r", type=str, dest="recording", help="Either spotify id or path to the recording, specified as ")
    edit_add_parent_parser.add_argument("-k", type=str, dest="key", help="Key of the tune")
    edit_add_parent_parser.add_argument("-s", type=int, dest="status", help="Status of tune. How well the tune is known, int from 1-5.")
    edit_add_parent_parser.add_argument("-a", type=str, dest="abc", help="ABC")
    edit_add_parent_parser.add_argument("-c", type=str, dest="comment", help="Comment(s)")

    parser_tui = subparsers.add_parser("tui", help="Initiate an interactive version of the app.")
    parser_tui.set_defaults(func=tui_wrapper)

    parser_add = subparsers.add_parser("add", parents=[edit_add_parent_parser], help="Add a tune")
    parser_add.set_defaults(func=add)

    parser_abc = subparsers.add_parser("abc", parents=[edit_add_parent_parser], help="Add a tune")
    parser_abc.set_defaults(func=abc)
    parser_abc.add_argument("-f", action="store_true", help="Use the first abc without confirming")

    parser_edit = subparsers.add_parser("edit", parents=[edit_add_parent_parser], help="Edit a tune")
    parser_edit.set_defaults(func=edit)

    parser_flash = subparsers.add_parser("flash", help="Make tune flashcards")
    parser_flash.set_defaults(func=flash)

    parser_list = subparsers.add_parser("ls", parents=[parent_parser], help="List tunes")
    parser_list.set_defaults(func=list)
    parser_list.add_argument("-n", dest="name", help="Name of tune")
    parser_list.add_argument("-t", dest="type", help="Type of tune (jig, reel, etc.)")
    parser_list.add_argument("-s", dest="status", help="Status of tune. How well the tune is known, int from 1-5.")

    parser_parse = subparsers.add_parser("parse", parents=[parent_parser], help="Add list")
    parser_parse.set_defaults(func=parse_)
    parser_parse.add_argument("infile", help="The path to the tune list to parse")
    parser_parse.add_argument("-o", dest="outfile", help="The name of the output file (db will be appended)")

    parser_scrape = subparsers.add_parser("scrape")
    parser_scrape.set_defaults(func=scrape_tunes)
    parser_scrape.add_argument("tune_name", help="Name of tune to find abc settings of.")

    parser_recordings = subparsers.add_parser("recs", help="Find recordings of a tune and save your favorites.")
    parser_recordings.set_defaults(func=recs)
    parser_recordings.add_argument("tune", help="Name fo the tune to find recordings of.")

    parser_spot = subparsers.add_parser("spot", help="Scrape albums of thesession.org by name and search for them on spotify.")
    parser_spot.set_defaults(func=spot)
    parser_spot.add_argument("name", help="Name of the tune.")

    args = parser.parse_args()
    if args.command:
        args.func(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    sys.exit(main())