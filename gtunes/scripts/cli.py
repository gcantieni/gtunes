#!/usr/bin/env python3
# The frontend: command line interface for the app.

import enum
import typing
import peewee
from gtunes import parse
from gtunes import scrape
from gtunes import db
from gtunes import audio
from gtunes import util
from gtunes import spot_select
import dotenv
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

EnumClass = typing.TypeVar('E', bound=enum.Enum)

def _select_from_enum_values(prompt: str, enum_class: typing.Type[EnumClass], default_val: int, return_as_value : bool = False) -> int | None:
    enum_names = [enum_val.name for enum_val in enum_class]
    enum_names.insert(0, "")

    # Convert default_val to a string of type specified by enum class 
    default_str = enum_class(default_val).name if default_val else ""

    selected_name = questionary.select(prompt, choices=enum_names, default=default_str).ask()

    if not return_as_value:
        return selected_name

    if selected_name is not None:
        selected_value = enum_class[selected_name].value
    else:
        selected_value = None

    return selected_value

def _edit_and_save_tune_interactively(tune: db.Tune):
    """
    Edits the input tune in-place, defaulting to the values already present in the tune.
    """

    tune.name = questionary.text("Name", default=_str_default(tune.name)).ask()

    should_init_from_session = questionary.confirm("Initialize from TheSession.org?").ask()
    if should_init_from_session:
        print("Scraping tune data from TheSession.org...")
        tune_data = scrape.get_tune_data(tune.name)
        if tune_data is not None:
            tune.name = tune_data.tune_name
            tune.abc = tune_data.tune_abc
            tune.key = tune_data.tune_key
            tune.ts_id = tune_data.ts_id
            print(f"Loaded tune data: Name: {tune.name} Key: {tune.key}")
            print(tune.abc[0])
            tune.status = _select_from_enum_values("Status", db.Status, tune.status, return_as_value=True)
            tune.comments = questionary.text("Comment", default=_str_default(tune.comments)).ask()
        else:
            print("Failed to find tune. Must manually add/edit.")
    else:
        tune.status = _select_from_enum_values("Status", db.Status, tune.status, return_as_value=True)
        tune.type = _select_from_enum_values("Type", db.TuneType, tune.type)
        tune.key = questionary.text("Key", default=_str_default(tune.key)).ask()
        tune.comments = questionary.text("Comment", default=_str_default(tune.comments)).ask()

    should_save = questionary.confirm(f"Save tune: {tune}").ask()
    if should_save:
        tune.save()
        print(f"Saved tune {tune}")
        should_add_rec = questionary.confirm(f"Add recording associated with this tune?").ask()
        if should_add_rec:
            rec_exists = questionary.confirm("Recording exists?").ask()
            if rec_exists:
                _add_recording_to_tune_interactively(None, tune)
            else:
                rec_url = questionary.text("Enter url of recording").ask()
                _rec_add(rec_url)
    else:
        print("Not saving tune.")

def _add_recording_to_tune_interactively(rec: db.Recording | None, tune: db.Tune | None) -> bool:
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
    if not rec:
        rec = db.select_recording("Associate this tune with a recording")
        if not rec:
            print("No recording selected. Exiting.")
            return False

    print(f"Recording: {rec}")

    if not tune:
        tune = db.select_tune("Select tune to link")
        if not tune:
            print("No tune selected")
            return False

    recording_tune = db.RecordingTune(recording=rec, tune=tune)

    recording_tune.start_time_secs = util.timestamp_to_seconds(questionary.text("Start time (MM:SS)").ask())
    recording_tune.end_time_secs = util.timestamp_to_seconds(questionary.text("End time (MM:SS)").ask())

    print("Saving tune data")
    recording_tune.save()

    return True

def tune_add(args):
    db.open_db()

    this_tune = db.Tune()

    if args.name or args.ts_id:
        if args.name:
            this_tune.name = args.name
        if args.type:
            this_tune.type = db.TuneType(args.type).value
        if args.status:
            this_tune.status = db.Status(args.status).value
        if args.ts_id:
            this_tune.ts_id = args.td_id
        if args.comments:
            this_tune.comments = args.comments
        if args.from_:
            this_tune.from_ = args.from_
    else:
        _edit_and_save_tune_interactively(this_tune)

    db.close_db()

def tune_edit(args):
    ret = 0

    db.open_db()

    this_tune = None
    if args.name:
        this_tune = db.Tune.select().where(db.Tune.name == args.name).get_or_none()
    else:
        this_tune = db.select_tune(message="Select tune to edit")

    if not this_tune:
        print("Tune not found.")
        db.close_db()
        return 1
    
    if args.type or args.status or args.ts_id or args.comments or args.from_ or args.new_name:
        if args.new_name:
            this_tune.name = args.new_name
        if args.type:
            this_tune.type = db.TuneType(args.type).value
        if args.status:
            this_tune.status = db.Status(args.status).value
        if args.ts_id:
            this_tune.ts_id = args.td_id
        if args.comments:
            this_tune.comments = args.comments
        if args.from_:
            this_tune.from_ = args.from_
    else:
        _edit_and_save_tune_interactively(this_tune)

    db.close_db()

    return 0

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
    tune: db.Tune | None = None
    if args.name:
        tune_name = args.name
    else:
        tune = db.select_tune(message="Select tune to find on Spotify")
        if not tune:
            print("Must specify a tune in order to search for it on Spotify.")
        else:
            tune_name = tune.name

    
    if tune_name:
        output = spot_select.select_spotify_track(tune_name) # Launch the interface to play and integrate spotify tracks

        sp = audio.connect_to_spotify()
        for i in range(len(output)):
            track_data: audio.SpotTuneTrackData = output[i]
            audio.spot_play_track(track_data.track_uri, sp)
            if not questionary.confirm(f"Save {track_data.track_name} off of {track_data.album_name} by {track_data.artist_name}?").ask():
                print("Skipping")
                continue

            recording = db.Recording.create(name=track_data.track_name,
                                            album=track_data.album_name,
                                            artist=track_data.artist_name,
                                            source=db.RecordingSource.SPOTIFY.value,
                                            url=track_data.track_uri)

            # TODO: associate with a tune matching name or prompt to make new tune
            if tune:
                print(f"Associating with tune {tune}")
                print("Selecting start and end time:")
                print(f"Track tunes: {track_data.track_tunes}")
                rec_tune = db.RecordingTune()
                rec_tune.tune = tune
                rec_tune.recording = recording
                
                rec_tune.start_time_secs = util.timestamp_to_seconds(questionary.text("Start time (MM:SS):").ask())
                rec_tune.end_time_secs = util.timestamp_to_seconds(questionary.text("End time (MM:SS):").ask())
                
                print("Saving tune-recording association")
                rec_tune.save()

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
        db.close_db()
        return 1

    if not tune.abc:
        _add_first_abc_setting_to_tune(tune)
    else:
        print("Using stored abc for tune.")

    tune_name_for_file = tune.name.replace(" ", "-")
    
    # Remove the name for the abc so that the flashcard doesn't give away the tune name.
    # TODO: remove the tmp file
    _convert_abc_to_svg(_remove_title_from_abc(tune.abc), tune_name_for_file)

    file_name = tune_name_for_file + "001.svg" # For some reason abcm2svg appends "001" to the filename
    file_path = os.path.abspath(file_name)

    dotenv.load_dotenv()
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
        should_bump = questionary.confirm(
            f"Bump tune status to {db.Status(3).name} now that it's in the flashcard deck?")
        if should_bump:
            print("Tune acquired!")
            tune.status = 3

    db.close_db()
    
# =============
# Parse command
# =============

def parse_(args):
    db.open_db()

    parser = parse.TuneListParser(args.infile)
    parser.parse()
    parser.print_tunes()
    
    db.close_db()


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
# Rec command
# =============

def _rec_add(url: str, prompt_to_add_tune: bool = False) -> db.Recording:
    dotenv.load_dotenv()
    data_dir = os.getenv("GTUNES_DATA_DIR", os.path.join("gtunes", "data"))
    # TODO: implement local storage
    recs_dir = os.path.join(data_dir, "recs")
    this_rec = None
    # https://open.spotify.com/track/3dEbGOSpPkqa5p2Jrx9fkS?si=ec31a1a68cb3489e
    if re.match(r"^https://open.spotify.com/track.*", url):
        print("Detected spotify")

        sp = audio.connect_to_spotify()
        track_data = sp.track(url)
        artist = track_data["artists"][0]["name"]
        album = track_data["album"]["name"]
        name = track_data["name"]
        print(f"Found Spotify track {name} off album {album} by {artist}.")

        existing_rec = db.Recording.select().where(db.Recording.url == url).get_or_none()
        if existing_rec:
            print("Already have this recording in the database:")
            print(existing_rec)
        else:
            this_rec = db.Recording(name=name, url=url, source=db.RecordingSource.SPOTIFY, album=album, artist=artist)

    # https://www.youtube.com/watch?v=zHqC__xzSkI
    elif re.match(r"^https://www.youtube.com.*", url):
        print("Detected YouTube")
        id = url.split("v=")[1].split("&")[0]
        print("ID: " + id)
    else:
        print("Interpreting as file path")
        if not os.path.exists(url):
            print(f"Error: path '{url}' doesn't exist")
        else:
            pass

    if this_rec:
        print("Saving recording")
        this_rec.save()

        if prompt_to_add_tune:
            should_add_tune = questionary.confirm("Add existing tune to this recording?").ask()
        else:
            should_add_tune = False

        if should_add_tune == "y":
            tune = db.select_tune()
            if not tune:
                print("Must have existing tune to associate with recording.")
            else:
                start_time_seconds = util.timestamp_to_seconds(questionary.text("Start time (MM:SS)"))
                end_time_time_seconds = util.timestamp_to_seconds(questionary.text("End time (MM:SS)"))

                db.RecordingTune.create(tune=tune, recording=this_rec,
                                        start_time_secs=start_time_seconds, end_time_secs=end_time_time_seconds)
                
                print(f"Tune {tune} now associated with {this_rec}. Proceeding...")

        print("Done saving recording")

    return this_rec

def rec_add(args):
    """
    Add a recording to the tune database.
    After adding, the user will be prompted if they want to associate it with
    an existing tune.

    Args:
        args.url: Either a filepath, a Spotify URL, or a Youtube URL
    """
    db.open_db()

    rec = _rec_add(args.url)

    db.close_db()

    if not rec:
        return 1
    return 0

def rec_ls(args):
    db.open_db()
    query = db.Recording.select()
    print("Listing recordings.")

    for recording in query:
        print(recording)
    
    db.close_db()

def rec_info(args):
    db.open_db()
    recording = db.select_recording("Select a recording to show info of")

    print("Tunes:")
    for rectune in db.RecordingTune.select().where(db.Recording == recording):
        print(rectune.tune)

    db.close_db()

def rec_edit(args):
    db.open_db()

    selected_recording = db.select_recording("Select recording to edit")
    if not selected_recording:
        print("No recording selected")
    else:
        selected_recording.name = questionary.text("Name", default=_str_default(selected_recording.name)).ask()
        selected_recording.source = _select_from_enum_values("Source", db.RecordingSource, selected_recording.source)
        selected_recording.url = questionary.text("Url", default=_str_default(selected_recording.url)).ask()

        print(f"Saving recording {selected_recording}")
        selected_recording.save()

    db.close_db()

    return 0

def rec_link(args):
    db.open_db()
    _add_recording_to_tune_interactively(None, None)
    db.close_db()

def main():
    parser = argparse.ArgumentParser(description="Add and manipulate traditional tunes.")

    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # Create the parent parser with common arguments
    parent_parser_add_edit = argparse.ArgumentParser(add_help=False)  # Don't add help to avoid duplication
    parent_parser_add_edit.add_argument("--name", help="Name of the tune")
    parent_parser_add_edit.add_argument("--status", help=f"How well you know the tune", choices=[s.name for s in db.Status])
    parent_parser_add_edit.add_argument("--type", help="Type of tune", choices=[t.name for t in db.TuneType])
    parent_parser_add_edit.add_argument("--key", help="Key of the tune")
    parent_parser_add_edit.add_argument("--ts-id", help="Id of tune on TheSession")
    parent_parser_add_edit.add_argument("--comments", help="Any comments about the tune")
    parent_parser_add_edit.add_argument("--from", dest="from_", help="The place of person the tune is from")
    # Create parsers for subcommands

    # Tune subparser
    parser_tune = subparsers.add_parser("tune", help="Manage tunes")
    subparser_tune = parser_tune.add_subparsers(required=True)

    parser_tune_add = subparser_tune.add_parser("add", parents=[parent_parser_add_edit], help="Add a tune. Do so interactively if no arguments supplied.")
    parser_tune_add.set_defaults(func=tune_add)

    parser_tune_edit = subparser_tune.add_parser("edit", parents=[parent_parser_add_edit], help="Edit a tune")
    parser_tune_edit.add_argument("--new-name", help="Name to set the tune to.")
    parser_tune_edit.set_defaults(func=tune_edit)

    parser_tune_list = subparser_tune.add_parser("ls", help="List tunes")
    parser_tune_list.set_defaults(func=tune_list)
    parser_tune_list.add_argument("-n", dest="name", help="Name of tune")
    parser_tune_list.add_argument("-t", dest="type", help="Type of tune (jig, reel, etc.)")
    parser_tune_list.add_argument("-s", dest="status", help="Status of tune. How well the tune is known, int from 1-5.")

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

    parser_rec_info = rec_subparser.add_parser("info", help="Show more information about a recording.")
    parser_rec_info.set_defaults(func=rec_info)

    parser_rec_edit = rec_subparser.add_parser("edit", help="Edit recording information.")
    parser_rec_edit.set_defaults(func=rec_edit)

    parser_rec_link = rec_subparser.add_parser("link", help="Link this recording to an existing tune.")
    parser_rec_link.set_defaults(func=rec_link)

    # Set subparser
    parser_set = subparsers.add_parser("set", help="Manage sets of tunes")
    subparser_set = parser_set.add_subparsers(required=True)
    parser_set_add = subparser_set.add_parser("add", help="Add a set of tunes. composed of tunes in your tune database")
    parser_set_add.set_defaults(func=set_add)

    # Parse subparser
    parser_parse = subparsers.add_parser("parse", parents=[parent_parser_add_edit], help="Add list")
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