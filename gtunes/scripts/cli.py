#!/usr/bin/env python3
# The frontend: command line interface for the app.

import shelve
import argparse
from gtunes import tune
from gtunes import parse
from gtunes import scrape
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

def parse(args):
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

def main():
    parser = argparse.ArgumentParser(description="Add and manipulate traditional tunes.")

    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # Create the parent parser with common arguments
    parent_parser = argparse.ArgumentParser(add_help=False)  # Don't add help to avoid duplication
    parent_parser.add_argument("-l", type=str, default="tunes", dest="list_location", help="List location")

    # Create parsers for subcommands
    parser_add = subparsers.add_parser("add", parents=[parent_parser], help="Add a tune")
    parser_parse = subparsers.add_parser("parse", parents=[parent_parser], help="Add list")
    parser_list = subparsers.add_parser("list", parents=[parent_parser], help="List tunes")
    parser_scrape = subparsers.add_parser("scrape")

    parser_add.set_defaults(func=add)
    parser_list.set_defaults(func=list)
    parser_parse.set_defaults(func=parse)
    parser_scrape.set_defaults(func=scrape_tunes)

    parser_add.add_argument("name", type=str, help="Name of the tune")
    parser_add.add_argument("-t", type=str, dest="type", help="Type of tune (jig, reel, etc.)")
    parser_add.add_argument("-m", type=str, dest="mp3", help="Name of mp3 file")
    parser_add.add_argument("-k", type=str, dest="key", help="Key of the tune")
    parser_add.add_argument("-s", type=int, dest="status", help="Status of tune. How well the tune is known, int from 1-5.")
    parser_add.add_argument("-a", type=str, dest="abc", help="ABC")
    parser_add.add_argument("-c", type=str, dest="comment", help="Comment(s)")

    parser_list.add_argument("infile", help="Name of tune list")
    parser_list.add_argument("-n", dest="name", help="Name of tune")
    parser_list.add_argument("-t", dest="type", help="Type of tune (jig, reel, etc.)")
    parser_list.add_argument("-s", dest="status", help="Status of tune. How well the tune is known, int from 1-5.")

    parser_parse.add_argument("infile", help="The path to the tune list to parse")
    parser_parse.add_argument("-o", dest="outfile", help="The name of the output file (db will be appended)")

    parser_scrape.add_argument("tune_name", help="Name of tune to find abc settings of.")

    args = parser.parse_args()
    if args.command:
        args.func(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()