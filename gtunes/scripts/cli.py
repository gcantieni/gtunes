#!/usr/bin/env python3
# The frontend: command line interface for the app.

import argparse
import shelve
from gtunes import tune
from gtunes import parse
from gtunes import scrape
from gtunes import db
from gtunes import audio
import csv
import os

def add(args):
    this_tune = this_tune.Tune(0, name=args.name)
    this_tune.type = args.type
    this_tune.key = args.key
    this_tune.comments = [ args.comment ]

    print(f"Adding tune: {this_tune}")

    with shelve.open(args.list_location) as shelf:
        shelf[this_tune.name] = this_tune

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

def spot(args):
    sp = audio.connect_to_spotify()
    if args.s or args.S: # thesession time, baby
        scraped_albums = None
        if args.s:
            scraped_albums = scrape.scrape_recordings(tune_id=args.s)
        else:
            scraped_albums = scrape.scrape_recordings(tune_name=args.S, limit=15)

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
    # TODO: handle arg parsing up front, not here 
    elif not args.a and not args.t:
        print("Must specify either album or track option")
    if args.t:
        audio.search_for_track(args.name, sp)
    

def main():
    parser = argparse.ArgumentParser(description="Add and manipulate traditional tunes.")

    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # Create the parent parser with common arguments
    parent_parser = argparse.ArgumentParser(add_help=False)  # Don't add help to avoid duplication
    parent_parser.add_argument("-l", type=str, default="tunes", dest="list_location", help="List location")

    # Create parsers for subcommands

    parser_add = subparsers.add_parser("add", parents=[parent_parser], help="Add a tune")
    parser_add.set_defaults(func=add)
    parser_add.add_argument("name", type=str, help="Name of the tune")
    parser_add.add_argument("-t", type=str, dest="type", help="Type of tune (jig, reel, etc.)")
    parser_add.add_argument("-m", type=str, dest="mp3", help="Name of mp3 file")
    parser_add.add_argument("-k", type=str, dest="key", help="Key of the tune")
    parser_add.add_argument("-s", type=int, dest="status", help="Status of tune. How well the tune is known, int from 1-5.")
    parser_add.add_argument("-a", type=str, dest="abc", help="ABC")
    parser_add.add_argument("-c", type=str, dest="comment", help="Comment(s)")

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
    main()