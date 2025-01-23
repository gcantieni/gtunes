#!/usr/bin/env python3

from tune import Tune
import re

class TuneListConsumer:
    """Can consume a tune list and output a list of Tunes.
    """
    def __init__(self, file_location):
        self.file_location = file_location
        self.tunes = {}
        self.state = StartLineParser(self.tunes)

    def parse(self):
        with open(args.infile, "r") as file:
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
    def parse_line(self, line):
        if line.strip() == "PRACTICE:":
            return PracticeLineParser(self.tunes)
        
        tune = self.parse_tune(line)
        if tune:
            self.add_tune(tune)

        return self

class PracticeLineParser(LineParser):
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
    