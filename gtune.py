#!/usr/bin/env python3
import shelve
import argparse

class Tune:
    """A traditional tune."""
    def __init__(self, name, type="reel", status=1, abc="", tradition="Irish"):
        self.name = name
        self.type = type
        self.status = status
        self.abc = abc
        self.tradition = tradition
    
    def __str__(self):
        return f"Name: {self.name}, Type: {self.type}, Status: {self.status}"

def add():
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Add and manipulate traditional tunes.")

    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    parser_add = subparsers.add_parser("add", help="Add a tune")
    parser_add.add_argument("name", type=str, help="Name of the tune")
    parser_add.set_defaults(func=add)

    args = parser.parse_args()


    with shelve.open("tunes_list") as shelf:
        abbey_reel = shelf["Abbey Reel"]

        print(f"Abbey reel fetched: {abbey_reel}")