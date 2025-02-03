#!/usr/bin/env python3
# The frontend: command line interface for the app.

import argparse
import shelve
from gtunes import parse
from gtunes import scrape
from gtunes import db
from gtunes import audio
from gtunes.tui import tui
from curses import wrapper
import csv
import os

CURSOR="gtn> "

def tui_wrapper(args): # args isn't used
    wrapper(tui)

def _edit_tune_interactively(tune):
    print(tune)
    help_menu = """h: help, n: name, k: key, t: type, r: recordings, c: comment,
a: status, o: search spotify, p: print, s: save, q: quit"""
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
            tune.comment = input("Commend: ")
        elif opt == "a":
            tune.status = input("Status: ")
        elif opt == "o":
            save_data = _search_spotify_interactively(tune_name=tune.name)
            # TODO: save Recordings
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
            print(tune)
            tune.save()
            break

def edit(args):
    if not args.n:
        print("Select tune to edit")
        db.init_db()
        tune = db.select_tune()
        _edit_tune_interactively(tune)
        db.close_db()
    else:
        print("Non-interactive edit has not been implemented yet.")

def add(args):
    db.init_db()
    this_tune = db.GTune(name=args.name)
    this_tune.type = args.type
    this_tune.key = args.key
    this_tune.comments = args.comment

    print(f"Adding tune: {this_tune}")

    this_tune.save()
    db.close_db()

def list(args):
    with shelve.open(args.list_location) as shelf:
        print(f"Shelf contains {len(shelf)} tunes")
        for name in shelf:
            print(f"{shelf[name]}")

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
    scrape.scrape_recordings(tune_name=args.tune)

def _search_spotify_interactively(tune_ts_id=None, tune_name=None):
    sp = audio.connect_to_spotify()
    scraped_albums = None
    if tune_ts_id is not None:
        scraped_albums = scrape.scrape_recordings(tune_id=tune_ts_id, limit=15)
    elif tune_name is not None:
        scraped_albums = scrape.scrape_recordings(tune_name=tune_name, limit=15)
    else:
        print("Error: Supplied neither tune name not thesession id")

    saved_albums = {}
    for album_name, scrape_data in scraped_albums.items():
        alb = audio.spot_search_albums(album_name, sp, artist_name=scrape_data['artist_name'])
        if alb:
            track_data = audio.spot_play_nth_album_track(alb['id'], scraped_albums[album_name]['track_number'], sp)
            if not track_data:
                print(f"No track data for album {album_name}, skipping")
                continue
            print(f"Album: {album_name}, track: {track_data['name']}")
            user_input = input("s: save, n: next q: quit > ")
            if user_input == "s":
                saved_albums[album_name] = scraped_albums[album_name]
                saved_albums[album_name]['spot_album_id'] = alb['id']
            elif user_input == "q":
                print("bye")
                break
            elif user_input == "n":
                continue
    print("Done playing albums.")
    if saved_albums:
        print(f"Save data: {saved_albums}")
    return saved_albums

def spot(args):
    if args.s or args.S: # thesession time, baby
        if args.s:
            _search_spotify_interactively(tune_ts_id=args.s)
        else:
            _search_spotify_interactively(tune_name=args.S)
    elif not args.a and not args.t:
        print("Must specify either album or track option")
    if args.t:
        sp = audio.connect_to_spotify()
        audio.search_for_track(args.name, sp)
    

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

    parser_edit = subparsers.add_parser("edit", parents=[edit_add_parent_parser], help="Edit a tune")
    parser_edit.set_defaults(func=edit)

    parser_list = subparsers.add_parser("list", parents=[parent_parser], help="List tunes")
    parser_list.set_defaults(func=list)
    parser_list.add_argument("infile", help="Name of tune list")
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

    parser_spot = subparsers.add_parser("spot", help="Play albums from spotify.")
    parser_spot.set_defaults(func=spot)
    parser_spot.add_argument("-name", help="Name of track or album to be played.")
    parser_spot.add_argument("-a", action="store_true", help="Play album")
    parser_spot.add_argument("-t", action="store_true", help="Play track")
    parser_spot.add_argument("-s", help="Scrape albums of thesession.org by id and search for them on spotify.")
    parser_spot.add_argument("-S", help="Scrape albums of thesession.org by name and search for them on spotify.")

    args = parser.parse_args()
    if args.command:
        args.func(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    os.exit(main())