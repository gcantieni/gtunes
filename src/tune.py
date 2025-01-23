#!/usr/bin/env python3
# Provide the basic data structures to be used by other modules.

class Tune:
    """A traditional tune."""
    def __init__(self, name, type="", status=1, abc=None, tradition="Irish", key="", comments=None, rec="", mp3=None):
        self.name = name
        self.type = type
        self.status = status
        self.key = key
        self.abc = [] if not abc else abc
        self.tradition = tradition
        self.mp3 = mp3
        self.comments = [] if not comments else comments
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
        if self.abc:
            ret += "\nABC: \n"
            for abc in self.abc:
                ret += abc + "\n"
        if len(self.comments) > 0:
            ret += f"\nComments: {self.comments[0]}"
            for comment in self.comments[1:]:
                ret += f", {comment}"
        return ret
