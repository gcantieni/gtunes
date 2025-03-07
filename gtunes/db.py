from peewee import SqliteDatabase, Model, CharField, IntegerField, TextField, ForeignKeyField, DateTimeField
import os
from dotenv import load_dotenv
from gtunes.fzf_interact import fzf_select
from enum import Enum
import datetime

load_dotenv()
data_dir = os.getenv("GTUNES_DB", os.path.join("gtunes", "data"))
database_path = os.path.join(data_dir, "gtunes.db")
db = SqliteDatabase(database_path, pragmas={'foreign_keys': 1})

def open_db():
    global db
    db.connect()
    db.create_tables([Tune, Recording, RecordingTune], safe=True)

def close_db():
    db.close()

class BaseClass(Model):
    class Meta:
        database = db
    
class Status(Enum):
    TODO = 1
    CAN_PLAY = 2
    CAN_START = 3
    IN_SET = 4
    MASTERED = 5

class TuneType(Enum):
    REEL = 1
    JIG = 2
    POLKA = 3
    SLIDE = 4


# Start simple, each tune just has one recording, one spotify id, one path to an mp3
class Tune(BaseClass):
    name = CharField(unique=True)
    key = CharField(null=True)
    # Storing full string so that looking through the database is easier
    # from an external viewer
    type = CharField(null=True, choices=[t.name for t in TuneType])
    status = IntegerField(choices=[(s.value, s.name) for s in Status], default=Status["TODO"])
    abc = TextField(null=True)
    ts_id = IntegerField(null=True) # Thesession id
    #itinfo_id = IntegerField() # Someday might use irishtunes.info
    comments = TextField(null=True)
    from_ = TextField(null=True)
    date_updated = DateTimeField(default=datetime.datetime.now)
    date_added = DateTimeField(default=datetime.datetime.now)

    # Desired output:
    # The Lark in the Morning (D jig) - S: 1 
    def __str__(self):
        ret = ""

        if self.name:
            ret += self.name

        opened_paren = False
        if self.key or self.type or self.status:
            ret += " ("
            opened_paren = True

        if self.key:
            ret += self.key
            if self.type:
                ret += " "

        if self.type:
            ret += self.type.lower()

        if self.key or self.type:
            ret += ", "
    
        # TODO: could represent based on color, like green for learned
        if self.status:
            ret += Status(self.status).name
        
        if opened_paren:
            ret += ")"

        if self.comments:
            ret += f" - {self.comments}"

        return ret

class Source(Enum):
    SPOTIFY = "spotify"
    YOUTUBE = "youtube"
    LOCAL = "local"

class Recording(BaseClass):
    name = CharField(null=True)
    url = TextField()
    source = CharField(choices=[(rec_source.value, rec_source.name) for rec_source in Source])
    artist = CharField(null=True)
    album = CharField(null=True)
   
    def __str__(self):
        """
        Want something like:
        From Galway to Dublin / The Harp and Shamrock by Nathan Gourley, Laura Feddersen
        """
        out = self.name
        if self.artist:
            out += f" by {self.artist}"
        return out

# jump table: find all the recordings of a tune you have, and where they start
# or find all the tunes in a recording that you have tracked
class RecordingTune(BaseClass):
    tune = ForeignKeyField(Tune, backref='tune_recordings')
    recording = ForeignKeyField(Recording, backref='recording_tunes')
    start_time_secs = IntegerField(null=True)
    end_time_secs = IntegerField(null=True)

class Set(BaseClass):
    name = CharField(null=True)

class SetTune(BaseClass):
    set_ = ForeignKeyField(Set, backref='set_tunes', on_delete='CASCADE')
    tune = ForeignKeyField(Tune, backref='tune_sets', on_delete='CASCADE')
    position = IntegerField()
    indexes = (
        (('set', 'tune'), True),  # Ensure a tune isn't duplicated in a set
    )
    ordering = ['position']  # Default ordering by position field

def select_tune(header=None):
    """
    Returns:
        selected_tune (db.Tune)
        user_input (str)
    """
    query = Tune.select()
    tune_list = [t.name for t in query]
    tune_name, user_input = fzf_select(tune_list, header=header)

    selected_tune = None
    if tune_name:
        selected_tune = Tune.select().where(Tune.name == tune_name).get_or_none()

    return selected_tune, user_input

def select_recording(header=None):
    query = Recording.select()

    recording_list = [r.name for r in query]
    rec_name, user_input = fzf_select(recording_list, header=header)

    selected_rec = None
    if rec_name:
        selected_rec = Recording.select().where(Recording.name == rec_name).get()
    
    return selected_rec, user_input

def get_tune_by_name(tune_name):
    return Tune.select().where(Tune.name == tune_name).get()

def main():
    open_db()
    select_tune()
    close_db()

    return 0

if __name__ == "__main__":
    exit(main())



