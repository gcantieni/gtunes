#!/usr/bin/env python3
# Provide the basic data structures to be used by other modules.

class Tune:
    """A traditional tune."""
    def __init__(self, id, name="", type="", status=1, abc=None, tradition="Irish", key="", comments=None, recordings=None, mp3=None):
        self.id = id
        self.name = name
        self.type = type
        self.status = status
        self.key = key
        self.abc = [] if not abc else abc
        #self.tradition = tradition # doesn't feel necessary yet since it's built around irish
        self.mp3 = mp3
        self.comments = [] if not comments else comments
        self.recordings = [] if not recordings else recordings

    # TODO: add a build_string that will not add something if its none
    
    def __str__(self):
        name = getattr(self, 'name', 'None')
        id_ = getattr(self, 'id', 'None')
        type_ = getattr(self, 'type', 'None')
        abc = getattr(self, 'abc', 'None')
        mp3 = getattr(self, 'mp3', 'None')
        key = getattr(self, 'key', 'None')
        status = getattr(self, 'status', 'None')
        comments = getattr(self, 'comments', 'None')
        recordings = getattr(self, 'recordings', 'None')

        return f"ID: {id_}, Name: {name}, Type: {type_}, Key:{key}\nABC: {abc}, MP3: {mp3}, Status: {status}, Comments: {comments}, recordings={recordings}"


if __name__ == "__main__":
    print(Tune(12345, name="Lark in the Morning", type="jig", status=5, comments=["Many parts", "A bit overplayed"], mp3="lark.m4a"))