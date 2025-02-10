from peewee import SqliteDatabase, Model, CharField, IntegerField, TextField, ForeignKeyField, DateTimeField
import os
from dotenv import load_dotenv
from gtunes.fzf_interact import fzf_select
import datetime

load_dotenv()
database_path = os.getenv("GTUNES_DB", "gtunes/data/gtunes.db")
db = SqliteDatabase(database_path, pragmas={'foreign_keys': 1})

def init_db():
    global db
    db.connect()
    db.create_tables([GTune, Recording], safe=True)

def close_db():
    db.close()

class BaseClass(Model):
    class Meta:
        database = db

# Start simple, each tune just has one recording, one spotify id, one path to an mp3
class GTune(BaseClass):
    name = CharField(unique=True)
    key = CharField(null=True)
    type = CharField(null=True)
    status = IntegerField(null=True)
    abc = TextField(null=True)
    ts_id = IntegerField(null=True) # Thesession id
    #itinfo_id = IntegerField() # Someday might use irishtunes.info
    comments = TextField(null=True)
    from_ = TextField(null=True)
    date_updated = DateTimeField(default=datetime.datetime.now)
    date_added = DateTimeField(default=datetime.datetime.now)

    def __str__(self):
        name = getattr(self, 'name', 'None')
        id = getattr(self, 'id', 'None')
        type_ = getattr(self, 'type', 'None')
        abc = getattr(self, 'abc', 'None')
        key = getattr(self, 'key', 'None')
        status = getattr(self, 'status', 'None')
        comments = getattr(self, 'comments', 'None')

        return f"ID: {id}, Name: {name}, Type: {type_}, Key: {key}\nABC: {abc}, Status: {status}, Comments: {comments}"


class Recording(BaseClass):
    name = CharField(null=True)
    spot_id = CharField(null=True)
    path = CharField(null=True)
    tune = ForeignKeyField(GTune, backref='recordings', null=True)
    start_time_secs = IntegerField(null=True)
    end_time_secs = IntegerField(null=True)

def select_tune(header=None):
    query = GTune.select()
    tune_list = [t.name for t in query]
    tune_name = fzf_select(tune_list, header=header)

    selected_tune = GTune.select().where(GTune.name == tune_name).get()

    return selected_tune

def get_tune_by_name(tune_name):
    return GTune.select().where(GTune.name == tune_name).get()

def main():
    init_db()
    select_tune()
    close_db()

    return 0

if __name__ == "__main__":
    exit(main())



