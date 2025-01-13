#!/usr/bin/env python3
import shelve
import argparse
import re

class Tune:
    """A traditional tune."""
    def __init__(self, name, type="", status=1, abc="", tradition="Irish", key="", comments=None, rec="", mp3=None):
        self.name = name
        self.type = type
        self.status = status
        self.key = key
        self.abc = abc
        self.tradition = tradition
        self.mp3 = mp3
        self.comments = []
        if comments is not None:
            self.comments = comments
        self.rec = rec
    
    def __str__(self):
        ret = f"Name: {self.name}"
        if self.type != "":
            ret += f", Type: {self.type}"
        ret += f", Status: {self.status}"
        if self.key:
            ret += f", Key: {self.key}"
        if self.mp3 is not None:
            ret += f", mp3: {self.mp3}"
        if self.abc != "":
            ret += f"\nABC: {self.abc}"
        if len(self.comments) > 0:
            ret += f"\nComments: {self.comments[0]}"
            for comment in self.comments[1:]:
                ret += f", {comment}"
        return ret

class TuneListConsumer:
    """Can consume a tune list and output a list of Tunes.
    Expects something like:
    LEARN:
     - tunes
    PRACTICE:
     - tunes
    REELS:
    A
     - tunes
    JIGS:
    G
     - tunes
    """
    def __init__(self, file_location):
        self.file_location = file_location
        self.tunes = {}
        self.state = StartLineParser(self.tunes)

    def parse(self):
        with open(args.filepath, "r") as file:
            for line in file:
                new_state = self.state.parse_line(line)
                self.state = self.state.parse_line(line)

        return self.tunes
    
    def print_tunes(self):
        for tune in self.tunes:
            print(f"{self.tunes[tune]}")
    
class LineParser:
    def __init__(self, tunes):
        self.tunes = tunes

    def __str__(self):
        return "Base Line Parser"

    # Abstract method
    def parse_line(self, line):
        pass

    def add_tune(self, tune):
        self.tunes[tune.name] = tune

    def parse_tune(self, line):
        line_parts = line.split("-")

        if len(line_parts) < 2:
            return None

        if line_parts[0] == "":
            line_parts.pop(0)
        
        name = line_parts[0].strip()

        tune = None
        # Some of my names are actually audio file names.
        # These I can parse slightly differently. They will look like: [[BlackPats.m4a]]
        m4a_pattern = r'\[\[(.*?)\.m4a\]\]'
        m4a_match = re.match(m4a_pattern, name)
        if m4a_match:
            stripped_name = m4a_match.group(1)
            tune = Tune(stripped_name, mp3=name.strip('[]'))
        else:
            tune = Tune(name)

        if len(line_parts) == 1:
            return tune
        
        metadata = line_parts[1]
        metadata = metadata.split(",")
        for md in metadata:
            md = md.strip()
            key_pattern = r'[A-G]'
            type_pattern = r'(?i)(reel|slip jig|hop jig|jig|polka|hornpipe)'

            key_match = re.search(key_pattern, md)
            type_match = re.search(type_pattern, md)

            if key_match:
                tune.key = key_match.group()
            if type_match:
                tune.type = type_match.group()
            
            if not key_match and not type_match:
                tune.comments.append(md)
        
        return tune

class StartLineParser(LineParser):
    def __str__(self):
        return "Start parser"
    
    def parse_line(self, line):
        line = line.strip()
        if line == "LEARN:":
            return LearnLineParser(self.tunes)
        if line == "PRACTICE:":
            return PracticeLineParser()
        if line == "REELS:":
            return LearnedTuneParser("reel")
        return self


class LearnLineParser(LineParser):
    def __str__(self):
        return "Learn parser"

    def parse_line(self, line):
        if line.strip() == "PRACTICE:":
            return PracticeLineParser(self.tunes)
        
        tune = self.parse_tune(line)
        if tune:
            self.add_tune(tune)

        return self

class PracticeLineParser(LineParser):
    def __str__(self):
        return "Practice parser"
    
    def parse_line(self, line):
        if line.strip() == "REELS:":
            return LearnedTuneParser(self.tunes, "reel")

        tune = self.parse_tune(line)
        if tune:
            tune.status = 2
            self.add_tune(tune)

        return self

class LearnedTuneParser(LineParser):
    def __init__(self, tunes, tune_type):
        super().__init__(tunes)
        self.tune_type = tune_type
        self.key = None
    
    def __str__(self):
        return "Learned parser"

    def match_key(self, line):
        pattern = r'[A-G]#?(m)?( modal)?'
        return re.search(pattern, line)
    
    def match_tune_type(self, line):
        pattern = r'(REELS|JIGS|HORNPIPES|POLKAS)'
        return re.match(pattern, line.strip(':\t '))

    def parse_line(self, line):
        match = self.match_key(line)
        if match:
            self.key = match.group()
            return self
        
        match = self.match_tune_type(line)
        if match:
            self.tune_type = match.group().lower()[:-1] # e.g. REELS -> reel
            return self
        
        tune = self.parse_tune(line)
        if tune:
            tune.type = self.tune_type
            tune.key = self.key
            self.add_tune(tune)

        return self

def add(args):
    tune = Tune(args.name)

    tune.type = args.type

    with shelve.open(args.list_location) as shelf:
        for key in shelf:
            print(f"tune with key {key}: {shelf[key]}")

def list(args):
    with shelve.open(args.list_location) as shelf:
        for key in shelf:
            print(f"tune with key {key}: {shelf[key]}")

def consume(args):
    parser = TuneListConsumer(args.filepath)
    parser.parse()
    parser.print_tunes()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Add and manipulate traditional tunes.")

    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # Create the parent parser with common arguments
    parent_parser = argparse.ArgumentParser(add_help=False)  # Don't add help to avoid duplication
    parent_parser.add_argument("-l", type=str, default="tunes_list", dest="list_location", help="List location")

    # Create parsers for subcommands
    parser_add = subparsers.add_parser("add", parents=[parent_parser], help="Add a tune")
    parser_consume = subparsers.add_parser("consume", parents=[parent_parser], help="Add list")
    parser_list = subparsers.add_parser("list", parents=[parent_parser], help="List tunes")

    parser_add.set_defaults(func=add)
    parser_list.set_defaults(func=list)
    parser_consume.set_defaults(func=consume)

    parser_add.add_argument("name", type=str, help="Name of the tune")
    parser_add.add_argument("-t", type=str, dest="type", help="Type of tune (jig, reel, etc.)")
    parser_add.add_argument("-s", type=int, dest="status", help="Status of tune. How well the tune is known, int from 1-5.")
    parser_add.add_argument("-a", type=str, dest="abc", help="ABC")

    parser_list.add_argument("-n", dest="name", help="Name of tune")
    parser_list.add_argument("-t", dest="type", help="Type of tune (jig, reel, etc.)")
    parser_list.add_argument("-s", dest="status", help="Status of tune. How well the tune is known, int from 1-5.")

    parser_consume.add_argument("filepath", help="The path to the tune list to consume")

    args = parser.parse_args()
    if args.command:
        args.func(args)
    else:
        parser.print_help()