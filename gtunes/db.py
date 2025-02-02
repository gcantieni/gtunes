from peewee import *

db = SqliteDatabase(':memory:', pragmas={'foreign_keys': 1})

# def load_db():
#     global conn
#     #db_path = os.getenv("TUNE_DB", "example.db")
def init_db():
    global db
    db.connect()
    db.create_tables([GTune, Recording])

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
    #itinfo_id = IntegerField()
    comments = TextField(null=True)
    from_ = TextField(null=True)

    def __str__(self):
        name = getattr(self, 'name', 'None')
        id = getattr(self, 'id', 'None')
        type_ = getattr(self, 'type', 'None')
        abc = getattr(self, 'abc', 'None')
        key = getattr(self, 'key', 'None')
        status = getattr(self, 'status', 'None')
        comments = getattr(self, 'comments', 'None')
        #recordings = getattr(self, 'recordings', 'None')

        return f"ID: {id}, Name: {name}, Type: {type_}, Key: {key}\nABC: {abc}, Status: {status}, Comments: {comments}"


class Recording(BaseClass):
    name = CharField(null=True)
    spot_id = CharField(null=True)
    path = CharField(null=True)
    tune = ForeignKeyField(GTune, backref='recordings', null=True)
    start_time_secs = IntegerField(null=True)
    end_time_secs = IntegerField(null=True)

def peewee():
    db.connect()
    db.create_tables([GTune, Recording])

    lark = GTune.create(name="The Lark in the Morning", key="D", type="Jig", status=4, 
                        comments="Classic. Probably overplayed.")
    s = GTune.create(name="Spike Island Lasses", key="D modal", type="Reel", status=4)
    
    larc_rec = Recording.create(spot_id="5RZiKVsRf2Bg8y4KlJp7MH", tune=lark)

    
    l = (GTune
        .select()
        .join(Recording)
        .where(GTune.name == "The Lark in the Morning").get_or_none())
    
    print(GTune.get_by_id(1))


if __name__ == "__main__":
    # c = load_db()
    # init_tune_db(c)
    # add_tune(c, name="Lark in the Morning", key="D", type_="jig")
    # list_tunes(c)
    # close_db()
    peewee()



