#!/usr/bin/env python3
# The frontend: command line interface for the app.

from gtunes import parse
from gtunes import scrape
from gtunes import db
from gtunes import audio
from dotenv import load_dotenv
from gtunes.util import timestamp_to_seconds
from gtunes.spot_select import select_spotify_track
import argparse
import csv
import os
import sys
import subprocess
import json
import urllib.request
import re
import questionary

# ================
# Tune subcommands
# ================

def _str_default(value):
    return value if value is not None else ""

def _get_val_from_dict(value_name, the_dict):
    """
    Args:
        value_name: the name of the value to retreive from the dictionary
        the_dict: dictionary to get value from
    Returns:
        Either the value, or None instead of falsy values. This helps with the database. 
    """
    val = the_dict[value_name]
    return val if val else None

def _edit_and_save_tune_interactively(tune: db.Tune):
    """
    Edits the input tune in-place, defaulting to the values already present in the tune.
    """
    tune_type_choices = [t.name for t in db.TuneType]
    tune_type_choices.append("")

    status_choices = [s.name for s in db.Status]
    status_choices.append("")

    responses = questionary.form(
        name = questionary.text("Name", default=_str_default(tune.name)),
        status = questionary.select("Status", choices=status_choices),
        tune_type = questionary.select("Type", choices=tune_type_choices, default=_str_default(tune.type)),
        key = questionary.text("Key", default=_str_default(tune.key)),
        comments = questionary.text("Comment", default=_str_default(tune.comments)),
    ).ask()

    tune.name = _get_val_from_dict("name", responses)
    tune.status = db.Status[_get_val_from_dict("status", responses)]
    tune.type = _get_val_from_dict("tune_type", responses)
    tune.key = _get_val_from_dict("key", responses)
    tune.comments = _get_val_from_dict("comments", responses)

    print(tune)

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

    recording_tune.start_time_secs = timestamp_to_seconds(input("Start time (MM:SS): "))
    recording_tune.end_time_secs = timestamp_to_seconds(input("End time (MM:SS): "))

    print("Saving tune data")
    recording_tune.save()

    return True

def tune_edit(args):
    ret = 0

    db.open_db()

    tune = db.select_tune(message="Select tune to edit")
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
    tune= db.select_tune("Choose a tune to get the abc of.")

    if not tune.abc:
        _add_first_abc_setting_to_tune(tune)
    else:
        print("Using stored abc setting")

    filename = tune.name.replace(" ", "-")

    _convert_abc_to_svg(tune.abc, filename)

    db.close_db()




def tune_spot(args):
    db.open_db()

    tune_name = None
    if args.name:
        tune_name = args.name
    else:
        tune = db.select_tune(message="Select tune to find on Spotify")
        if not tune:
            print("Must specify a tune in order to search for it on Spotify.")
        else:
            tune_name = tune.name

    
    if tune_name:
        output = select_spotify_track(tune_name) # Launch the interface to play and integrate spotify tracks

        sp = audio.connect_to_spotify()
        for i in range(len(output)):
            track_data: audio.SpotTuneTrackData = output[i]
            audio.spot_play_track(track_data.track_uri, sp)
            if not questionary.confirm(f"Save {track_data.track_name} off of {track_data.album_name} by {track_data.artist_name}?").ask():
                print("Skipping")
                continue

            recording = db.Recording.create(album=track_data.album_name,
                                            artist=track_data.artist_name,
                                            source=db.Source.SPOTIFY,
                                            url=track_data.track_uri)

            print(f"Track tunes: {track_data.track_tunes}")
            rec_tune = db.RecordingTune()
            rec_tune.tune = tune_name
            rec_tune.recording = recording
            rec_tune.start_time_secs = timestamp_to_seconds(questionary.text("Start time (MM:SS):").ask())
            rec_tune.end_time_secs = timestamp_to_seconds(questionary.text("End time (MM:SS):").ask())

    db.close_db()

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

    tune = db.select_tune("Choose tune to put on flashcard")

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
            tune = db.select_tune()
            if not tune:
                print("Must have existing tune to associate with recording.")
            else:
                start_time_seconds = timestamp_to_seconds(input("Start time (MM:SS): "))
                end_time_time_seconds = timestamp_to_seconds(input("End time (MM:SS): "))

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
    parser_spot.add_argument("--name", help="Name of the tune.", required=False)

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